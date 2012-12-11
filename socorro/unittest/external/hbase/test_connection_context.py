# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock

from socorro.external.hbase.connection_context import \
     HBaseConnectionContextPooled
from socorro.external.hbase.hbase_client import (
    FatalException,
    NoConnectionException
)
from socorro.lib.util import SilentFakeLogger, DotDict
from socorro.database.transaction_executor import TransactionExecutor
from configman import Namespace

from hbase import ttypes
from thrift import Thrift
from socket import timeout, error


class FakeHB_Connection(object):
    def __init__(self):
        self.hbaseThriftExceptions = (error,)
        self.close_counter = 0
        self.commit_counter = 0
        self.rollback_counter = 0

    def close(self):
        self.close_counter += 1

    def commit(self):
        self.commit_counter += 1

    def rollback(self):
        self.rollback_counter += 1

    def in_transaction(self):
        return True


class TestConnectionContext(unittest.TestCase):

    @mock.patch('socorro.external.hbase.connection_context.hbase_client')
    def test_basic_hbase_usage(self, mocked_hbcl):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
        })
        a_fake_hbase_connection = FakeHB_Connection()
        mocked_hbcl.HBaseConnectionForCrashReports = \
            mock.Mock(return_value=a_fake_hbase_connection)
        hb_context = HBaseConnectionContextPooled(
            local_config,
            local_config
        )
        self.assertEqual(
            mocked_hbcl.HBaseConnectionForCrashReports.call_count,
            1
        )
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            1
        )
        # open a connection
        with hb_context() as conn:
            self.assertEqual(
                mocked_hbcl.HBaseConnectionForCrashReports.call_count,
                2
            )
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            1
        )
        # get that same connection again
        with hb_context() as conn:
            self.assertEqual(
                mocked_hbcl.HBaseConnectionForCrashReports.call_count,
                2
            )
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            1
        )
        # get a named connection
        with hb_context('fred') as conn:
            self.assertEqual(
                mocked_hbcl.HBaseConnectionForCrashReports.call_count,
                3
            )
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            1
        )
        self.assertEqual(
            len(hb_context.pool),
            2
        )
        # get that original same connection again
        with hb_context() as conn:
            self.assertEqual(
                mocked_hbcl.HBaseConnectionForCrashReports.call_count,
                3
            )
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            1
        )
        # close all connections
        hb_context.close()
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            3
        )

    @mock.patch('socorro.external.hbase.connection_context.hbase_client')
    def test_hbase_usage_with_transaction(self, mocked_hbcl):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
        })
        a_fake_hbase_connection = FakeHB_Connection()
        mocked_hbcl.HBaseConnectionForCrashReports = \
            mock.Mock(return_value=a_fake_hbase_connection)
        hb_context = HBaseConnectionContextPooled(
            local_config,
            local_config
        )
        def all_ok(connection, dummy):
            self.assertEqual(dummy, 'hello')
            return True

        transaction = TransactionExecutor(local_config, hb_context)
        result = transaction(all_ok, 'hello')
        self.assertTrue(result)
        self.assertEqual(
            mocked_hbcl.HBaseConnectionForCrashReports.call_count,
            2
        )
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            1
        )
        self.assertEqual(
            a_fake_hbase_connection.rollback_counter,
            0
        )
        self.assertEqual(
            a_fake_hbase_connection.commit_counter,
            1
        )

        def bad_deal(connection, dummy):
            raise KeyError('fred')

        self.assertRaises(KeyError, transaction, bad_deal, 'hello')
        self.assertEqual(
            mocked_hbcl.HBaseConnectionForCrashReports.call_count,
            2
        )
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            1
        )
        self.assertEqual(
            a_fake_hbase_connection.rollback_counter,
            1
        )
        self.assertEqual(
            a_fake_hbase_connection.commit_counter,
            1
        )

        hb_context.close()
        self.assertEqual(
            a_fake_hbase_connection.close_counter,
            2
        )


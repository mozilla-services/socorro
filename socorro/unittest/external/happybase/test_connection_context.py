# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock

import happybase

from socorro.external.happybase import connection_context
from socorro.external.happybase.connection_context import (
    HappyBaseConnectionContext,
    HappyBasePooledConnectionContext,
)

from socorro.lib.util import SilentFakeLogger, DotDict
from socorro.database.transaction_executor import TransactionExecutor
from socorro.unittest.testbase import TestCase
from configman import Namespace

from socket import timeout, error


class FakeHB_Connection(object):
    def __init__(self, config, *args, **kwargs):
        self.close_counter = 0
        self.commit_counter = 0
        self.rollback_counter = 0

    def close(self):
        self.close_counter += 1

    def commit(self):
        self.commit_counter += 1

    def rollback(self):
        self.rollback_counter += 1


class TestConnectionContext(TestCase):
    def test_basic_hbase_usage(self):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'logger': SilentFakeLogger(),
        })
        a_fake_hbase_connection = FakeHB_Connection(local_config)
        with mock.patch.object(happybase, 'Connection',
                               mock.Mock(return_value=a_fake_hbase_connection)):
            hb_context = connection_context.HappyBaseConnectionContext(
                local_config
            )
            # open a connection
            with hb_context() as conn:
                pass
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                1
            )
            # open another connection again
            with hb_context() as conn:
                pass
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                2
            )
            # get a named connection
            with hb_context('fred') as conn:
                pass
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                3
            )
            # close all connections
            hb_context.close()
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                3
            )

    def test_hbase_usage_with_transaction(self):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
        })
        a_fake_hbase_connection = FakeHB_Connection(local_config)
        with mock.patch.object(HappyBaseConnectionContext, 'connection',
                               mock.Mock(return_value=a_fake_hbase_connection)):
            hb_context = connection_context.HappyBaseConnectionContext(
                local_config
            )
            def all_ok(connection, dummy):
                self.assertEqual(dummy, 'hello')
                return True

            transaction = TransactionExecutor(local_config, hb_context)
            result = transaction(all_ok, 'hello')
            self.assertTrue(result)
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
                a_fake_hbase_connection.close_counter,
                2
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

from contextlib import contextmanager

class FakeHB_Connection2(object):
    def __init__(self, config, *args, **kwargs):
        self.close_counter = 0
        self.commit_counter = 0
        self.rollback_counter = 0

    def close(self):
        self.close_counter += 1

    def commit(self):
        self.commit_counter += 1

    def rollback(self):
        self.rollback_counter += 1

    @contextmanager
    def __call__(self):
        yield self

class HappyBasePooledConnectionContextMock(HappyBasePooledConnectionContext):
    @contextmanager
    def __call__(self, name=None):
        with self._connection_pool.connection() as connection:
            yield connection


class TestPooledConnectionContext(TestCase):
    def test_basic_hbase_usage(self):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'logger': SilentFakeLogger(),
        })
        a_fake_hbase_connection = FakeHB_Connection(local_config)
        a_fake_hbase_pool = mock.MagicMock()
        a_fake_hbase_pool.return_value = a_fake_hbase_connection
        with mock.patch.object(
            happybase,
            'ConnectionPool',
            mock.Mock(return_value=a_fake_hbase_pool)
        ):
            hb_context = connection_context.HappyBasePooledConnectionContext(
                local_config
            )
            # open a connection
            with hb_context() as conn:
                pass
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                0
            )
            # open another connection again
            with hb_context() as conn:
                pass
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                0
            )
            # get a named connection
            with hb_context('fred') as conn:
                pass
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                0
            )
            # close all connections
            hb_context.close()
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                0
            )

    def test_hbase_usage_with_transaction(self):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
        })
        a_fake_hbase_connection = FakeHB_Connection2(local_config)
        a_fake_hbase_pool = mock.MagicMock()
        a_fake_hbase_pool.connection = a_fake_hbase_connection
        with mock.patch.object(
            happybase,
            'ConnectionPool',
            mock.Mock(return_value=a_fake_hbase_pool)
        ):
            hb_context = HappyBasePooledConnectionContextMock(
                local_config
            )
            def all_ok(connection, dummy):
                self.assertEqual(dummy, 'hello')
                return True

            transaction = TransactionExecutor(local_config, hb_context)
            result = transaction(all_ok, 'hello')
            self.assertTrue(result)
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                0
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
                a_fake_hbase_connection.close_counter,
                0
            )
            self.assertEqual(
                a_fake_hbase_connection.commit_counter,
                1
            )

            hb_context.close()
            self.assertEqual(
                a_fake_hbase_connection.close_counter,
                0
            )

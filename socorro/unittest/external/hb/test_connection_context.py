# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
from nose.tools import eq_, ok_, assert_raises

from socorro.external.hb import connection_context
from socorro.lib.util import SilentFakeLogger, DotDict
from socorro.database.transaction_executor import TransactionExecutor
from socorro.unittest.testbase import TestCase

from socket import error


class FakeHB_Connection(object):
    def __init__(self, config):
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


class TestConnectionContext(TestCase):
    def test_basic_hbase_usage(self):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
          'executor_identity': lambda: 'dwight'  # bogus thread id
        })
        a_fake_hbase_connection = FakeHB_Connection(local_config)
        with mock.patch.object(connection_context, 'HBaseConnection',
                               mock.Mock(return_value=a_fake_hbase_connection)):
            hb_context = connection_context.HBaseConnectionContext(
                local_config
            )
            # open a connection
            with hb_context() as conn:
                pass
            eq_(
                a_fake_hbase_connection.close_counter,
                1
            )
            # open another connection again
            with hb_context() as conn:
                pass
            eq_(
                a_fake_hbase_connection.close_counter,
                2
            )
            # get a named connection
            with hb_context('fred') as conn:
                pass
            eq_(
                a_fake_hbase_connection.close_counter,
                3
            )
            # close all connections
            hb_context.close()
            eq_(
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
          'executor_identity': lambda: 'dwight'  # bogus thread id
        })
        a_fake_hbase_connection = FakeHB_Connection(local_config)
        with mock.patch.object(connection_context, 'HBaseConnection',
                               mock.Mock(return_value=a_fake_hbase_connection)):
            hb_context = connection_context.HBaseConnectionContext(
                local_config
            )
            def all_ok(connection, dummy):
                eq_(dummy, 'hello')
                return True

            transaction = TransactionExecutor(local_config, hb_context)
            result = transaction(all_ok, 'hello')
            ok_(result)
            eq_(
                a_fake_hbase_connection.close_counter,
                1
            )
            eq_(
                a_fake_hbase_connection.rollback_counter,
                0
            )
            eq_(
                a_fake_hbase_connection.commit_counter,
                1
            )

            def bad_deal(connection, dummy):
                raise KeyError('fred')

            assert_raises(KeyError, transaction, bad_deal, 'hello')
            eq_(
                a_fake_hbase_connection.close_counter,
                2
            )
            eq_(
                a_fake_hbase_connection.commit_counter,
                1
            )

            hb_context.close()
            eq_(
                a_fake_hbase_connection.close_counter,
                2
            )


class TestHBasePooledConnectionContext(TestCase):

    def test_basic_hbase_usage(self):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
          'executor_identity': lambda: 'dwight'  # bogus thread id
        })
        a_fake_hbase_connection = FakeHB_Connection(local_config)
        with mock.patch.object(connection_context, 'HBaseConnection',
                               mock.Mock(return_value=a_fake_hbase_connection)):
            hb_context = connection_context.HBasePooledConnectionContext(
                local_config
            )
            # open a connection
            with hb_context() as conn:
                pass
            eq_(
                a_fake_hbase_connection.close_counter,
                0
            )
            # open another connection again
            with hb_context() as conn:
                pass
            eq_(
                a_fake_hbase_connection.close_counter,
                0
            )
            # get a named connection
            with hb_context('fred') as conn:
                pass
            eq_(
                a_fake_hbase_connection.close_counter,
                0
            )
            # close all connections
            hb_context.close()
            eq_(
                a_fake_hbase_connection.close_counter,
                2
            )

    def test_hbase_usage_with_transaction(self):
        local_config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
          'executor_identity': lambda: 'dwight'  # bogus thread id
        })
        a_fake_hbase_connection = FakeHB_Connection(local_config)
        with mock.patch.object(connection_context, 'HBaseConnection',
                               mock.Mock(return_value=a_fake_hbase_connection)):
            hb_context = connection_context.HBasePooledConnectionContext(
                local_config
            )
            def all_ok(connection, dummy):
                eq_(dummy, 'hello')
                return True

            transaction = TransactionExecutor(local_config, hb_context)
            result = transaction(all_ok, 'hello')
            ok_(result)
            eq_(
                a_fake_hbase_connection.close_counter,
                0
            )
            eq_(
                a_fake_hbase_connection.rollback_counter,
                0
            )
            eq_(
                a_fake_hbase_connection.commit_counter,
                1
            )

            def bad_deal(connection, dummy):
                raise KeyError('fred')

            assert_raises(KeyError, transaction, bad_deal, 'hello')
            # at this point, the underlying connection has been deleted from
            # the pool, because it was considered to be a bad connection.
            eq_(
                a_fake_hbase_connection.close_counter,
                0
            )
            eq_(
                a_fake_hbase_connection.commit_counter,
                1
            )

            hb_context.close()
            # because the connection was previously deleted from the pool,
            # no connection gets closed at this point.
            eq_(
                a_fake_hbase_connection.close_counter,
                0
            )

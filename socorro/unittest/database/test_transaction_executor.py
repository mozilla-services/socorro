# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_, assert_raises
import psycopg2
from configman import Namespace, ConfigurationManager, class_converter
import socorro.database.transaction_executor
from socorro.database.transaction_executor import (
  TransactionExecutor, TransactionExecutorWithInfiniteBackoff)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.unittest.testbase import TestCase

class SomeError(Exception):
    pass


class MockConnectionContext(ConnectionContext):

    def connection(self, __=None):
        return MockConnection()


class MockLogging:
    def __init__(self):
        self.debugs = []
        self.warnings = []
        self.errors = []
        self.criticals = []

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))

    def critical(self, *args, **kwargs):
        self.criticals.append((args, kwargs))


class MockConnection(object):

    def __init__(self):
        self.transaction_status = \
          psycopg2.extensions.TRANSACTION_STATUS_IDLE

    def get_transaction_status(self):
        return self.transaction_status

    def close(self):
        pass

    def commit(self):
        global commit_count
        commit_count += 1

    def rollback(self):
        global rollback_count
        rollback_count += 1


commit_count = 0
rollback_count = 0


class TestTransactionExecutor(TestCase):

    def setUp(self):
        global commit_count, rollback_count
        commit_count = 0
        rollback_count = 0

    def test_basic_usage_with_postgres(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          #default=TransactionExecutorWithBackoff,
          default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )
        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)
            _function_calls = []  # some mutable

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                _function_calls.append(connection)

            executor(mock_function)
            ok_(_function_calls)
            eq_(commit_count, 1)
            eq_(rollback_count, 0)

    def test_rollback_transaction_exceptions_with_postgres(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                connection.transaction_status = \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                raise SomeError('crap!')

            assert_raises(SomeError, executor, mock_function)

            eq_(commit_count, 0)
            eq_(rollback_count, 1)
            ok_(mock_logging.errors)

    def test_basic_usage_with_postgres_with_backoff(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithInfiniteBackoff,
          #default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)
            _function_calls = []  # some mutable

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                _function_calls.append(connection)

            executor(mock_function)
            ok_(_function_calls)
            eq_(commit_count, 1)
            eq_(rollback_count, 0)

    def test_operation_error_with_postgres_with_backoff(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithInfiniteBackoff,
          #default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'backoff_delays': [2, 4, 6, 10, 15]}],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)
            _function_calls = []  # some mutable

            _sleep_count = []

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                _function_calls.append(connection)
                # the default sleep times are going to be,
                # 2, 4, 6, 10, 15
                # so after 2 + 4 + 6 + 10 + 15 seconds
                # all will be exhausted
                if sum(_sleep_count) < sum([2, 4, 6, 10, 15]):
                    raise psycopg2.OperationalError('Arh!')

            def mock_sleep(n):
                _sleep_count.append(n)

            # monkey patch the sleep function from inside transaction_executor
            _orig_sleep = socorro.database.transaction_executor.time.sleep
            socorro.database.transaction_executor.time.sleep = mock_sleep

            try:
                executor(mock_function)
                ok_(_function_calls)
                eq_(commit_count, 1)
                eq_(rollback_count, 5)
                ok_(mock_logging.criticals)
                eq_(len(mock_logging.criticals), 5)
                ok_(len(_sleep_count) > 10)
            finally:
                socorro.database.transaction_executor.time.sleep = _orig_sleep

    def test_operation_error_with_postgres_with_backoff_with_rollback(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithInfiniteBackoff,
          #default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'backoff_delays': [2, 4, 6, 10, 15]}],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)
            _function_calls = []  # some mutable

            _sleep_count = []

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                connection.transaction_status = \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                _function_calls.append(connection)
                # the default sleep times are going to be,
                # 2, 4, 6, 10, 15
                # so after 2 + 4 + 6 + 10 + 15 seconds
                # all will be exhausted
                if sum(_sleep_count) < sum([2, 4, 6, 10, 15]):
                    raise psycopg2.OperationalError('Arh!')

            def mock_sleep(n):
                _sleep_count.append(n)

            # monkey patch the sleep function from inside transaction_executor
            _orig_sleep = socorro.database.transaction_executor.time.sleep
            socorro.database.transaction_executor.time.sleep = mock_sleep

            try:
                executor(mock_function)
                ok_(_function_calls)
                eq_(commit_count, 1)
                eq_(rollback_count, 5)
                ok_(mock_logging.criticals)
                eq_(len(mock_logging.criticals), 5)
                ok_(len(_sleep_count) > 10)
            finally:
                socorro.database.transaction_executor.time.sleep = _orig_sleep

    def test_programming_error_with_postgres_with_backoff_with_rollback(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithInfiniteBackoff,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'backoff_delays': [2, 4, 6, 10, 15]}],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)
            _function_calls = []  # some mutable

            _sleep_count = []

            def mock_function_struggling(connection):
                assert isinstance(connection, MockConnection)
                connection.transaction_status = \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                _function_calls.append(connection)
                # the default sleep times are going to be,
                # 2, 4, 6, 10, 15
                # so after 2 + 4 + 6 + 10 + 15 seconds
                # all will be exhausted
                if sum(_sleep_count) < sum([2, 4, 6, 10, 15]):
                    raise psycopg2.ProgrammingError(
                        'SSL SYSCALL error: EOF detected'
                    )

            def mock_sleep(n):
                _sleep_count.append(n)

            # monkey patch the sleep function from inside transaction_executor
            _orig_sleep = socorro.database.transaction_executor.time.sleep
            socorro.database.transaction_executor.time.sleep = mock_sleep

            try:
                executor(mock_function_struggling)
                ok_(_function_calls)
                eq_(commit_count, 1)
                eq_(rollback_count, 5)
                ok_(mock_logging.criticals)
                eq_(len(mock_logging.criticals), 5)
                ok_(len(_sleep_count) > 10)
            finally:
                socorro.database.transaction_executor.time.sleep = _orig_sleep

        # this time, simulate an actual code bug where a callable function
        # raises a ProgrammingError() exception by, for example, a syntax error
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)

            def mock_function_developer_mistake(connection):
                assert isinstance(connection, MockConnection)
                connection.transaction_status = \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                raise psycopg2.ProgrammingError("syntax error")

            assert_raises(psycopg2.ProgrammingError,
                              executor,
                              mock_function_developer_mistake)

    def test_abandon_transaction(self):
        """this is when a transaction is intentionally aborted, not because
        of an error, but because the client of the TransactionExcutor has
        determined that the transaction is of no further use."""
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(
                config,
                mocked_context
            )

            class AbandonTransaction(Exception):
                abandon_transaction = True

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                connection.transaction_status = \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                raise AbandonTransaction('crap!')

            # the method to test
            executor(mock_function)

            eq_(commit_count, 0)
            eq_(rollback_count, 1)
            ok_(not mock_logging.errors)

    def test_abandon_backoff_transaction(self):
        """this is when a transaction is intentionally aborted, not because
        of an error, but because the client of the TransactionExcutor has
        determined that the transaction is of no further use.  This test
        uses the TransactionExecutorWithInfiniteBackoff class instead of
        the base TransactionExcutor"""
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithInfiniteBackoff,
          doc='a class that will execute transactions'
        )
        required_config.add_option(
          'database_class',
          default=MockConnectionContext,
          from_string_converter=class_converter
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
          argv_source=[]
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(
                config,
                mocked_context
            )

            class AbandonTransaction(Exception):
                abandon_transaction = True

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                connection.transaction_status = \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                raise AbandonTransaction('crap!')

            # the method to test
            executor(mock_function)

            eq_(commit_count, 0)
            eq_(rollback_count, 1)
            ok_(not mock_logging.errors)

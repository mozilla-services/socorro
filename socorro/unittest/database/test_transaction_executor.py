# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import psycopg2
import mock
from configman import Namespace, ConfigurationManager, class_converter
import socorro.database.transaction_executor
from socorro.database.transaction_executor import (
  TransactionExecutor, TransactionExecutorWithInfiniteBackoff)

from socorro.external.postgresql.connection_context import ConnectionContext


class SomeError(Exception):
    pass


class MockConnectionContext(ConnectionContext):

    def connection(self, __=None):
        return MockConnection()


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


class TestTransactionExecutor(unittest.TestCase):

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

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
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
            self.assertTrue(_function_calls)
            self.assertEqual(commit_count, 1)
            self.assertEqual(rollback_count, 0)

    def test_no_rollback_exception_with_postgres(self):
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

        mock_logging = mock.Mock()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
        )
        with config_manager.context() as config:
            mocked_context = config.database_class(config)
            executor = config.transaction_executor_class(config,
                                                         mocked_context)

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                raise NameError('crap!')

            self.assertRaises(NameError, executor, mock_function)

            self.assertEqual(commit_count, 0)
            self.assertEqual(rollback_count, 0)
            mock_logging.error.assert_called_with(
              'Exception raised during transaction', exc_info=True)

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

        mock_logging = mock.Mock()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[],
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

            self.assertRaises(SomeError, executor, mock_function)

            self.assertEqual(commit_count, 0)
            self.assertEqual(rollback_count, 1)
            mock_logging.error.assert_called_with(
              'Exception raised during transaction', exc_info=True)

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
            self.assertTrue(_function_calls)
            self.assertEqual(commit_count, 1)
            self.assertEqual(rollback_count, 0)

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

        mock_logging = mock.Mock()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'backoff_delays': [2, 4, 6, 10, 15]}],
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
                self.assertTrue(_function_calls)
                self.assertEqual(commit_count, 1)
                self.assertEqual(rollback_count, 0)
                self.assertEqual(len(mock_logging.critical.mock_calls), 5)
                self.assertTrue(len(_sleep_count) > 10)
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

        mock_logging = mock.Mock()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'backoff_delays': [2, 4, 6, 10, 15]}],
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
                self.assertTrue(_function_calls)
                self.assertEqual(commit_count, 1)
                self.assertEqual(rollback_count, 5)
                self.assertEqual(len(mock_logging.critical.mock_calls), 5)
                self.assertTrue(len(_sleep_count) > 10)
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

        mock_logging = mock.Mock()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'backoff_delays': [2, 4, 6, 10, 15]}],
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
                    exp = psycopg2.ProgrammingError()
                    exp.pgerror = 'SSL SYSCALL error: EOF detected'
                    raise exp

            def mock_sleep(n):
                _sleep_count.append(n)

            # monkey patch the sleep function from inside transaction_executor
            _orig_sleep = socorro.database.transaction_executor.time.sleep
            socorro.database.transaction_executor.time.sleep = mock_sleep

            try:
                executor(mock_function_struggling)
                self.assertTrue(_function_calls)
                self.assertEqual(commit_count, 1)
                self.assertEqual(rollback_count, 5)
                self.assertEqual(len(mock_logging.critical.mock_calls), 5)
                self.assertTrue(len(_sleep_count) > 10)
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

            self.assertRaises(psycopg2.ProgrammingError,
                              executor,
                              mock_function_developer_mistake)

import unittest
import psycopg2
from configman import Namespace, ConfigurationManager
import socorro.database.transaction_executor
from socorro.database.transaction_executor import (
  TransactionExecutor, TransactionExecutorWithBackoff)
from socorro.external.postgresql.connection_context import ConnectionContext


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

    def debug(self, *args, **kwargs):
        self.debugs.append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))


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

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockConnectionContext}],
        )
        with config_manager.context() as config:
            executor = config.transaction_executor_class(config)
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
        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockConnectionContext}],
        )
        with config_manager.context() as config:
            executor = config.transaction_executor_class(config)

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                raise NameError('crap!')

            self.assertRaises(NameError, executor, mock_function)

            self.assertEqual(commit_count, 0)
            self.assertEqual(rollback_count, 0)
            self.assertTrue(mock_logging.errors)

    def test_rollback_transaction_exceptions_with_postgres(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockConnectionContext}],
        )
        with config_manager.context() as config:
            executor = config.transaction_executor_class(config)

            def mock_function(connection):
                assert isinstance(connection, MockConnection)
                connection.transaction_status = \
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                raise SomeError('crap!')

            self.assertRaises(SomeError, executor, mock_function)

            self.assertEqual(commit_count, 0)
            self.assertEqual(rollback_count, 1)
            self.assertTrue(mock_logging.errors)

    def test_basic_usage_with_postgres_with_backoff(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithBackoff,
          #default=TransactionExecutor,
          doc='a class that will execute transactions'
        )

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockConnectionContext}],
        )
        with config_manager.context() as config:
            executor = config.transaction_executor_class(config)
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
          default=TransactionExecutorWithBackoff,
          #default=TransactionExecutor,
          doc='a class that will execute transactions'
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockConnectionContext,
                               'backoff_delays': [2, 4, 6, 10, 15]}],
        )
        with config_manager.context() as config:
            executor = config.transaction_executor_class(config)
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
            socorro.database.transaction_executor.time.sleep = mock_sleep

            executor(mock_function)
            self.assertTrue(_function_calls)
            self.assertEqual(commit_count, 1)
            self.assertEqual(rollback_count, 0)
            self.assertTrue(mock_logging.warnings)
            self.assertEqual(len(mock_logging.warnings), 5)
            self.assertTrue(len(_sleep_count) > 10)

    def test_operation_error_with_postgres_with_backoff_with_rollback(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithBackoff,
          #default=TransactionExecutor,
          doc='a class that will execute transactions'
        )

        mock_logging = MockLogging()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockConnectionContext,
                               'backoff_delays': [2, 4, 6, 10, 15]}],
        )
        with config_manager.context() as config:
            executor = config.transaction_executor_class(config)
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
            socorro.database.transaction_executor.time.sleep = mock_sleep

            executor(mock_function)
            self.assertTrue(_function_calls)
            self.assertEqual(commit_count, 1)
            self.assertEqual(rollback_count, 5)
            self.assertTrue(mock_logging.warnings)
            self.assertEqual(len(mock_logging.warnings), 5)
            self.assertTrue(len(_sleep_count) > 10)
            

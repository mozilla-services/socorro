import unittest
import psycopg2
from configman import Namespace, ConfigurationManager
import socorro.database.transaction_executor
from socorro.database.transaction_executor import (
  TransactionExecutor, TransactionExecutorWithBackoff)
from socorro.external.postgresql.transactional import Postgres


class MockPostgres(Postgres):

    def connection(self, __=None):
        return MockConnection()


class MockConnection(object):

    def get_transaction_status(self):
        return 0

    def close(self):
        pass

    def commit(self):
        global commit_count
        commit_count += 1


commit_count = 0


class TestTransactionExecutor(unittest.TestCase):

    def setUp(self):
        global commit_count
        commit_count = 0

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
          values_source_list=[{'database_class': MockPostgres}],
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
          values_source_list=[{'database_class': MockPostgres}],
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

    def test_operation_error_with_postgres_with_backoff(self):
        required_config = Namespace()
        required_config.add_option(
          'transaction_executor_class',
          default=TransactionExecutorWithBackoff,
          #default=TransactionExecutor,
          doc='a class that will execute transactions'
        )
        import logging
        required_config.add_option('logger', default=logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockPostgres}],
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
            self.assertTrue(len(_sleep_count) > 10)

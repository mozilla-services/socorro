from configman import Namespace, ConfigurationManager
from socorro.database.transaction_executor import TransactionExecutor


class MockDatabaseClass(object):
    pass

class TestTransactionExecutor:

    def test_basic_usage_with_postgres(self):
        required_config = Namespace()
#        required_config.add_option('database_class', default=MockDatabaseClass)
        required_config.add_option('transaction_executor_class',
                                   #default=TransactionExecutorWithBackoff,
                                   default=TransactionExecutor,
                                   doc='a class that will execute transactions')
        
        
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'database_class': MockDatabaseClass}],
        )
        with config_manager.context() as config:
            tx = config.transaction_executor_class(config)
            def mock_function(connection):
                print "BLA"
                print "connection", repr(connection)
                return 1
            tx.do_transaction(mock_function)
            
    
        

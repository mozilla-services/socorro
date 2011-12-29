import configman.config_manager as cm
import configman.converters as cnv


#==============================================================================
class DBTransactionApp(cm.RequiredConfig):
    """implementation of an app that does one database transaction and quits"""
    #--------------------------------------------------------------------------
    # configman parameter definiton section
    # here we're setting up the minimal parameters required for connecting
    # to a database.  This configman Option allows the underlying database
    # transaction engine to change at config time.
    required_config = cm.Namespace()
    required_config.add_option(
      name='transaction_class',
      default='socorro.external.postgresql.pgtransaction.PGTransaction',
      doc='the classname of the database transaction',
      from_string_converter=cnv.class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(DBTransactionApp, self).__init__()
        self.config = config

    #--------------------------------------------------------------------------
    def main(self):
        with self.config.db_transaction() as transaction:
            self.do_transaction(transaction)
            transaction.commit()

    #--------------------------------------------------------------------------
    # **** this function should be overridden in a derived class
    # If this function returns without raising an excption, then the
    # transaction is considered to be successful and is commited.
    # If an exception is raised, then the transactions is considered failed
    # and is automatically rolled back.
    def do_transaction(transaction):
        raise Exception('no actions taken in transaction')


#==============================================================================
class StoredProcedureApp(DBTransactionApp):
    """implementation of an app that invokes a stored procedure within a
    transaction and then quits"""
    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(StoredProcedureApp, self).__init__(config)

    #--------------------------------------------------------------------------
    def do_transaction(self, transaction):
        cursor = transaction.cursor()
        parameters = self.stored_procedure_parameters()
        cursor.callproc(self.stored_procedure_name,
                        parameters)

    #--------------------------------------------------------------------------
    # **** this value should be overridden in a derived class
    stored_procedure_name = ''

    #--------------------------------------------------------------------------
    # **** this method should be overridden in a derived class
    def stored_procedure_parameters(self):
        return ()




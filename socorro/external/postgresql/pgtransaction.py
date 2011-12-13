import psycopg2
import psycopg2.extensions
import contextlib

import configman.config_manager as cm


#------------------------------------------------------------------------------
def transaction_context_factory(config_unused,
                                local_namespace,
                                args_unused):
    """a configman aggregating function for Postgres transactions wrapped in
    a contextlib context.

    parameters:
        config_usused - a dict representing the app's entire configuration.
                        this implementation doesn't use them
        local_namespace - a dict representintg the configman Namespace at the
                          local level.
        args_unused - a sequence of commandline arguments.  This implementation
                      doesn't use them"""
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    dsn = ("host=%(database_host)s "
           "dbname=%(database_name)s "
           "port=%(database_port)s "
           "user=%(database_user)s "
           "password=%(database_password)s") % local_namespace

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @contextlib.contextmanager
    def transaction_context():
        conn = psycopg2.connect(dsn)
        try:
            yield conn
        finally:
            status = conn.get_transaction_status()
            if status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                conn.rollback()
            conn.close()
    return transaction_context


#==============================================================================
class PGTransaction(cm.RequiredConfig):
    """a configman complient class for setup of a Postgres transaction"""
    #--------------------------------------------------------------------------
    # configman parameter definition section
    # here we're setting up the minimal parameters required for connecting
    # to a database.
    required_config = cm.Namespace()
    required_config.add_option(
      name='database_host',
      default='localhost',
      doc='the hostname of the database',
    )
    required_config.add_option(
      name='database_name',
      default='breakpad',
      doc='the name of the database',
    )
    required_config.add_option(
      name='database_port',
      default=5432,
      doc='the name of the database',
    )
    required_config.add_option(
      name='database_user',
      default='breakpad_rw',
      doc='the name of the user within the database',
    )
    required_config.add_option(
      name='database_password',
      default='secrets',
      doc='the name of the database',
    )

    # this aggregation takes the preceeding Option definitions and produces a
    # a transaction context object suitable for use in a 'with' statement.
    required_config.add_aggregation(
      name='db_transaction',
      function=transaction_context_factory
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(PGTransaction, self).__init__()
        self.config = config

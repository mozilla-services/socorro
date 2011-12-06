import psycopg2
import psycopg2.extensions

import configman.config_manager as cm


def transaction_context_factory(config_unused,
                                local_namespace,
                                args_unused):
    dsn = ("host=%(database_host)s "
           "dbname=%(database_name)s "
           "port=%(database_port)s "
           "user=%(database_user)s "
           "password=%(database_password)s") % local_namespace
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

class DBTransactionApp(cm.RequiredConfig):
    required_config = Namespace()
    # here we're setting up the minimal parameters required for connecting
    # to a database.
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
    required_config.add_aggregation(
      name='db_transaction',
      function=transaction_context_factory
    )

    def __init__(self, config):
        super(DBTransactionApp, self).__init__()
        self.config = config




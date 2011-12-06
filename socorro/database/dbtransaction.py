import psycopg2
import psycopg2.extensions

import configman.config_manager as cm
import configman.converters as cnv


class DBTransactionApp(cm.RequiredConfig):
    required_config = cm.Namespace()
    # here we're setting up the minimal parameters required for connecting
    # to a database.
    required_config.add_option(
      name='transaction_class',
      default='socorro.external.postgresql.pgtransaction.PGTransaction',
      doc='the classname of the database transaction',
      from_string_converter=cnv.class_converter
    )

    def __init__(self, config):
        super(DBTransactionApp, self).__init__()
        self.config = config




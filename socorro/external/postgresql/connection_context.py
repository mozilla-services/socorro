import threading
import socket
import contextlib
import psycopg2
import psycopg2.extensions

from configman.config_manager import RequiredConfig
from configman import Namespace


class ConnectionContext(RequiredConfig):
    """a configman compliant class for setup of Postgres connections"""
    #--------------------------------------------------------------------------
    # configman parameter definition section
    # here we're setting up the minimal parameters required for connecting
    # to a database.
    required_config = Namespace()
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
        doc='the port for the database',
    )
    required_config.add_option(
        name='database_user',
        default='breakpad_rw',
        doc='the name of the user within the database',
    )
    required_config.add_option(
        name='database_password',
        default='aPassword',
        doc="the user's database password",
    )

    # clients of this class may need to detect Exceptions raised in the
    # underlying dbapi2 database module.  Rather that forcing them to import
    # what should be a hidden module, we expose just the Exception. Clients
    # can then just refer to it as ConnectionContext.IntegrityError
    IntegrityError = psycopg2.IntegrityError

    #--------------------------------------------------------------------------
    def __init__(self, config, local_config=None):
        """Initialize the parts needed to start making database connections

        parameters:
            config - the complete config for the app.  If a real app, this
                     would be where a logger or other resources could be
                     found.
            local_config - this is the namespace within the complete config
                           where the actual database parameters are found"""
        super(ConnectionContext, self).__init__()
        self.config = config
        if local_config is None:
            local_config = config
        self.dsn = ("host=%(database_host)s "
                    "dbname=%(database_name)s "
                    "port=%(database_port)s "
                    "user=%(database_user)s "
                    "password=%(database_password)s") % local_config
        self.operational_exceptions = (
          psycopg2.OperationalError,
          psycopg2.InterfaceError,
          socket.timeout
        )
        self.conditional_exceptions = (
          psycopg2.ProgrammingError,
        )

    #--------------------------------------------------------------------------
    def connection(self, name_unused=None):
        """return a new database connection

        parameters:
            name_unused - optional named connections.  Used by the
                          derived class
        """
        return psycopg2.connect(self.dsn)

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self, name=None):
        """returns a database connection wrapped in a contextmanager.

        The context manager will assure that the connection is closed but will
        not try to commit or rollback lingering transactions.

        parameters:
            name - an optional name for the database connection"""
        #self.config.logger.debug('acquiring connection')
        conn = self.connection(name)
        try:
            #self.config.logger.debug('connection acquired')
            yield conn
        finally:
            #self.config.logger.debug('connection closed')
            self.close_connection(conn)

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        """close the connection passed in.

        This function exists to allow derived classes to override the closing
        behavior.

        parameters:
            connection - the database connection object
            force - unused boolean to force closure; used in derived classes
        """
        connection.close()

    #--------------------------------------------------------------------------
    def close(self):
        """close any pooled or cached connections.  Since this base class
        object does no caching, there is no implementation required.  Derived
        classes may implement it."""
        pass

    #--------------------------------------------------------------------------
    def in_transaction(self, connection):
        """detect if the supplied connection reports that it is in the middle
        of a transaction"""
        return (connection.get_transaction_status() ==
                  psycopg2.extensions.TRANSACTION_STATUS_INTRANS)

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        """return True if a conditional exception is actually an operational
        error. Return False if it's a genuine error that should probably be
        raised and propagate up.

        Some conditional exceptions might be actually be some form of
        operational exception "labelled" wrong by the psycopg2 code error
        handler.
        """
        if msg.pgerror in ('SSL SYSCALL error: EOF detected',):
            # Ideally we'd like to check against msg.pgcode values
            # but certain odd ProgrammingError exceptions don't have
            # pgcodes so we have to rely on reading the pgerror :(
            return True

        # at the of writing, the list of exceptions is short but this would be
        # where you add more as you discover more odd cases of psycopg2

        return False


#==============================================================================
class ConnectionContextPooled(ConnectionContext):  # pragma: no cover
    """a configman compliant class that pools Postgres database connections"""
    #--------------------------------------------------------------------------
    def __init__(self, config, local_config=None):
        super(ConnectionContextPooled, self).__init__(config, local_config)
        #self.config.logger.debug("PostgresPooled - "
        #                         "setting up connection pool")
        self.pool = {}

    #--------------------------------------------------------------------------
    def connection(self, name=None):
        """return a named connection.

        This function will return a named connection by either finding one
        in its pool by the name or creating a new one.  If no name is given,
        it will use the name of the current executing thread as the name of
        the connection.

        parameters:
            name - a name as a string
        """
        if not name:
            name = threading.currentThread().getName()
        if name in self.pool:
            #self.config.logger.debug('connection: %s', name)
            return self.pool[name]
        self.pool[name] = \
            super(ConnectionContextPooled, self).connection(name)
        return self.pool[name]

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        """overriding the baseclass function, this routine will decline to
        close a connection at the end of a transaction context.  This allows
        for reuse of connections."""
        if force:
            try:
                (super(ConnectionContextPooled, self)
                  .close_connection(connection, force))
            except self.operational_exceptions:
                self.config.logger.error('PostgresPooled - failed closing')
            for name, conn in self.pool.iteritems():
                if conn is connection:
                    break
            del self.pool[name]
        else:
            pass
            #self.config.logger.debug('PostgresPooled - refusing to '
                                     #'close connection %s',
                                     #threading.currentThread().getName())

    #--------------------------------------------------------------------------
    def close(self):
        """close all pooled connections"""
        self.config.logger.debug("PostgresPooled - "
                                 "shutting down connection pool")
        for name, conn in self.pool.iteritems():
            conn.close()
            self.config.logger.debug("PostgresPooled - connection %s closed"
                                     % name)

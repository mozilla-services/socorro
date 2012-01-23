import threading
import socket
import contextlib
import psycopg2
import psycopg2.extensions

from configman.config_manager import RequiredConfig
from configman import Namespace


class Postgres(RequiredConfig):
    """a configman compliant class for setup of Postgres transactions"""
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
        default='secrets',
        doc="the user's database password",
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, local_config):
        """Initialize the parts needed to start making database connections

        parameters:
            config - the complete config for the app.  If a real app, this
                     would be where a logger or other resources could be
                     found.
            local_config - this is the namespace within the complete config
                           where the actual database parameters are found"""
        super(Postgres, self).__init__()
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
        conn = self.connection(name)
        try:
            yield conn
        finally:
            self.close_connection(conn)
        
#        exception_raised = False
#        conn = self.connection(name)
#        try:
#            yield conn
#        except self.operational_exceptions:
#            exception_raised = False
#        except Exception:
#            # we need to close the connection
#            exception_raised = True
#        finally:
#            if exception_raised:
#                try:
#                    self.close_connection(conn, force=True)
#                except self.operational_exceptions:
#                    pass
#                raise
#            else:
#                try:
#                    if conn.get_transaction_status() == \
#                      psycopg2.extensions.TRANSACTION_STATUS_INTRANS:
#                        conn.rollback()
#                    self.close_connection(conn)
#                except self.operational_exceptions:
#                    exception_raised = True

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        """close the connection passed in.

        This function exists to allow derived classes to override the closing
        behavior.

        parameters:
            connection - the database connection object
            force - unused boolean to force closure; used in derived classes
        """
        #print "Postgres - requestng connection to close"
        connection.close()

    #--------------------------------------------------------------------------
    def close(self):
        """close any pooled or cached connections.  Since this base class
        object does no caching, there is no implementation required.  Derived
        classes may implement it."""
        pass


#==============================================================================
# This code is NOT in use and is left here intentionally as inspiration 
# towards how to write a pooled postgres class.
# If we don't use this code at the end of 2012, just delete it :)
class PostgresPooled(Postgres):  # pragma: no cover
    """a configman compliant class that pools Postgres database connections"""
    #--------------------------------------------------------------------------
    def __init__(self, config, local_config):
        super(PostgresPooled, self).__init__(config, local_config)
        print "PostgresPooled - setting up connection pool"
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
            return self.pool[name]
        self.pool[name] = FakeDatabaseConnection(self.dsn)
        return self.pool[name]

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        """overriding the baseclass function, this routine will decline to
        close a connection at the end of a transaction context.  This allows
        for reuse of connections."""
        if force:
            print 'PostgresPooled - delegating connection closure'
            try:
                super(PostgresPooled, self).close_connection(connection,
                                                                  force)
            except self.operational_exceptions:
                print 'PostgresPooled - failed closing'
            for name, conn in self.pool.iteritems():
                if conn is connection:
                    break
            del self.pool[name]
        else:
            print 'PostgresPooled - refusing to close connection'

    #--------------------------------------------------------------------------
    def close(self):
        """close all pooled connections"""
        print "PostgresPooled - shutting down connection pool"
        for name, conn in self.pool.iteritems():
            conn.close()
            print "PostgresPooled - connection %s closed" % name

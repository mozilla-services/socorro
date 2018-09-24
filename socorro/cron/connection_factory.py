# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socket
import contextlib
import threading

import psycopg2
import psycopg2.extensions

from configman import Namespace
from configman.config_manager import RequiredConfig


class ConnectionFactory(RequiredConfig):
    """a configman compliant class that pools Postgres database connections"""

    # configman parameter definition section
    # here we're setting up the minimal parameters required for connecting
    # to a database.
    required_config = Namespace()
    required_config.add_option(
        name='host',
        default='localhost',
        doc='the hostname of the database',
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        name='dbname',
        default='',
        doc='the name of the database',
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        name='port',
        default=5432,
        doc='the port for the database',
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        name='user',
        default='',
        doc='the name of the user within the database',
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        name='password',
        default='',
        doc="the user's database password",
        reference_value_from='resource.postgresql',
    )

    # clients of this class may need to detect Exceptions raised in the
    # underlying dbapi2 database module.  Rather that forcing them to import
    # what should be a hidden module, we expose just the Exception. Clients
    # can then just refer to it as ConnectionFactory.IntegrityError
    IntegrityError = psycopg2.IntegrityError

    def __init__(self, config, local_config=None):
        """Initialize the parts needed to start making database connections

        parameters:
            config - the complete config for the app.  If a real app, this
                     would be where a logger or other resources could be
                     found.
            local_config - this is the namespace within the complete config
                           where the actual database parameters are found"""
        super(ConnectionFactory, self).__init__()
        self.config = config
        if local_config is None:
            local_config = config
        self.dsn = (
            "host=%(host)s "
            "dbname=%(dbname)s "
            "port=%(port)s "
            "user=%(user)s "
            "password=%(password)s"
            % local_config
        )
        self.operational_exceptions = (
            psycopg2.OperationalError,
            psycopg2.InterfaceError,
            socket.timeout
        )
        self.conditional_exceptions = (
            psycopg2.ProgrammingError,
        )
        self.pool = {}

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
            name = self._get_default_connection_name()
        if name in self.pool:
            return self.pool[name]
        self.pool[name] = psycopg2.connect(self.dsn)
        return self.pool[name]

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

    def close_connection(self, connection, force=False):
        """overriding the baseclass function, this routine will decline to
        close a connection at the end of a transaction context.  This allows
        for reuse of connections."""
        if force:
            try:
                connection.close()
            except self.operational_exceptions:
                self.config.logger.error('ConnectionFactory - failed closing')
            for name, conn in self.pool.iteritems():
                if conn is connection:
                    break
            del self.pool[name]
        else:
            pass

    def close(self):
        """close all pooled connections"""
        for conn in self.pool.itervalues():
            conn.close()

    def force_reconnect(self):
        name = self._get_default_connection_name()
        if name in self.pool:
            del self.pool[name]

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

    @staticmethod
    def _get_default_connection_name():
        return threading.current_thread().getName()

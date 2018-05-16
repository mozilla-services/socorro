# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import socket
import contextlib
import psycopg2
import psycopg2.extensions
from urlparse import urlparse

from configman import RequiredConfig, Namespace


def get_field_from_pg_database_url(field, default):
    database_url_from_enviroment = os.environ.get('database_url')
    if not database_url_from_enviroment:
        # either database_url is not set or it has an empty value
        return default
    if 'postgres' in database_url_from_enviroment:
        # make sure we respond only to PG URLs
        return getattr(urlparse(database_url_from_enviroment), field, default)
    # it wasn't a PG url
    return default


class ConnectionContext(RequiredConfig):
    """a configman compliant class for setup of Postgres connections"""
    # configman parameter definition section
    # here we're setting up the minimal parameters required for connecting
    # to a database.
    required_config = Namespace()
    required_config.add_option(
        name='database_hostname',
        default=get_field_from_pg_database_url('hostname', 'localhost'),
        doc='the hostname of the database',
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        name='database_name',
        default=get_field_from_pg_database_url('path', ' breakpad')[1:],
        doc='the name of the database',
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        name='database_port',
        default=get_field_from_pg_database_url('port', 5432),
        doc='the port for the database',
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        name='database_username',
        default=get_field_from_pg_database_url('username', 'breakpad_rw'),
        doc='the name of the user within the database',
        reference_value_from='secrets.postgresql',
    )
    required_config.add_option(
        name='database_password',
        default=get_field_from_pg_database_url('password', 'aPassword'),
        doc="the user's database password",
        reference_value_from='secrets.postgresql',
        secret=True,
    )

    # clients of this class may need to detect Exceptions raised in the
    # underlying dbapi2 database module.  Rather that forcing them to import
    # what should be a hidden module, we expose just the Exception. Clients
    # can then just refer to it as ConnectionContext.IntegrityError
    IntegrityError = psycopg2.IntegrityError
    ProgrammingError = psycopg2.ProgrammingError

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
        if local_config['database_port'] is None:
            local_config['database_port'] = 5432
        self.dsn = (
            "host=%(database_hostname)s "
            "dbname=%(database_name)s "
            "port=%(database_port)s "
            "user=%(database_username)s "
            "password=%(database_password)s") % local_config
        self.operational_exceptions = (
            psycopg2.InterfaceError,
            socket.timeout
        )
        self.conditional_exceptions = (
            psycopg2.OperationalError,
            psycopg2.ProgrammingError,
        )

    def connection(self, name_unused=None):
        """return a new database connection

        parameters:
            name_unused - optional named connections.  Used by the
                          derived class
        """
        return psycopg2.connect(self.dsn)

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

    def close_connection(self, connection, force=False):
        """close the connection passed in.

        This function exists to allow derived classes to override the closing
        behavior.

        parameters:
            connection - the database connection object
            force - unused boolean to force closure; used in derived classes
        """
        connection.close()

    def close(self):
        """close any pooled or cached connections.  Since this base class
        object does no caching, there is no implementation required.  Derived
        classes may implement it."""
        pass

    def is_operational_exception(self, exp):
        """return True if a conditional exception is actually an operational
        error. Return False if it's a genuine error that should probably be
        raised and propagate up.

        Some conditional exceptions might be actually be some form of
        operational exception "labelled" wrong by the psycopg2 code error
        handler.
        """
        message = exp.args[0]
        if message in ('SSL SYSCALL error: EOF detected', ):
            # Ideally we'd like to check against exp.pgcode values
            # but certain odd ProgrammingError exceptions don't have
            # pgcodes so we have to rely on reading the pgerror :(
            return True

        if (
            isinstance(exp, psycopg2.OperationalError) and
            message not in ('out of memory',)
        ):
            return True

        # at the of writing, the list of exceptions is short but this would be
        # where you add more as you discover more odd cases of psycopg2

        return False

    def force_reconnect(self):
        pass

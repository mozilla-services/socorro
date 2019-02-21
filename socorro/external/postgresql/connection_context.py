# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import logging
import os
import socket

from configman import RequiredConfig, Namespace
import psycopg2
import psycopg2.extensions
from six.moves.urllib.parse import urlparse


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
    """Postgres Connection Context"""
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

    RETRYABLE_EXCEPTIONS = (
        psycopg2.InterfaceError,
        socket.timeout
    )

    def __init__(self, config, local_config=None):
        """Initialize the parts needed to start making database connections

        parameters:
            config - the complete config for the app.  If a real app, this
                     would be where a logger or other resources could be
                     found.
            local_config - this is the namespace within the complete config
                           where the actual database parameters are found

        """
        super(ConnectionContext, self).__init__()
        self.config = config
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
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

    def connection(self, name_unused=None):
        return psycopg2.connect(self.dsn)

    @contextlib.contextmanager
    def __call__(self, name=None):
        """returns a database connection wrapped in a contextmanager.

        The context manager will assure that the connection is closed but will
        not try to commit or rollback lingering transactions.

        parameters:
            name - an optional name for the database connection
        """
        conn = self.connection(name)
        try:
            yield conn
        finally:
            # self.logger.debug('connection closed')
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
        pass

    def is_retryable_exception(self, exc):
        """Return True if this is a retryable exception"""
        message = exc.args[0]
        if message in ('SSL SYSCALL error: EOF detected', ):
            # Ideally we'd like to check against exc.pgcode values
            # but certain odd ProgrammingError exceptions don't have
            # pgcodes so we have to rely on reading the pgerror :(
            return True

        if isinstance(exc, psycopg2.OperationalError) and message != 'out of memory':
            return True

        return isinstance(exc, self.RETRYABLE_EXCEPTIONS)

    def force_reconnect(self):
        pass

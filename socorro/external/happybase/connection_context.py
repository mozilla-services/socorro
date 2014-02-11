# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import socket
import threading

from configman.config_manager import RequiredConfig
from configman import Namespace

import happybase


#==============================================================================
class HBaseConnection(object):
    """An HBase connection class encapsulating various parts of the underlying
    mechanism to connect to HBase."""
    #--------------------------------------------------------------------------
    def __init__(self, config, connection):
        self.config = config
        self._connection = connection

    #--------------------------------------------------------------------------
    def commit(self):
        pass

    #--------------------------------------------------------------------------
    def rollback(self):
        pass

    #--------------------------------------------------------------------------
    def close(self):
        self._connection.close()

    #--------------------------------------------------------------------------
    def __getattr__(self, name):
        return getattr(self._connection, name)


#==============================================================================
class HappyBaseConnectionContext(RequiredConfig):
    """This class implements a connection to HBase for every transaction to be
    executed.
    """
    required_config = Namespace()
    required_config.add_option(
        'hbase_host',
        doc='Host to HBase server',
        default='localhost',
        reference_value_from='resource.hb',
    )
    required_config.add_option(
        'hbase_port',
        doc='Port to HBase server',
        default=9090,
        reference_value_from='resource.hb',
    )
    required_config.add_option(
        'hbase_timeout',
        doc='timeout in milliseconds for an HBase connection',
        default=5000,
        reference_value_from='resource.hb',
    )
    required_config.add_option(
        'temporary_file_system_storage_path',
        doc='a local filesystem path where dumps temporarily '
            'during processing',
        default='/tmp',
        reference_value_from='resource.hb',
    )
    required_config.add_option(
        'dump_file_suffix',
        doc='the suffix used to identify a dump file (for use in temp files)',
        default='.dump',
        reference_value_from='resource.hb',
    )

    operational_exceptions = (
        happybase.NoConnectionsAvailable,
        socket.timeout,
        socket.error,
    )

    conditional_exceptions = ()

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(HappyBaseConnectionContext, self).__init__()
        self.config = config

    #--------------------------------------------------------------------------
    def connection(self, name=None):
        return HBaseConnection(
            self.config,
            happybase.Connection(
                host=self.config.hbase_host,
                port=self.config.hbase_port,
                timeout=self.config.hbase_timeout
            )
        )

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self, name=None):
        conn = self.connection(name)
        try:
            yield conn
        finally:
            self.close_connection(conn)

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        pass

    #--------------------------------------------------------------------------
    def close(self):
        pass

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        connection.close()

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        return False


#==============================================================================
class HappyBasePooledConnectionContext(HappyBaseConnectionContext):
    """This class implements a connection to HBase for every transaction to be
    executed.
    """

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(HappyBasePooledConnectionContext, self).__init__(config)
        self._connection_pool = happybase.ConnectionPool(
            20,  # TODO: how to get this number imported from the taskmanager
            host=self.config.hbase_host,
            port=self.config.hbase_port,
            timeout=self.config.hbase_timeout
        )

    #--------------------------------------------------------------------------
    def connection(self, name=None):
        raise Exception('must use context manager')

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self, name=None):
        with self._connection_pool.connection() as connection:
            yield HBaseConnection(self.config, connection)


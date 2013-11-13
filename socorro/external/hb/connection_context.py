# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import socket
import threading

from configman.config_manager import RequiredConfig
from configman import Namespace

from thrift import Thrift
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from hbase.Hbase import Client
import hbase.ttypes


#==============================================================================
class HBaseConnection(object):
    """An HBase connection class encapsulating various parts of the underlying
    mechanism to connect to HBase."""
    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.make_connection()

    #--------------------------------------------------------------------------
    def commit(self):
        pass

    #--------------------------------------------------------------------------
    def rollback(self):
        pass

    #--------------------------------------------------------------------------
    def make_connection(self):
        self.socket = TSocket.TSocket(self.config.hbase_host,
                                      self.config.hbase_port)
        self.socket.setTimeout(self.config.hbase_timeout)
        self.transport = TTransport.TBufferedTransport(self.socket)
        self.protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
        self.client = Client(self.protocol)
        self.transport.open()

    #--------------------------------------------------------------------------
    def close(self):
        self.transport.close()


#==============================================================================
class HBaseConnectionContext(RequiredConfig):
    """This class implements a connection to HBase for every transaction to be
    executed.
    """
    required_config = Namespace()
    required_config.add_option(
        'hbase_host',
        doc='Host to HBase server',
        default='localhost',
    )
    required_config.add_option(
        'hbase_port',
        doc='Port to HBase server',
        default=9090,
    )
    required_config.add_option(
        'hbase_timeout',
        doc='timeout in milliseconds for an HBase connection',
        default=5000,
    )
    required_config.add_option(
        'temporary_file_system_storage_path',
        doc='a local filesystem path where dumps temporarily '
            'during processing',
        default='/tmp',
    )
    required_config.add_option(
        'dump_file_suffix',
        doc='the suffix used to identify a dump file (for use in temp files)',
        default='.dump'
    )

    operational_exceptions = (
        hbase.ttypes.IOError,
        Thrift.TException,
        socket.timeout,
        socket.error,
    )

    conditional_exceptions = ()

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(HBaseConnectionContext, self).__init__()
        self.config = config

    #--------------------------------------------------------------------------
    def connection(self, name=None):
        return HBaseConnection(self.config)

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
class HBasePooledConnectionContext(HBaseConnectionContext):
    """a configman compliant class that pools HBase database connections"""
    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(HBasePooledConnectionContext, self).__init__(config)
        #self.config.logger.debug("HBasePooledConnectionContext - "
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
            return self.pool[name]
        self.pool[name] = \
            super(HBasePooledConnectionContext, self).connection(name)
        return self.pool[name]

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        """overriding the baseclass function, this routine will decline to
        close a connection at the end of a transaction context.  This allows
        for reuse of connections."""
        if force:
            try:
                (super(HBasePooledConnectionContext, self)
                  .close_connection(connection, force))
            except self.operational_exceptions:
                self.config.logger.error(
                    'HBasePooledConnectionContext - failed closing'
                )
            for name, conn in self.pool.iteritems():
                if conn is connection:
                    break
            del self.pool[name]

    #--------------------------------------------------------------------------
    def close(self):
        """close all pooled connections"""
        self.config.logger.debug(
            "HBasePooledConnectionContext - shutting down connection pool"
        )
        # force a list, we're changing the pool as we iterate
        for name, connection in list(self.pool.iteritems()):
            self.close_connection(connection, force=True)
            self.config.logger.debug(
                "HBasePooledConnectionContext - connection %s closed",
                name
            )

    #--------------------------------------------------------------------------
    def force_reconnect(self, name=None):
        """tell this functor that the next time it gives out a connection
        under the given name, it had better make sure it is brand new clean
        connection.  Use this when you discover that your connection has
        gone bad and you want to report that fact to the appropriate
        authority.  You are responsible for actually closing the connection or
        not, if it is really hosed."""
        if name is None:
            name = threading.currentThread().getName()
        if name in self.pool:
            del self.pool[name]

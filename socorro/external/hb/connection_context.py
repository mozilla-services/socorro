# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib

from configman.config_manager import RequiredConfig
from configman import Namespace

from thrift import Thrift
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from hbase.Hbase import Client


class HBaseConnection(object):
    """An HBase connection class encapsulating various parts of the underlying
    mechanism to connect to HBase."""
    def __init__(self, config):
        self.config = config
        self.make_connection()

    def commit(self):
        pass

    def rollback(self):
        pass

    def in_transaction(self, dummy):
        return False

    def is_operational_exception(self, msg):
        return True

    def make_connection(self):
        self.socket = TSocket.TSocket(self.config.hbase_host,
                                      self.config.hbase_port)
        self.socket.setTimeout(self.config.hbase_timeout)
        self.transport = TTransport.TBufferedTransport(self.socket)
        self.protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
        self.client = Client(self.protocol)
        self.transport.open()

    def close(self):
        self.transport.close()


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
        'forbidden_keys',
        default='email, url, user_id, exploitability',
        doc='a comma delimited list of keys banned from the processed crash '
            'in HBase',
        from_string_converter=lambda s: [x.strip() for x in s.split(',')]
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

    def __init__(self, config):
        super(HBaseConnectionContext, self).__init__()
        self.config = config

    def connection(self, name=None):
        return HBaseConnection(self.config)

    @contextlib.contextmanager
    def __call__(self, name=None):
        conn = self.connection(name)
        try:
            yield conn
        finally:
            self.close_connection(conn)

    def close(self):
        pass

    def close_connection(self, connection):
        connection.close()

    def in_transaction(self, connection):
        return True

    def is_operational_exception(self, msg):
        return False


class HBasePersistentConnectionContext(HBaseConnectionContext):
    """This class implements a persistent connection to HBase.
    """
    def __init__(self, config):
        super(HBasePersistentConnectionContext, self).__init__(self)
        self.conn = super(HBasePersistentConnectionContext, self).connection()

    def connection(self):
        return self.conn

    @contextlib.contextmanager
    def __call__(self):
        # don't close the connection!
        yield self.conn

    def close(self):
        self.close_connection(self.conn)

    def in_transaction(self, connection):
        return False

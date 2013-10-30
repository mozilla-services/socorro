# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import threading
import contextlib

from socorro.external.hbase import hbase_client
from configman.config_manager import RequiredConfig
from configman import Namespace


class HBaseSingleConnectionContext(RequiredConfig):
    """a configman compliant class for setup of HBase connections
    DO NOT SHARE HBASE CONNECTIONS BETWEEN THREADS
    """
    #--------------------------------------------------------------------------
    # configman parameter definition section
    # here we're setting up the minimal parameters required for connecting
    required_config = Namespace()
    required_config.add_option(
        'number_of_retries',
        doc='Max. number of retries when fetching from hbaseClient',
        default=0
    )
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
        default='/home/socorro/temp',
    )
    required_config.add_option(
        'dump_file_suffix',
        doc='the suffix used to identify a dump file (for use in temp files)',
        default='.dump'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, local_config=None):
        """Initialize the parts needed to start making database connections

        parameters:
            config - the complete config for the app.  If a real app, this
                     would be where a logger or other resources could be
                     found.
            local_config - this is the namespace within the complete config
                           where the actual database parameters are found"""
        super(HBaseSingleConnectionContext, self).__init__()
        self.config = config
        if local_config is None:
            local_config = config

        dummy_connection = hbase_client.HBaseConnectionForCrashReports(
            local_config.hbase_host,
            local_config.hbase_port,
            local_config.hbase_timeout,
            logger=self.config.logger
        )
        dummy_connection.close()
        self.operational_exceptions = \
            dummy_connection.hbaseThriftExceptions
        self.operational_exceptions += \
            (hbase_client.NoConnectionException,)
        self.conditional_exceptions = ()

    #--------------------------------------------------------------------------
    def connection(self, name_unused=None):
        """return a new database connection

        parameters:
            name_unused - optional named connections.  Used by the
                          derived class
        """
        #self.config.logger.debug('creating new HBase connection')
        return hbase_client.HBaseConnectionForCrashReports(
            self.config.hbase_host,
            self.config.hbase_port,
            self.config.hbase_timeout,
            logger=self.config.logger
        )

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
            #self.config.logger.debug('connection HBase acquired')
            yield conn
        finally:
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
        #self.config.logger.debug('connection HBase closed')
        connection.close()

    #--------------------------------------------------------------------------
    def close(self):
        """close any pooled or cached connections.  Since this base class
        object does no caching, there is no implementation required.  Derived
        classes may implement it."""
        pass

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        """return True if a conditional exception is actually an operational
        error. Return False if it's a genuine error that should probably be
        raised and propagate up.

        Some conditional exceptions might be actually be some form of
        operational exception "labelled" wrong by the psycopg2 code error
        handler.
        """

        return False

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        pass


#==============================================================================
class HBaseConnectionContextPooled(HBaseSingleConnectionContext):
    """a configman compliant class that pools HBase database connections"""
    #--------------------------------------------------------------------------
    def __init__(self, config, local_config=None):
        super(HBaseConnectionContextPooled, self).__init__(config,
                                                           local_config)
        #self.config.logger.debug("HBaseConnectionContextPooled - "
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
            super(HBaseConnectionContextPooled, self).connection(name)
        return self.pool[name]

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        """overriding the baseclass function, this routine will decline to
        close a connection at the end of a transaction context.  This allows
        for reuse of connections."""
        if force:
            try:
                (super(HBaseConnectionContextPooled, self)
                  .close_connection(connection, force))
            except self.operational_exceptions:
                self.config.logger.error('HBaseConnectionContextPooled - '
                                         'failed closing')
            for name, conn in self.pool.iteritems():
                if conn is connection:
                    break
            del self.pool[name]

    #--------------------------------------------------------------------------
    def close(self):
        """close all pooled connections"""
        self.config.logger.debug("HBasePooled - "
                                 "shutting down connection pool")
        for name, conn in self.pool.iteritems():
            conn.close()
            self.config.logger.debug("HBasePooled - connection %s closed"
                                     % name)

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        pass

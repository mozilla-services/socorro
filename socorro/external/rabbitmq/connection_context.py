# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import threading
import socket
import contextlib

import pika

from configman.config_manager import RequiredConfig
from configman import Namespace


class ConnectionContext(RequiredConfig):
    """a configman compliant class for setup of RabbitMQ connections"""
    #--------------------------------------------------------------------------
    # configman parameter definition section
    # here we're setting up the minimal parameters required for connecting
    # to a RabbitMQ server.
    required_config = Namespace()
    required_config.add_option(
        name='host',
        default='localhost',
        doc='the hostname of the RabbitMQ server',
    )
    required_config.add_option(
        name='virtual_host',
        default='/',
        doc='the name of the RabbitMQ virtual host',
    )
    required_config.add_option(
        name='port',
        default=5672,
        doc='the port for the RabbitMQ server',
    )
    required_config.add_option(
        name='rabbitmq_user',
        default='guest',
        doc='the name of the user within the RabbitMQ instance',
    )
    required_config.add_option(
        name='rabbitmq_password',
        default='guest',
        doc="the user's RabbitMQ password",
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, local_config=None):
        """Initialize the parts needed to start making RabbitMQ connections

        parameters:
            config - the complete config for the app.  If a real app, this
                     would be where a logger or other resources could be
                     found.
            local_config - this is the namespace within the complete config
                           where the actual RabbitMQ parameters are found"""
        super(ConnectionContext, self).__init__()
        self.config = config
        if local_config is None:
            local_config = config
        
        credentials = pika.credentials.PlainCredentials(local_config.rabbitmq_user, 
                                                        local_config.rabbitmq_password)
        
        self.connection_params = pika.ConnectionParamters(
                                    host=local_config.host,
                                    port=local_config.port,
                                    virtual_host=local_config.virtual_host,
                                    credentials=credentials
                                 )
        
        self.conn = pika.BlockingConnection(self.connection_params)
        
        self.operational_exceptions = (
          pika.exceptions.AMQPConnectionError,
          pika.exceptions.ChannelClosed,
          pika.exceptions.ConnectionClosed,
          pika.exceptions.NoFreeChannels,
          
          socket.timeout
        )

    #--------------------------------------------------------------------------
    def connection(self, name_unused=None):
        """return a new RabbitMQ connection

        parameters:
            name_unused - optional named connections.  Used by the
                          derived class
        """
                
        return self.conn.channel()

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self, name=None):
        """returns a RabbitMQ connection wrapped in a contextmanager.

        The context manager will assure that the connection is closed but will
        not try to commit or rollback lingering transactions.

        parameters:
            name - an optional name for the RabbitMQ connection"""
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
            connection - the RabbitMQ connection object
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
    def force_reconnect(self):
        pass


#==============================================================================
class ConnectionContextPooled(ConnectionContext):  # pragma: no cover
    """a configman compliant class that pools RabbitMQ connections"""
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
                self.config.logger.error('RabbitMQPooled - failed closing')
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
        self.config.logger.debug("RabbitMQPooled - "
                                 "shutting down connection pool")
        for name, channel in self.pool.iteritems():
            channel.close()
            self.config.logger.debug("RabbitMQPooled - channel %s closed"
                                     % name)
        
        self.conn.close()

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        name = threading.currentThread().getName()
        if name in self.pool:
            del self.pool[name]

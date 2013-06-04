# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import threading
import socket
import contextlib
import pika

from configman.config_manager import RequiredConfig
from configman import Namespace


class Connection(object):
    """A facade around a RabbitMQ channel that standardizes certain gross
    elements of its API with those of other connection types."""

    def __init__(self, config, connection):
        """Construct.

        parameters:
            config - A configman config
            connection - A RabbitMQ BlockingConnection from which we can derive
                channels
        """
        self.config = config
        self.connection = connection
        self.channel = connection.channel()
        self.channel.queue_declare(queue='socorro.normal', durable=True)
        self.channel.queue_declare(queue="socorro.priority", durable=True)
        # I'm not very happy about things having to reach inside me and prod
        # self.channel directly to get anything done, but I think there's a
        # greater architectural issue to solve here: none of these Connection
        # objects abstract their connections fully.

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.connection.close()


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
        self.conditional_exceptions = ()
        self.config = config
        if local_config is None:
            local_config = config

        self.conn = pika.BlockingConnection(pika.ConnectionParameters(
            host=local_config.host,
            port=local_config.port,
            virtual_host=local_config.virtual_host,
            credentials=pika.credentials.PlainCredentials(
                local_config.rabbitmq_user,
                local_config.rabbitmq_password)))

        self.operational_exceptions = (
          pika.exceptions.AMQPConnectionError,
          pika.exceptions.ChannelClosed,
          pika.exceptions.ConnectionClosed,
          pika.exceptions.NoFreeChannels,
          socket.timeout)

    #--------------------------------------------------------------------------
    def connection(self, name=None):
        """Return a new RabbitMQ Connection.

        parameters:
            name - unused
        """
        return Connection(self.config, self.conn)

    #--------------------------------------------------------------------------
    # TODO: Factor this and close_connection (at least) up to a superclass.
    @contextlib.contextmanager
    def __call__(self, name=None):
        """returns a RabbitMQ connection wrapped in a contextmanager.

        The context manager will assure that the connection is closed but will
        not try to commit or rollback lingering transactions.

        parameters:
            name - an optional name for the RabbitMQ connection"""
        conn = self.connection(name)
        try:
            yield conn
        finally:
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

    def is_operational_exception(self, msg):
        # TODO: Should we check against self.operational_exceptions here?
        return False


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


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import threading
import socket
import contextlib
import pika

from configman.config_manager import RequiredConfig
from configman import Namespace


#==============================================================================
class Connection(object):
    """A facade in front of a RabbitMQ channel that standardizes certain gross
    elements of its API with those of other connection types.  Clients of this
    class get access to some general behaviors that typically used in the
    Transaction classes.  Drilling down to the actual underlying connection
    for implementation of more specific behaviors is encouraged. This class is
    not intended to be instantiated by clients of this module, though it is
    not forbidden.  Instances of this class are returned by the connection
    context factories ConnectionContext and ConnectionContextPooled below.
    This class is as thread safe as the underlying connection - as of 2013,
    that means not thread safe.
    """

    #--------------------------------------------------------------------------
    def __init__(self, config,  connection,
                 standard_queue_name='socorro.normal',
                 priority_queue_name='socorro.priority'):
        """Construct.

        parameters:
            config - a mapping containing
            connection - A RabbitMQ BlockingConnection from which we can derive
                channels
        """
        self.config = config
        self.connection = connection
        self.channel = connection.channel()
        self.channel.queue_declare(queue=standard_queue_name, durable=True)
        self.channel.queue_declare(queue=priority_queue_name, durable=True)

        # I'm not very happy about things having to reach inside me and prod
        # self.channel directly to get anything done, but I think there's a
        # greater architectural issue to solve here: none of these Connection
        # objects abstract their connections fully.

        # lars: we don't want to fully abstract connections at this level.
        # This is an internal use class to assist in the implementation of
        # RabbitMQ resource specific behaviors. Other modules within this
        # RabbitMQ package are free to use this class or not.  Using this
        # class is not meant to preclude using the low level RabbitMQ api.
        # It provides simple access to the underlying connection as well as
        # adding some common semantics to aid the implementation of the fully
        # abstracted RabbitMQCrashStorage class.

    #--------------------------------------------------------------------------
    def commit(self):
        pass

    #--------------------------------------------------------------------------
    def rollback(self):
        pass

    #--------------------------------------------------------------------------
    def close(self):
        self.connection.close()


#==============================================================================
class ConnectionContext(RequiredConfig):
    """A factory object in the form of a functor.  It returns connections
    to RabbitMQ wrapped in the minimal Connection class above.  Suitable for
    use in a "with" statment this class will handle opening a connection to
    RabbitMQ and its subsequent closure.  Use this class only when connections
    are never reused outside of the context for which they were created."""
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
    required_config.add_option(
        name='standard_queue_name',
        default='socorro.normal',
        doc="the name of standard crash queue name within RabbitMQ",
    )
    required_config.add_option(
        name='priority_queue_name',
        default='socorro.priority',
        doc="the name of priority crash queue name within RabbitMQ",
    )
    required_config.add_option(
        name='rabbitmq_connection_wrapper_class',
        default=Connection,
        doc="a classname for the type of wrapper for RabbitMQ connections",
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
        self.local_config = local_config

        # if a connection raises one of these exceptions, then they are
        # considered to be retriable exceptions.  This class does not implement
        # any retry behaviors itself, but just provides this information
        # about the connections it produces.  This is to facilitate a client
        # of this class to define its own retry or transaction behavior.
        # The information is used by the TransactionExector classes
        self.operational_exceptions = (
          pika.exceptions.AMQPConnectionError,
          pika.exceptions.ChannelClosed,
          pika.exceptions.ConnectionClosed,
          pika.exceptions.NoFreeChannels,
          socket.timeout)
        # conditional exceptions are amibiguous in their eligibilty to
        # trigger a retry behavior.  They're listed here so that custom code
        # written in the 'is_operational_exception' method can examine them
        # more closel and make the determination.  No ambiguous exceptions
        # have been identified, if and or when they are identified, they should
        # be entered here.
        self.conditional_exceptions = ()

    #--------------------------------------------------------------------------
    def connection(self, name=None):
        """create a new RabbitMQ connection, set it up for our queues, then
        return it wrapped with our connection class.

        parameters:
            name - unused in this context
        """
        bare_rabbitmq_connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.local_config.host,
                port=self.local_config.port,
                virtual_host=self.local_config.virtual_host,
                credentials=pika.credentials.PlainCredentials(
                    self.local_config.rabbitmq_user,
                    self.local_config.rabbitmq_password
                )
            )
        )
        wrapped_connection = \
            self.local_config.rabbitmq_connection_wrapper_class(
                self.config,
                bare_rabbitmq_connection,
                self.local_config.standard_queue_name,
                self.local_config.priority_queue_name,
            )
        return wrapped_connection

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self, name=None):
        """returns a RabbitMQ connection wrapped in a contextmanager.

        The context manager will assure that the connection is closed but will
        not try to commit or rollback lingering transactions.

        parameters:
            name - an optional name for the RabbitMQ connection"""
        wrapped_rabbitmq_connection = self.connection(name)
        try:
            yield wrapped_rabbitmq_connection
        finally:
            self.close_connection(wrapped_rabbitmq_connection)

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
        """since this class uses a model where connections are opened and
        closed within the bounds of a context manager, this method is a
        No Op.  Derived classes may choose to do otherwise."""
        pass

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        """Sometimes a resource connection can raise an ambiguous exception.
        The exception could either be an OperationalException (therefore
        eligible to be retried) or an unrecoverable exception.  This function
        is for implementation of code that make the determination.  No such
        exception have yet been identified.  """
        return False


#==============================================================================
class ConnectionContextPooled(ConnectionContext):
    """A factory object in the form of a functor.  It returns connections
    to RabbitMQ wrapped in the minimal Connection class above.  It implements
    connection pooling behavior based on naming connections.  If no name is
    given when requesting a connection, then the current executing thread
    name is used.  This means that a given thread will always be guaranteed
    to get the same open connection each time a connection context is produced
    by this functor.  This ensures thread safety for RabbitMQ's unsafe
    connections.
    """
    #--------------------------------------------------------------------------
    def __init__(self, config, local_config=None):
        super(ConnectionContextPooled, self).__init__(config, local_config)
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
            #self.config.logger.debug('fetching RMQ connection: %s', name)
            return self.pool[name]
        self.config.logger.debug('creating new RMQ connection: %s', name)
        self.pool[name] = \
            super(ConnectionContextPooled, self).connection(name)
        return self.pool[name]

    #--------------------------------------------------------------------------
    def close_connection(self, connection, force=False):
        """overriding the baseclass function, this routine will decline to
        close a connection at the end of a connection context.  This allows
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

    #--------------------------------------------------------------------------
    def close(self):
        """close all pooled connections"""
        self.config.logger.debug(
            "RabbitMQPooled - shutting down connection pool"
        )
        for name, connection in list(self.pool.iteritems()):
            self.close_connection(connection, force=True)
            self.config.logger.debug(
                "RabbitMQPooled - channel %s closed",
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


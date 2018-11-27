# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socket
import contextlib
import pika

from configman import Namespace, RequiredConfig


class Connection(object):
    """A facade in front of a RabbitMQ channel that standardizes certain gross
    elements of its API with those of other connection types.

    This class is not intended to be instantiated by clients of this module,
    though it is not forbidden. Instances of this class are returned by the
    connection context factories ConnectionContext and ConnectionContextPooled
    below. This class is as thread safe as the underlying connection - as of
    2013, that means not thread safe.

    """

    def __init__(self, config, connection,
                 standard_queue_name='socorro.normal',
                 priority_queue_name='socorro.priority',
                 reprocessing_queue_name='socorro.reprocessing'):
        """Construct.

        parameters:
            config - a mapping containing
            connection - A RabbitMQ BlockingConnection from which we can derive
                channels
        """
        self.config = config
        self.connection = connection
        self.channel = connection.channel()
        self.queue_status_standard = self.channel.queue_declare(
            queue=standard_queue_name, durable=True
        )
        self.queue_status_priority = self.channel.queue_declare(
            queue=priority_queue_name, durable=True
        )
        self.queue_status_reprocessing = self.channel.queue_declare(
            queue=reprocessing_queue_name, durable=True
        )

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

    def close(self):
        self.connection.close()


class ConnectionContext(RequiredConfig):
    """A factory object in the form of a functor.  It returns connections
    to RabbitMQ wrapped in the minimal Connection class above.  Suitable for
    use in a "with" statment this class will handle opening a connection to
    RabbitMQ and its subsequent closure.  Use this class only when connections
    are never reused outside of the context for which they were created.

    """
    required_config = Namespace()
    required_config.add_option(
        name='host',
        default='localhost',
        doc='the hostname of the RabbitMQ server',
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        name='virtual_host',
        default='/',
        doc='the name of the RabbitMQ virtual host',
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        name='port',
        default=5672,
        doc='the port for the RabbitMQ server',
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        name='rabbitmq_user',
        default='guest',
        doc='the name of the user within the RabbitMQ instance',
        reference_value_from='secrets.rabbitmq',
    )
    required_config.add_option(
        name='rabbitmq_password',
        default='guest',
        doc="the user's RabbitMQ password",
        reference_value_from='secrets.rabbitmq',
        secret=True,
    )
    required_config.add_option(
        name='standard_queue_name',
        default='socorro.normal',
        doc="the name of standard crash queue name within RabbitMQ",
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        name='priority_queue_name',
        default='socorro.priority',
        doc="the name of priority crash queue name within RabbitMQ",
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        name='reprocessing_queue_name',
        default='socorro.reprocessing',
        doc="the name of reprocessing crash queue name within RabbitMQ",
    )
    required_config.add_option(
        name='rabbitmq_connection_wrapper_class',
        default=Connection,
        doc="a classname for the type of wrapper for RabbitMQ connections",
        reference_value_from='resource.rabbitmq',
    )

    # These exceptions indicate the connection should get closed and a new
    # one created and the operation retried
    RETRYABLE_EXCEPTIONS = (
        pika.exceptions.AMQPConnectionError,
        pika.exceptions.ChannelClosed,
        pika.exceptions.ConnectionClosed,
        pika.exceptions.NoFreeChannels,
        socket.timeout
    )

    def __init__(self, config, local_config=None):
        """Initialize the parts needed to start making RabbitMQ connections

        parameters:
            config - the complete config for the app.  If a real app, this
                     would be where a logger or other resources could be
                     found.
            local_config - this is the namespace within the complete config
                           where the actual RabbitMQ parameters are found
        """
        super(ConnectionContext, self).__init__()
        self.config = config
        if local_config is None:
            local_config = config
        self.local_config = local_config

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
        wrapped_connection = self.local_config.rabbitmq_connection_wrapper_class(
            self.config,
            bare_rabbitmq_connection,
            self.local_config.standard_queue_name,
            self.local_config.priority_queue_name,
            self.local_config.reprocessing_queue_name,
        )
        return wrapped_connection

    @contextlib.contextmanager
    def __call__(self, name=None):
        """returns a RabbitMQ connection wrapped in a contextmanager.

        The context manager will assure that the connection is closed but will
        not try to commit or rollback lingering transactions.

        parameters:
            name - an optional name for the RabbitMQ connection

        """
        wrapped_rabbitmq_connection = self.connection(name)
        try:
            yield wrapped_rabbitmq_connection
        finally:
            self.close_connection(wrapped_rabbitmq_connection)

    def close_connection(self, connection, force=False):
        """close the connection passed in.

        This function exists to allow derived classes to override the closing
        behavior.

        parameters:
            connection - the RabbitMQ connection object
            force - unused boolean to force closure; used in derived classes
        """
        connection.close()

    def close(self):
        """close any pooled or cached connections.  Since this base class
        object does no caching, there is no implementation required.  Derived
        classes may implement it
        """
        pass

    def force_reconnect(self):
        """Force reconnect

        This is a no-op because connections get created and destroyed in the
        contextmanager.

        """
        pass

    def is_retryable_exception(self, exc):
        return isinstance(exc, self.RETRYABLE_EXCEPTIONS)


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
    def __init__(self, config, local_config=None):
        super(ConnectionContextPooled, self).__init__(config, local_config)
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
            name = self.config.executor_identity()
        if name in self.pool:
            return self.pool[name]
        self.config.logger.debug('creating new RMQ connection: %s', name)
        self.pool[name] = super(ConnectionContextPooled, self).connection(name)
        return self.pool[name]

    def close_connection(self, connection, force=False):
        """Closes a connection only if forced

        This allows reuse of connections created in the contextmanager.

        """
        if force:
            try:
                super(ConnectionContextPooled, self).close_connection(connection, force)
            except self.operational_exceptions:
                self.config.logger.error('RabbitMQPooled - failed closing')
            for name, conn in list(self.pool.items()):
                if conn is connection:
                    break
            del self.pool[name]

    def close(self):
        """Close all pooled connections"""
        self.config.logger.debug('RabbitMQPooled - shutting down connection pool')
        for name, connection in list(self.pool.items()):
            self.close_connection(connection, force=True)
            self.config.logger.debug('RabbitMQPooled - channel %s closed', name)

    def force_reconnect(self, name=None):
        """Force reconnect"""
        if name is None:
            name = self.config.executor_identity()
        if name in self.pool:
            del self.pool[name]

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pika
from Queue import (
    Queue,
    Empty
)

from configman import (
    Namespace,
    class_converter
)
from socorro.external.rabbitmq.connection_context import (
    ConnectionContextPooled
)
from socorro.external.crashstorage_base import (
    CrashStorageBase,
)


#==============================================================================
class RabbitMQCrashStorage(CrashStorageBase):
    """This class is an implementation of a Socorro Crash Storage system.
    It is used as a crash queing methanism for raw crashes.  It implements
    the save_raw_crash method as a queue submission function, and the
    new_crashes generator as a queue consumption function.  Please note: as
    it only queues the crash_id and not the whole raw crash, it is not suitable
    to actually save a crash.  It is a very lossy container.  This class
    should be used in conjuction with a more persistant storage mechanism.

    The implementations CrashStorage classes can use arbitrarly high or low
    level semantics to talk to their underlying resource.  In the RabbitMQ,
    implementation, queing through the 'save_raw_crash' method is given full
    transactional semantics using the TransactorExecutor classes.  The
    'new_crashes' generator has a lower level relationship with the
    underlying connection object"""

    required_config = Namespace()
    required_config.add_option(
        'rabbitmq_class',
        default=ConnectionContextPooled,  # we choose a pooled connection
                                          # because we need thread safe
                                          # connection behaviors
        doc='the class responsible for connecting to RabbitMQ'
    )
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'routing_key',
        default='socorro.normal',
        doc='the name of the queue to recieve crashes'
    )
    required_config.add_option(
        'filter_on_legacy_processing',
        default=True,
        doc='toggle for using or ignoring the throttling flag'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(RabbitMQCrashStorage, self).__init__(
            config,
            quit_check_callback=quit_check_callback
        )

        # Note: this may continue to grow if we aren't acking certain UUIDs.
        # We should find a way to time out UUIDs after a certain time.
        self.acknowledgement_token_cache = {}
        self.acknowledgment_queue = Queue()

        self.rabbitmq = config.rabbitmq_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.rabbitmq,
            quit_check_callback=quit_check_callback
        )

        # cache this object so we don't have to remake it for every transaction
        self._basic_properties = pika.BasicProperties(
            delivery_mode = 2, # make message persistent
        )

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        try:
            this_crash_should_be_queued = (
                (not self.config.filter_on_legacy_processing)
                or
                raw_crash.legacy_processing == 0
            )
        except KeyError:
            self.config.logger.debug(
                'RabbitMQCrashStorage legacy_processing key absent in crash '
                '%s', crash_id
            )
            return

        if this_crash_should_be_queued:
            self.transaction(self._save_raw_crash_transaction, crash_id)
        else:
            self.config.logger.debug(
                'RabbitMQCrashStorage not saving crash %s, legacy processing '
                'flag is %s', crash_id, raw_crash.legacy_processing
            )

    #--------------------------------------------------------------------------
    def _save_raw_crash_transaction(self, connection, crash_id):
        connection.channel.basic_publish(
            exchange='',
            routing_key=self.config.routing_key,
            body=crash_id,
            properties=self._basic_properties
        )

    #--------------------------------------------------------------------------
    def new_crashes(self):
        """This generator fetches crash_ids from RabbitMQ."""

        # We've set up RabbitMQ to require acknowledgement of processing of a
        # crash_id form this generator.  It is the respsonsibility of the
        # consumer of the crash_id to tell this instance of the class when has
        # completed its work on the crash_id.  That is done with the call to
        # 'ack_crash' below.  Because RabbitMQ connections are not thread safe,
        # only the thread that read the crash may acknowledge it.  'ack_crash'
        # queues the crash_id. The '_consume_acknowledgement_queue' function
        # is run to send acknowledgments back to RabbitMQ=
        self._consume_acknowledgement_queue()
        connection = self.rabbitmq.connection()
        data = connection.channel.basic_get(queue="socorro.priority")
        # RabbitMQ gives us: (channel information, meta information, payload)
        if data == (None, None, None):
            data = connection.channel.basic_get(queue="socorro.normal")
        while data != (None, None, None):
            self._consume_acknowledgement_queue()
            # Something terrible is happening right here
            self.acknowledgement_token_cache[data[2]] = data[0]
            yield data[2]
            data = connection.channel.basic_get(queue="socorro.priority")
            if data == (None, None, None):
                data = connection.channel.basic_get(queue="socorro.normal")

    #--------------------------------------------------------------------------
    def ack_crash(self, crash_id):
        self.acknowledgment_queue.put(crash_id)

    #--------------------------------------------------------------------------
    def _consume_acknowledgement_queue(self):
        """The acknowledgement of the processing of each crash_id yielded
        from the 'new_crashes' method must take place on the same connection
        that the crash_id came from.  The crash_ids are queued in the
        'acknowledgment_queue'.  That queue is consumed by the QueuingThread"""
        try:
            while True:
                crash_id_to_be_acknowledged = \
                    self.acknowledgment_queue.get_nowait()
                #self.config.logger.debug(
                    #'RabbitMQCrashStorage set to acknowledge %s',
                    #crash_id_to_be_acknowledged
                #)
                try:
                    acknowledgement_token = \
                        self.acknowledgement_token_cache[
                            crash_id_to_be_acknowledged
                        ]
                    self.transaction(
                        self._transaction_ack_crash,
                        acknowledgement_token
                    )
                    del self.acknowledgement_token_cache[
                        crash_id_to_be_acknowledged
                    ]
                except KeyError, x:
                    self.config.logger.error(x, exc_info=True)
                    self.config.logger.error(
                        'RabbitMQCrashStorage tried to acknowledge crash %s'
                        ', which was not in the cache',
                        crash_id_to_be_acknowledged
                    )
        except Empty:
            pass  # nothing to do with an empty queue

    #--------------------------------------------------------------------------
    def _transaction_ack_crash(self, connection, acknowledgement_token):
        self.config.logger.debug(
            'RabbitMQCrashStorage acking with delivery_tag %s',
            acknowledgement_token.delivery_tag
        )
        connection.channel.basic_ack(
            delivery_tag=acknowledgement_token.delivery_tag
        )

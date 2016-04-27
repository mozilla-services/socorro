# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pika
from random import randint

from Queue import (
    Queue,
    Empty
)

from configman import (
    Namespace,
    class_converter
)
from configman.dotdict import DotDict
from socorrolib.lib.converters import change_default
from socorro.external.rabbitmq.connection_context import (
    ConnectionContext,
    ConnectionContextPooled,
)
from socorro.external.crashstorage_base import CrashStorageBase


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
        doc='the class responsible for connecting to RabbitMQ',
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        'routing_key',
        default='socorro.normal',
        doc='the name of the queue to recieve crashes',
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        'filter_on_legacy_processing',
        default=True,
        doc='toggle for using or ignoring the throttling flag',
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        'throttle',
        default=100,
        doc='percentage of the time that rabbit will try to queue',
        reference_value_from='resource.rabbitmq',
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(RabbitMQCrashStorage, self).__init__(
            config,
            quit_check_callback=quit_check_callback
        )

        self.config = config

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
            delivery_mode=2,  # make message persistent
        )

        if config.throttle == 100:
            self.dont_queue_this_crash = lambda: False
        else:
            self.dont_queue_this_crash = lambda: randint(1, 100) > config.throttle

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        if  self.dont_queue_this_crash():
            self.config.logger.info(
                'Crash %s filtered out of RabbitMQ queue %s',
                crash_id,
                self.config.routing_key
            )
            return
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
            self.config.logger.debug(
                'RabbitMQCrashStorage saving crash %s', crash_id
            )
            self.transaction(self._save_raw_crash_transaction, crash_id)
            return True
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
    def _basic_get_transaction(self, conn, queue):
        """reorganize the the call to rabbitmq basic_get so that it can be
        used by the transaction retry wrapper."""
        things = conn.channel.basic_get(queue=queue)
        return things

    #--------------------------------------------------------------------------
    def new_crashes(self):
        """This generator fetches crash_ids from RabbitMQ."""

        # We've set up RabbitMQ to require acknowledgement of processing of a
        # crash_id from this generator.  It is the responsibility of the
        # consumer of the crash_id to tell this instance of the class when has
        # completed its work on the crash_id.  That is done with the call to
        # 'ack_crash' below.  Because RabbitMQ connections are not thread safe,
        # only the thread that read the crash may acknowledge it.  'ack_crash'
        # queues the crash_id. The '_consume_acknowledgement_queue' function
        # is run to send acknowledgments back to RabbitMQ
        self._consume_acknowledgement_queue()
        conn = self.rabbitmq.connection()
        queues = [
            self.rabbitmq.config.priority_queue_name,
            self.rabbitmq.config.standard_queue_name,
            self.rabbitmq.config.reprocessing_queue_name,
            self.rabbitmq.config.priority_queue_name,
        ]
        while True:
            for queue in queues:
                method_frame, header_frame, body = self.transaction(
                    self._basic_get_transaction,
                    queue=queue
                )
                if method_frame and self._suppress_duplicate_jobs(
                    body,
                    method_frame
                ):
                    continue
                if method_frame:
                    break
            # must consume ack queue before testing for end of iterator
            # or the last job won't get ack'd
            self._consume_acknowledgement_queue()
            if not method_frame:
                # there was nothing in the queue - leave the iterator
                return
            self.acknowledgement_token_cache[body] = method_frame
            yield body
            queues.reverse()

    #--------------------------------------------------------------------------
    def ack_crash(self, crash_id):
        self.acknowledgment_queue.put(crash_id)

    #--------------------------------------------------------------------------
    def _suppress_duplicate_jobs(self, crash_id, acknowledgement_token):
        """if this crash is in the cache, then it is already in progress
        and this is a duplicate.  Acknowledge it, then return to True
        to let the caller know to skip on to the next crash."""
        if crash_id in self.acknowledgement_token_cache:
            # reject this crash - it's already being processsed
            self.config.logger.info(
                'duplicate job: %s is already in progress',
                crash_id
            )
            # ack this
            self.transaction(
                self._transaction_ack_crash,
                crash_id,
                acknowledgement_token
            )
            return True
        return False

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
                # self.config.logger.debug(
                #     'RabbitMQCrashStorage set to acknowledge %s',
                #     crash_id_to_be_acknowledged
                # )
                try:
                    acknowledgement_token = \
                        self.acknowledgement_token_cache[
                            crash_id_to_be_acknowledged
                        ]
                    self.transaction(
                        self._transaction_ack_crash,
                        crash_id_to_be_acknowledged,
                        acknowledgement_token
                    )
                    del self.acknowledgement_token_cache[
                        crash_id_to_be_acknowledged
                    ]
                except KeyError:
                    self.config.logger.warning(
                        'RabbitMQCrashStorage tried to acknowledge crash %s'
                        ', which was not in the cache',
                        crash_id_to_be_acknowledged,
                        exc_info=True
                    )
                except Exception:
                    self.config.logger.error(
                        'RabbitMQCrashStorage unexpected failure on %s',
                        crash_id_to_be_acknowledged,
                        exc_info=True
                    )

        except Empty:
            pass  # nothing to do with an empty queue

    #--------------------------------------------------------------------------
    def _transaction_ack_crash(
        self,
        connection,
        crash_id,
        acknowledgement_token
    ):
        connection.channel.basic_ack(
            delivery_tag=acknowledgement_token.delivery_tag
        )
        self.config.logger.debug(
            'RabbitMQCrashStorage acking %s with delivery_tag %s',
            crash_id,
            acknowledgement_token.delivery_tag
        )


#==============================================================================
class ReprocessingRabbitMQCrashStore(RabbitMQCrashStorage):
    required_config = Namespace()
    required_config.routing_key = change_default(
        RabbitMQCrashStorage,
        'routing_key',
        'socorro.reprocessing'
    )
    required_config.filter_on_legacy_processing = change_default(
        RabbitMQCrashStorage,
        'filter_on_legacy_processing',
        False
    )


#==============================================================================
class ReprocessingOneRabbitMQCrashStore(ReprocessingRabbitMQCrashStore):
    required_config = Namespace()
    required_config.rabbitmq_class = change_default(
        RabbitMQCrashStorage,
        'rabbitmq_class',
        ConnectionContext,
    )
    required_config.routing_key = change_default(
        RabbitMQCrashStorage,
        'routing_key',
        'socorro.reprocessing'
    )

    def reprocess(self, crash_id):
        return self.save_raw_crash(
            DotDict({'legacy_processing': 0}),
            [],
            crash_id
        )

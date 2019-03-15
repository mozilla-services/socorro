# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from functools import partial
from queue import Queue, Empty
import logging

from configman import Namespace, RequiredConfig
from configman.converters import class_converter
import pika

from socorro.lib.transaction import retry


class RabbitMQCrashQueue(RequiredConfig):
    """Crash queue that uses RabbitMQ."""

    required_config = Namespace()
    required_config.add_option(
        'rabbitmq_class',
        default='socorro.external.rabbitmq.connection_context.ConnectionContextPooled',
        doc='the class responsible for connecting to RabbitMQ',
        from_string_converter=class_converter,
        reference_value_from='resource.rabbitmq',
    )

    def __init__(self, config, namespace=None, quit_check_callback=None):
        self.config = config
        self.namespace = namespace
        self.quit_check_callback = quit_check_callback

        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

        # Note: this may continue to grow if we aren't acking certain UUIDs.
        # We should find a way to time out UUIDs after a certain time.
        self.acknowledgement_token_cache = {}
        self.acknowledgment_queue = Queue()

        self.rabbitmq = config.rabbitmq_class(config)
        self._basic_properties = pika.BasicProperties(
            # Make message persistent
            delivery_mode=2,
        )

    def close(self):
        pass

    def _basic_get(self, conn, queue):
        return conn.channel.basic_get(queue=queue)

    def __iter__(self):
        """Return an iterator over crashes from RabbitMQ.

        Each crash is a tuple of the ``(args, kwargs)`` variety. The lone arg
        is a crash ID, and the kwargs contain only a callback function which
        the FTS app will call to send an ack to Rabbit after processing is
        complete.

        """
        self._consume_acknowledgement_queue()

        queues = [
            self.rabbitmq.config.priority_queue_name,
            self.rabbitmq.config.standard_queue_name,
            self.rabbitmq.config.reprocessing_queue_name,
            self.rabbitmq.config.priority_queue_name,
        ]
        while True:
            for queue in queues:
                method_frame, header_frame, body = retry(
                    connection_context=self.rabbitmq,
                    quit_check=self.quit_check_callback,
                    fun=self._basic_get,
                    queue=queue
                )
                # The body is always a string, so convert it to a string
                if body:
                    body = body.decode('utf-8')

                if method_frame and self._suppress_duplicate_jobs(body, method_frame):
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
            yield (
                (body,),
                {'finished_func': partial(self.ack_crash, body)}
            )
            queues.reverse()

    def ack_crash(self, crash_id):
        self.acknowledgment_queue.put(crash_id)

    def _suppress_duplicate_jobs(self, crash_id, acknowledgement_token):
        """if this crash is in the cache, then it is already in progress
        and this is a duplicate.  Acknowledge it, then return to True
        to let the caller know to skip on to the next crash."""
        if crash_id in self.acknowledgement_token_cache:
            # reject this crash - it's already being processsed
            self.logger.info('duplicate job: %s is already in progress', crash_id)
            # ack this
            retry(
                connection_context=self.rabbitmq,
                quit_check=self.quit_check_callback,
                fun=self._ack_crash,
                crash_id=crash_id,
                acknowledgement_token=acknowledgement_token
            )
            return True
        return False

    def _consume_acknowledgement_queue(self):
        """The acknowledgement of the processing of each crash_id yielded
        from the 'new_crashes' method must take place on the same connection
        that the crash_id came from.  The crash_ids are queued in the
        'acknowledgment_queue'.  That queue is consumed by the QueuingThread"""
        try:
            while True:
                crash_id_to_be_acknowledged = self.acknowledgment_queue.get_nowait()

                try:
                    acknowledgement_token = self.acknowledgement_token_cache[
                        crash_id_to_be_acknowledged
                    ]
                    retry(
                        connection_context=self.rabbitmq,
                        quit_check=self.quit_check_callback,
                        fun=self._ack_crash,
                        crash_id=crash_id_to_be_acknowledged,
                        acknowledgement_token=acknowledgement_token
                    )
                    del self.acknowledgement_token_cache[crash_id_to_be_acknowledged]
                except KeyError:
                    self.logger.warning(
                        'RabbitMQCrashQueue tried to acknowledge crash %s, which was not in cache',
                        crash_id_to_be_acknowledged,
                        exc_info=True
                    )
                except Exception:
                    self.logger.error(
                        'RabbitMQCrashQueue unexpected failure on %s',
                        crash_id_to_be_acknowledged,
                        exc_info=True
                    )

        except Empty:
            pass  # nothing to do with an empty queue

    def _ack_crash(self, connection, crash_id, acknowledgement_token):
        connection.channel.basic_ack(delivery_tag=acknowledgement_token.delivery_tag)
        self.logger.debug(
            'RabbitMQCrashStorage acking %s with delivery_tag %s',
            crash_id,
            acknowledgement_token.delivery_tag
        )

    def new_crashes(self):
        return self.__iter__()

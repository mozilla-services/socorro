# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from configman import Namespace
from configman.converters import class_converter
from configman.dotdict import DotDict
import pika

from socorro.external.crashstorage_base import CrashStorageBase
from socorro.lib.transaction import retry


class RabbitMQCrashStorage(CrashStorageBase):
    """Save crash ids to the specified routing key."""

    required_config = Namespace()
    required_config.add_option(
        'rabbitmq_class',
        # we choose a pooled connection because we need thread safe connection
        # behaviors
        default='socorro.external.rabbitmq.connection_context.ConnectionContextPooled',
        doc='the class responsible for connecting to RabbitMQ',
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

    def __init__(self, config, namespace='', quit_check_callback=None):
        super().__init__(config, namespace=namespace, quit_check_callback=quit_check_callback)
        self.rabbitmq = config.rabbitmq_class(config)
        self._basic_properties = pika.BasicProperties(
            # Make message persistent
            delivery_mode=2,
        )

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        try:
            this_crash_should_be_queued = (
                not self.config.filter_on_legacy_processing or
                raw_crash.legacy_processing == 0
            )
        except KeyError:
            self.logger.debug(
                'RabbitMQCrashStorage legacy_processing key absent in crash '
                '%s', crash_id
            )
            return

        if this_crash_should_be_queued:
            self.logger.debug('RabbitMQCrashStorage saving crash %s', crash_id)
            retry(
                self.rabbitmq,
                self.quit_check,
                self._save_raw_crash,
                crash_id=crash_id
            )
            return True
        else:
            self.logger.debug(
                'RabbitMQCrashStorage not saving crash %s, legacy processing '
                'flag is %s', crash_id, raw_crash.legacy_processing
            )

    def _save_raw_crash(self, connection, crash_id):
        connection.channel.basic_publish(
            exchange='',
            routing_key=self.config.routing_key,
            body=crash_id,
            properties=self._basic_properties
        )


class ReprocessingRabbitMQCrashStore(RabbitMQCrashStorage):
    required_config = Namespace()
    required_config.add_option(
        'routing_key',
        default='socorro.reprocessing',
        doc='the name of the queue to recieve crashes',
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        'filter_on_legacy_processing',
        default=False,
        doc='toggle for using or ignoring the throttling flag',
        reference_value_from='resource.rabbitmq',
    )


class ReprocessingOneRabbitMQCrashStore(ReprocessingRabbitMQCrashStore):
    required_config = Namespace()
    required_config.add_option(
        'rabbitmq_class',
        default='socorro.external.rabbitmq.connection_context.ConnectionContext',
        doc='the class responsible for connecting to RabbitMQ',
        from_string_converter=class_converter,
        reference_value_from='resource.rabbitmq',
    )

    def reprocess(self, crash_ids):
        if not isinstance(crash_ids, (list, tuple)):
            crash_ids = [crash_ids]
        success = bool(crash_ids)
        for crash_id in crash_ids:
            if not self.save_raw_crash(
                DotDict({'legacy_processing': 0}),
                [],
                crash_id
            ):
                success = False
        return success


class PriorityjobRabbitMQCrashStore(RabbitMQCrashStorage):
    required_config = Namespace()
    required_config.add_option(
        'rabbitmq_class',
        default='socorro.external.rabbitmq.connection_context.ConnectionContext',
        doc='the class responsible for connecting to RabbitMQ',
        from_string_converter=class_converter,
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        'routing_key',
        default='socorro.priority',
        doc='the name of the queue to receive crashes',
    )

    def process(self, crash_ids):
        if not isinstance(crash_ids, (list, tuple)):
            crash_ids = [crash_ids]
        success = bool(crash_ids)
        for crash_id in crash_ids:
            if not self.save_raw_crash(
                DotDict({'legacy_processing': 0}),
                [],
                crash_id
            ):
                success = False
        return success

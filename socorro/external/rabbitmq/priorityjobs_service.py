# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pika
from pika.exceptions import ChannelClosed

from socorro.external import MissingArgumentError
from socorro.lib import external_common
from socorro.webapi.webapiService import MiddlewareWebServiceBase

from configman import Namespace, class_converter

#==============================================================================
class Priorityjobs(MiddlewareWebServiceBase):
    """Implement the /priorityjobs service with RabbitMQ."""

    uri = r'/priorityjobs/(.*)'

    required_config = Namespace()
    required_config.add_option(
        'crashstorage_class',
        default='socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage',
        from_string_converter=class_converter,
        reference_value_from='resource.rabbitmq',
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(Priorityjobs, self).__init__(config)
        self.crash_store = self.config.crashstorage_class(self.config)
        self.connection_source = self.crash_store.rabbitmq
        self.transaction = self.crash_store.transaction

    #--------------------------------------------------------------------------
    def get(self, **kwargs):
        raise NotImplementedError(
            'RabbitMQ does not support queue introspection.'
        )

    #--------------------------------------------------------------------------
    def post(self, **kwargs):
        """Add a new job to the priority queue
        """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        if not params.uuid:
            raise MissingArgumentError('uuid')

        with self.connection_source() as connection:
            try:
                self.config.logger.debug(
                    'Inserting priority job into RabbitMQ %s', params.uuid
                )
                connection.channel.basic_publish(
                    exchange='',
                    routing_key=self.config.priority_queue_name,
                    body=params.uuid,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
            except ChannelClosed:
                self.config.logger.error(
                    "Failed inserting priorityjobs data into RabbitMQ",
                    exc_info=True
                )
                return False

        return True

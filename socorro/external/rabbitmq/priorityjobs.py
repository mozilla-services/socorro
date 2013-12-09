# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from configman.dotdict import DotDictWithAcquisition
import pika
from pika.exceptions import ChannelClosed

from socorro.external import MissingArgumentError
from socorro.external.rabbitmq.connection_context import (Connection,
                                                          ConnectionContext)
from socorro.lib import external_common

class Priorityjobs(object):
    """Implement the /priorityjobs service with RabbitMQ."""

    def __init__(self, config, all_services=None):
        self.all_services = all_services
        self.config = config.rabbitmq
        self.context = self.config.rabbitmq_class(self.config)

    def get(self, **kwargs):
        raise NotImplementedError(
            'RabbitMQ does not support queue introspection.'
        )

    def create(self, **kwargs):
        """Add a new job to the priority queue
        """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingArgumentError('uuid')

        with self.context() as connection:
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


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import sys

import pika
from configman import Namespace

from socorro.app.socorro_app import App


# To run this script in production:
#   export PYTHON=/data/socorro/socorro-virtualenv/bin/python
#   $PYTHON ./script/reprocess_crashlist.py \
#       --admin.conf=/etc/socorro/reprocess_crashlist.ini
#
class ReprocessCrashlistApp(App):
    app_name = 'reprocess_crashlist'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()
    required_config.namespace('reprocesscrashlist')
    required_config.reprocesscrashlist.add_option(
        'host',
        doc='host to connect to for RabbitMQ',
        default='localhost',
        reference_value_from='resource.rabbitmq',
    )
    required_config.reprocesscrashlist.add_option(
        'port',
        doc='port to connect to for RabbitMQ',
        default=5672,
        reference_value_from='resource.rabbitmq',
    )
    required_config.reprocesscrashlist.add_option(
        'rabbitmq_user',
        doc='user to connect to for RabbitMQ',
        default='guest',
        reference_value_from='secrets.rabbitmq',
    )
    required_config.reprocesscrashlist.add_option(
        'rabbitmq_password',
        doc="the user's RabbitMQ password",
        default='guest',
        reference_value_from='secrets.rabbitmq',
        secret=True,
    )
    required_config.reprocesscrashlist.add_option(
        name='virtual_host',
        doc='the name of the RabbitMQ virtual host',
        default='/',
        reference_value_from='resource.rabbitmq',
    )
    required_config.reprocesscrashlist.add_option(
        'crashes',
        doc='File containing crash UUIDs, one per line',
        default='crashlist.txt'
    )

    def connect(self):
        logging.debug("connecting to rabbit")
        config = self.config.reprocesscrashlist
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=config.host,
                port=config.port,
                virtual_host=config.virtual_host,
                credentials=pika.credentials.PlainCredentials(
                    config.rabbitmq_user,
                    config.rabbitmq_password))
            )
        except Exception:
            logging.error("Failed to connect")
            raise
        self.connection = connection

    def main(self):
        self.connect()
        channel = self.connection.channel()

        channel.queue_declare(queue='socorro.reprocessing', durable=True)

        with open(self.config.reprocesscrashlist.crashes, 'r') as file:
            for uuid in file.read().splitlines():
                channel.basic_publish(
                    exchange='',
                    routing_key="socorro.reprocessing",
                    body=uuid,
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                logging.debug('submitted %s' % uuid)

        self.connection.close()


if __name__ == '__main__':
    sys.exit(ReprocessCrashlistApp.run())

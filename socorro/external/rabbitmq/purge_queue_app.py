# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace, class_converter
from socorrolib.app.socorro_app import App
FAIL = 1
SUCCESS = 0


#==============================================================================
class PurgeRabbitMQQueueApp(App):
    app_name = 'test_rabbitmq'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()
    required_config.add_option(
        'rabbitmq_class',
        default=
            'socorro.external.rabbitmq.connection_context.ConnectionContext',
        doc='the class responsible for connecting to RabbitMQ',
        from_string_converter=class_converter,
        reference_value_from='resource.rabbitmq',
    )
    required_config.add_option(
        'queue_name',
        doc='purge the named queue of all entries',
        is_argument=True,
        default=''
    )

    #--------------------------------------------------------------------------
    def main(self):
        if not self.config.queue_name:
            self.config.logger.critical('a queue name is required')
            return FAIL
        rabbitmq = self.config.rabbitmq_class(self.config)
        with rabbitmq() as rmq_connection:
            rmq_channel = rmq_connection.channel
            try:
                rmq_channel.queue_delete(queue=self.config.queue_name)
            except Exception:
                self.config.logger.debug(
                    "Could delete queue %s",
                    self.config.queue_name
                )
                raise

        self.config.logger.debug("Deleted queue %s", self.config.queue_name)
        return SUCCESS

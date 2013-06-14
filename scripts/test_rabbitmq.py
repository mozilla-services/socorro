import pika
import logging
logging.basicConfig()

from configman import ConfigurationManager, Namespace, RequiredConfig
from configman.converters import class_converter
from socorro.app.generic_app import App, main  # main not used here, but

class TestRabbitMQApp(App):
    app_name = 'test_rabbitmq'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()
    required_config.namespace('test_rabbitmq')
    required_config.test_rabbitmq.add_option(
      'rabbitmq_host',
      doc='host to connect to for RabbitMQ',
      default='localhost'
    )
    required_config.test_rabbitmq.add_option(
      'rabbitmq_port',
      doc='port to connect to for RabbitMQ',
      default=5672
    )
    required_config.test_rabbitmq.add_option(
      'rabbitmq_user',
      doc='user to connect to for RabbitMQ',
      default='guest'
    )
    required_config.test_rabbitmq.add_option(
      'rabbitmq_password',
      doc='password to connect to for RabbitMQ',
      default='guest'
    )
    required_config.test_rabbitmq.add_option(
      'rabbitmq_vhost',
      doc='virtual host to connect to for RabbitMQ',
      default='/'
    )

    def main(self):
        crash_id = 'blahblahblah'

        print "connecting"
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                            host=self.config.test_rabbitmq.rabbitmq_host,
                            port=self.config.test_rabbitmq.rabbitmq_port,
                            virtual_host=self.config.test_rabbitmq.rabbitmq_vhost,
                            credentials=pika.credentials.PlainCredentials(
                                self.config.test_rabbitmq.rabbitmq_user,
                                self.config.test_rabbitmq.rabbitmq_password)))
        except:
            print "Failed to connect"
            raise

        channel = connection.channel()

        print "declare channel"
        try:
            channel.queue_declare(queue='socorro.normal', durable=True)
        except:
            print "Couldn't declare channel"
            raise

        print "publish crash_id"
        channel.basic_publish(
            exchange='',
            routing_key='socorro.normal',
            body=crash_id,
            properties=pika.BasicProperties(
                delivery_mode = 2, # make message persistent
            )
        )

        print "basic get crash_id"
        data = channel.basic_get(queue="socorro.normal")

        print "ack crash_id"
        channel.basic_ack(
            delivery_tag=data[0].delivery_tag
        )

        print "close connection"
        channel.close()

if __name__ == '__main__':
    main(TestRabbitMQApp)

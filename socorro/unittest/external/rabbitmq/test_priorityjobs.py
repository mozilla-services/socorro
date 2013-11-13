# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from mock import Mock, patch
from nose.plugins.attrib import attr

from socorro.external.rabbitmq import priorityjobs

from configman.dotdict import DotDictWithAcquisition

#==============================================================================
@attr(integration='rabbitmq')  # for nosetests
class IntegrationTestPriorityjobs(unittest.TestCase):
    """Test socorro.external.rabbitmq.priorityjobs.Priorityjobs class."""

    def setUp(self):
        """Create a configuration context."""
        old_config = DotDictWithAcquisition()
        old_config.rabbitMQUsername = 'guest'
        old_config.rabbitMQPassword = 'guest'
        old_config.rabbitMQHost = 'localhost'
        old_config.rabbitMQPort = 5672
        old_config.rabbitMQVirtualhost = '/'
        old_config.rabbitMQStandardQueue = 'socorro.normal'
        old_config.rabbitMQPriorityQueue = 'socorro.priority'
        old_config.logger = Mock()
        self.old_config = old_config

        rabbitmq = DotDictWithAcquisition()
        rabbitmq.host='localhost'
        rabbitmq.port=5672
        rabbitmq.priority_queue_name='socorro.priority'
        rabbitmq.rabbitmq_class=Mock()
        rabbitmq.rabbitmq_password='guest'
        rabbitmq.rabbitmq_user='guest'
        rabbitmq.standard_queue_name='socorro.normal'
        rabbitmq.virtual_host='/'
        self.new_config = DotDictWithAcquisition()
        self.new_config.logger = Mock()
        self.new_config.rabbitmq = rabbitmq

    #--------------------------------------------------------------------------
    def test_get(self):
        """Test the get method raises an exception, since RabbitMQ doesn't
        implement a way to examine what's in a queue."""

        # test with old style config
        jobs = priorityjobs.Priorityjobs(config=self.old_config)
        self.assertRaises(
            NotImplementedError,
            jobs.get
        )

        # test with new style config
        jobs = priorityjobs.Priorityjobs(config=self.new_config)
        self.assertRaises(
            NotImplementedError,
            jobs.get
        )

    #--------------------------------------------------------------------------
    def test_create(self):
        """Test that the create() method properly creates the job, and errors
        when not given the proper arguments."""

        # with old config
        with patch(
            'socorro.external.rabbitmq.priorityjobs.ConnectionContext'
        ) as mocked_connection:
            jobs = priorityjobs.Priorityjobs(config=self.old_config)
            self.assertEqual(mocked_connection.call_count, 1)
            self.assertEqual(jobs.config.host, 'localhost')
            self.assertEqual(jobs.config.port, 5672)
            self.assertEqual(jobs.config.virtual_host, '/')
            self.assertEqual(jobs.config.rabbitmq_user, 'guest')
            self.assertEqual(jobs.config.rabbitmq_password, 'guest')
            self.assertEqual(jobs.config.standard_queue_name, 'socorro.normal')
            self.assertEqual(
                jobs.config.priority_queue_name,
                'socorro.priority'
            )
            self.assertEqual(jobs.create(uuid='b1'), True)

        # with new config
        with patch(
            'socorro.external.rabbitmq.priorityjobs.pika') as mocked_pika:
            jobs = priorityjobs.Priorityjobs(config=self.new_config)
            mocked_connection =  self.new_config.rabbitmq.rabbitmq_class
            self.assertEqual(mocked_connection.call_count, 1)
            self.assertEqual(jobs.config.host, 'localhost')
            self.assertEqual(jobs.config.port, 5672)
            self.assertEqual(jobs.config.virtual_host, '/')
            self.assertEqual(jobs.config.rabbitmq_user, 'guest')
            self.assertEqual(jobs.config.rabbitmq_password, 'guest')
            self.assertEqual(jobs.config.standard_queue_name, 'socorro.normal')
            self.assertEqual(
                jobs.config.priority_queue_name,
                'socorro.priority'
            )
            self.assertEqual(jobs.create(uuid='b1'), True)

            #..................................................................
            self.assertRaises(priorityjobs.MissingArgumentError,
                              jobs.create)
            self.assertTrue(
                mocked_connection.return_value.channel. \
                    basic_publish.called_once_with(
                        '',
                        'socorro.priority',
                        'b1',
                        mocked_pika.BasicProperties.return_value
                    )
            )

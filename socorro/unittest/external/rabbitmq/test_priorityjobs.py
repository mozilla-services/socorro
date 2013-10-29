# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from mock import Mock
from nose.plugins.attrib import attr

from socorro.external.rabbitmq import priorityjobs
from socorro.lib import ConfigurationManager
from socorro.unittest.config import commonconfig

from configman.dotdict import DotDict


#==============================================================================
@attr(integration='rabbitmq')  # for nosetests
class IntegrationTestPriorityjobs(unittest.TestCase):
    """Test socorro.external.rabbitmq.priorityjobs.Priorityjobs class."""

    def setUp(self):
        """Create a configuration context."""
        old_style_config = ConfigurationManager.newConfiguration(
            configurationModule=commonconfig,
            applicationName="RabbitMQ Tests"
        )
        self.config = DotDict({
            'rabbitmq': {
                'host': old_style_config.rabbitMQHost,
                'virtual_host': old_style_config.rabbitMQVirtualhost,
                'port': old_style_config.rabbitMQPort,
                'rabbitmq_user': old_style_config.rabbitMQUsername,
                'rabbitmq_password': old_style_config.rabbitMQPassword,
                'standard_queue_name': old_style_config.rabbitMQStandardQueue,
                'priority_queue_name': old_style_config.rabbitMQPriorityQueue,
                'rabbitmq_connection_wrapper_class':
                    'socorro.external.rabbitmq.connection_context'
                    '.Connction',
            },
        })


    #--------------------------------------------------------------------------
    def test_get(self):
        """Test the get method raises an exception, since RabbitMQ doesn't
        implement a way to examine what's in a queue."""

        jobs = priorityjobs.Priorityjobs(config=self.config)
        self.assertRaises(
            NotImplementedError,
            jobs.get
        )

    #--------------------------------------------------------------------------
    def test_create(self):
        """Test that the create() method properly creates the job, and errors
        when not given the proper arguments."""

        jobs = priorityjobs.Priorityjobs(config=self.config)
        jobs.context = Mock()

        self.assertEqual(jobs.create(uuid='b1'), True)

        #......................................................................
        self.assertRaises(priorityjobs.MissingArgumentError,
                          jobs.create)

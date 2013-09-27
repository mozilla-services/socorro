# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from mock import Mock
from nose.plugins.attrib import attr

from socorro.external.rabbitmq import priorityjobs
from socorro.lib import ConfigurationManager
from socorro.unittest.config import commonconfig


#==============================================================================
@attr(integration='rabbitmq')  # for nosetests
class IntegrationTestPriorityjobs(unittest.TestCase):
    """Test socorro.external.rabbitmq.priorityjobs.Priorityjobs class."""

    def setUp(self):
        """Create a configuration context."""
        self.config = ConfigurationManager.newConfiguration(
            configurationModule=commonconfig,
            applicationName="RabbitMQ Tests"
        )

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

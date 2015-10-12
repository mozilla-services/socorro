# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock, MagicMock, patch
from nose.tools import eq_, ok_, assert_raises

from socorro.external.rabbitmq import priorityjobs
from socorro.unittest.testbase import TestCase

from configman.dotdict import DotDictWithAcquisition

#==============================================================================
class IntegrationTestPriorityjobs(TestCase):
    """Test socorro.external.rabbitmq.priorityjobs.Priorityjobs class."""

    def setUp(self):
        """Create a configuration context."""
        super(IntegrationTestPriorityjobs, self).setUp()
        rabbitmq = DotDictWithAcquisition()
        rabbitmq.host='localhost'
        rabbitmq.port=5672
        rabbitmq.priority_queue_name='socorro.priority'
        rabbitmq.rabbitmq_class=Mock()
        rabbitmq.rabbitmq_password='guest'
        rabbitmq.rabbitmq_user='guest'
        rabbitmq.standard_queue_name='socorro.normal'
        rabbitmq.virtual_host='/'
        self.config = DotDictWithAcquisition()
        self.config.logger = Mock()
        self.config.rabbitmq = rabbitmq

    #--------------------------------------------------------------------------
    def test_get(self):
        """Test the get method raises an exception, since RabbitMQ doesn't
        implement a way to examine what's in a queue."""

        # test with new style config
        jobs = priorityjobs.Priorityjobs(config=self.config)
        assert_raises(
            NotImplementedError,
            jobs.get
        )

    #--------------------------------------------------------------------------
    def test_create(self):
        """Test that the create() method properly creates the job, and errors
        when not given the proper arguments."""

        # with new config
        with patch(
            'socorro.external.rabbitmq.priorityjobs.pika') as mocked_pika:
            jobs = priorityjobs.Priorityjobs(config=self.config)
            mocked_connection =  self.config.rabbitmq.rabbitmq_class
            mocked_connection.return_value.return_value = MagicMock()
            eq_(mocked_connection.call_count, 1)
            eq_(jobs.config.host, 'localhost')
            eq_(jobs.config.port, 5672)
            eq_(jobs.config.virtual_host, '/')
            eq_(jobs.config.rabbitmq_user, 'guest')
            eq_(jobs.config.rabbitmq_password, 'guest')
            eq_(jobs.config.standard_queue_name, 'socorro.normal')
            eq_(
                jobs.config.priority_queue_name,
                'socorro.priority'
            )
            eq_(jobs.create(uuid='b1'), True)

            #..................................................................
            assert_raises(priorityjobs.MissingArgumentError,
                              jobs.create)
            ok_(
                mocked_connection.return_value.channel. \
                    basic_publish.called_once_with(
                        '',
                        'socorro.priority',
                        'b1',
                        mocked_pika.BasicProperties.return_value
                    )
            )

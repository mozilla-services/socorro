# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock, MagicMock, patch
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from collections import Sequence

from socorro.external.rabbitmq.priorityjobs_service import (
    Priorityjobs,
    MissingArgumentError,
)
from socorro.external.rabbitmq.crashstorage import RabbitMQCrashStorage
from socorro.external.rabbitmq.connection_context import ConnectionContext
from socorro.database.transaction_executor import TransactionExecutor
from socorro.unittest.testbase import TestCase
from socorro.unittest.middleware.setup_configman import (
    get_standard_config_manager
)
from socorro.lib.util import SilentFakeLogger

from configman import ConfigurationManager, Namespace, environment
from configman.dotdict import DotDictWithAcquisition


#==============================================================================
@attr(integration='rabbitmq')  # for nosetests
class IntegrationTestPriorityjobs(TestCase):
    """Test socorro.external.rabbitmq.Priorityjobs class."""

    #--------------------------------------------------------------------------
    def setUp(self):
        """Create a configuration context."""
        super(IntegrationTestPriorityjobs, self).setUp()

        overrides = {
            'services.Priorityjobs.redactor_class': Mock(),
        }
        self.config_manager = get_standard_config_manager(
            service_classes=Priorityjobs,
            overrides=overrides,
        )
        self.config = self.config_manager.get_config()

    #--------------------------------------------------------------------------
    def test_get(self):
        """Test the get method raises an exception, since RabbitMQ doesn't
        implement a way to examine what's in a queue."""

        jobs = Priorityjobs(config=self.config.services.Priorityjobs)
        assert_raises(
            NotImplementedError,
            jobs.get
        )

    #--------------------------------------------------------------------------
    def test_post(self):
        """Test that the post() method properly creates the job, and errors
        when not given the proper arguments."""

        # with new config
        with patch(
            'socorro.external.rabbitmq.priorityjobs_service.pika'
        ) as mocked_pika:
            self.config.services.Priorityjobs.rabbitmq_class = Mock()
            mocked_connection = \
                self.config.services.Priorityjobs.rabbitmq_class
            mocked_connection.return_value.return_value = MagicMock()

            jobs = Priorityjobs(config=self.config)

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
            eq_(jobs.post(uuid='b1'), True)

            #..................................................................
            assert_raises(
                MissingArgumentError,
                jobs.post
            )
            ok_(
                mocked_connection.return_value.channel.
                    basic_publish.called_once_with(
                        '',
                        'socorro.priority',
                        'b1',
                        mocked_pika.BasicProperties.return_value
                    )
            )

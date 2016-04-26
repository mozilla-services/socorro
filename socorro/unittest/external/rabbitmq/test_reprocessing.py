# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock, MagicMock
from nose.tools import eq_, ok_

from socorro.external.crashstorage_base import (
    Redactor,
)
from socorro.external.rabbitmq.crashstorage import (
    ReprocessingOneRabbitMQCrashStore,
)
from socorro.external.rabbitmq.connection_context import ConnectionContext
from socorro.unittest.testbase import TestCase

from configman.dotdict import DotDict


#==============================================================================
class TestReprocessing(TestCase):

    def setUp(self):
        super(TestReprocessing, self).setUp()

    def _setup_config(self):
        config = DotDict()
        self.transaction_executor = MagicMock()
        config.transaction_executor_class = self.transaction_executor
        config.logger = Mock()
        config.rabbitmq_class = ConnectionContext
        config.routing_key = 'socorro.reprocessing'
        config.filter_on_legacy_processing = True
        config.forbidden_keys = ''
        config.redactor_class = Redactor
        config.throttle = 100
        return config

    def test_post(self):
        config = self._setup_config()
        reprocessing = ReprocessingOneRabbitMQCrashStore(config)

        def mocked_call(exc_func, crash_id):
            eq_(crash_id, 'some-crash-id')
            return True

        self.transaction_executor().side_effect = mocked_call
        ok_(reprocessing.reprocess('some-crash-id'))

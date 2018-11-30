# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
from mock import Mock, MagicMock

from socorro.external.crashstorage_base import Redactor
from socorro.external.rabbitmq.crashstorage import ReprocessingOneRabbitMQCrashStore
from socorro.external.rabbitmq.connection_context import ConnectionContext


class TestReprocessing(object):
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
        return config

    def test_post(self):
        config = self._setup_config()
        reprocessing = ReprocessingOneRabbitMQCrashStore(config)

        def mocked_save_raw_crash(raw_crash, dumps, crash_id):
            assert crash_id == 'some-crash-id'
            return True

        reprocessing.save_raw_crash = mocked_save_raw_crash
        assert reprocessing.reprocess('some-crash-id')

    def test_post_multiple_one_fails(self):
        config = self._setup_config()
        reprocessing = ReprocessingOneRabbitMQCrashStore(config)

        def mocked_save_raw_crash(raw_crash, dumps, crash_id):
            if crash_id == 'crash-id-1':
                return True
            elif crash_id == 'crash-id-2':
                return False
            raise NotImplementedError(crash_id)

        reprocessing.save_raw_crash = mocked_save_raw_crash
        assert not reprocessing.reprocess(['crash-id-1', 'crash-id-2'])

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
from mock import Mock, MagicMock, patch

from socorro.external.rabbitmq.crashstorage import RabbitMQCrashStorage
from socorro.external.crashstorage_base import Redactor


class TestCrashStorage(object):
    def _setup_config(self):
        config = DotDict()
        config.backoff_delays = (0, 0, 0)
        config.rabbitmq_class = MagicMock()
        config.routing_key = 'socorro.normal'
        config.filter_on_legacy_processing = True
        config.redactor_class = Redactor
        config.forbidden_keys = Redactor.required_config.forbidden_keys.default
        return config

    def test_save_raw_crash_normal(self):
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)

        with patch('socorro.external.rabbitmq.crashstorage.retry') as retry_mock:
            # test for "legacy_processing" missing from crash
            crash_store.save_raw_crash(
                raw_crash=DotDict(),
                dumps=DotDict(),
                crash_id='crash_id'
            )
            assert not retry_mock.called

        with patch('socorro.external.rabbitmq.crashstorage.retry') as retry_mock:
            # test for normal save
            raw_crash = DotDict()
            raw_crash.legacy_processing = 0
            crash_store.save_raw_crash(
                raw_crash=raw_crash,
                dumps=DotDict,
                crash_id='crash_id'
            )
            retry_mock.assert_called_with(
                crash_store.rabbitmq,
                crash_store.quit_check,
                crash_store._save_raw_crash,
                crash_id='crash_id'
            )

        with patch('socorro.external.rabbitmq.crashstorage.retry') as retry_mock:
            # test for save rejection because of "legacy_processing"
            raw_crash = DotDict()
            raw_crash.legacy_processing = 5
            crash_store.save_raw_crash(
                raw_crash=raw_crash,
                dumps=DotDict,
                crash_id='crash_id'
            )
            assert not retry_mock.called

    def test_save_raw_crash_no_legacy(self):
        config = self._setup_config()
        config.filter_on_legacy_processing = False
        crash_store = RabbitMQCrashStorage(config)

        with patch('socorro.external.rabbitmq.crashstorage.retry') as retry_mock:
            # test for "legacy_processing" missing from crash
            crash_store.save_raw_crash(
                raw_crash=DotDict(),
                dumps=DotDict(),
                crash_id='crash_id'
            )
            retry_mock.assert_called_with(
                crash_store.rabbitmq,
                crash_store.quit_check,
                crash_store._save_raw_crash,
                crash_id='crash_id'
            )

        with patch('socorro.external.rabbitmq.crashstorage.retry') as retry_mock:
            # test for normal save
            raw_crash = DotDict()
            raw_crash.legacy_processing = 0
            crash_store.save_raw_crash(
                raw_crash=raw_crash,
                dumps=DotDict,
                crash_id='crash_id'
            )
            retry_mock.assert_called_with(
                crash_store.rabbitmq,
                crash_store.quit_check,
                crash_store._save_raw_crash,
                crash_id='crash_id'
            )

        with patch('socorro.external.rabbitmq.crashstorage.retry') as retry_mock:
            # test for save without regard to "legacy_processing" value
            raw_crash = DotDict()
            raw_crash.legacy_processing = 5
            crash_store.save_raw_crash(
                raw_crash=raw_crash,
                dumps=DotDict,
                crash_id='crash_id'
            )
            retry_mock.assert_called_with(
                crash_store.rabbitmq,
                crash_store.quit_check,
                crash_store._save_raw_crash,
                crash_id='crash_id'
            )

    def test_save_raw_crash_priority(self):
        connection = Mock()
        config = self._setup_config()
        config.routing_key = 'socorro.priority'
        crash_store = RabbitMQCrashStorage(config)
        crash_store._save_raw_crash(connection, 'some_crash_id')
        connection.channel.basic_publish.assert_called_once_with(
            exchange='',
            routing_key='socorro.priority',
            body='some_crash_id',
            properties=crash_store._basic_properties
        )

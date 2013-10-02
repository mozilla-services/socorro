import unittest

from mock import Mock

from socorro.external.rabbitmq.crashstorage import (
    RabbitMQCrashStorage,
)
from socorro.lib.util import DotDict


class TestCrashStorage(unittest.TestCase):

    def _setup_config(self):
        config = DotDict();
        config.rabbitmq_class = Mock()
        config.transaction_executor_class = Mock()
        config.logger = Mock()
        config.routing_key = 'socorro.normal'
        config.filter_on_legacy_processing = True
        return config

    def test_constructor(self):
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)
        self.assertEqual(len(crash_store.acknowledgement_token_cache), 0)
        config.rabbitmq_class.assert_called_once_with(config)
        config.transaction_executor_class.assert_called_once_with(
            config,
            crash_store.rabbitmq,
            quit_check_callback=None
        )

    def test_save_raw_crash_normal(self):
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)

        # test for "legacy_processing" missing from crash
        crash_store.save_raw_crash(
            raw_crash=DotDict(),
            dumps=DotDict(),
            crash_id='crash_id'
        )
        self.assertFalse(crash_store.transaction.called)
        config.logger.reset_mock()

        # test for normal save
        raw_crash = DotDict()
        raw_crash.legacy_processing = 0;
        crash_store.save_raw_crash(
            raw_crash=raw_crash,
            dumps=DotDict,
            crash_id='crash_id'
        )
        crash_store.transaction.assert_called_with(
            crash_store._save_raw_crash_transaction,
            'crash_id'
        )
        crash_store.transaction.reset_mock()

        # test for save rejection because of "legacy_processing"
        raw_crash = DotDict()
        raw_crash.legacy_processing = 5;
        crash_store.save_raw_crash(
            raw_crash=raw_crash,
            dumps=DotDict,
            crash_id='crash_id'
        )
        self.assertFalse(crash_store.transaction.called)

    def test_save_raw_crash_no_legacy(self):
        config = self._setup_config()
        config.filter_on_legacy_processing = False
        crash_store = RabbitMQCrashStorage(config)

        # test for "legacy_processing" missing from crash
        crash_store.save_raw_crash(
            raw_crash=DotDict(),
            dumps=DotDict(),
            crash_id='crash_id'
        )
        crash_store.transaction.assert_called_with(
            crash_store._save_raw_crash_transaction,
            'crash_id'
        )
        config.logger.reset_mock()

        # test for normal save
        raw_crash = DotDict()
        raw_crash.legacy_processing = 0;
        crash_store.save_raw_crash(
            raw_crash=raw_crash,
            dumps=DotDict,
            crash_id='crash_id'
        )
        crash_store.transaction.assert_called_with(
            crash_store._save_raw_crash_transaction,
            'crash_id'
        )
        crash_store.transaction.reset_mock()

        # test for save without regard to "legacy_processing" value
        raw_crash = DotDict()
        raw_crash.legacy_processing = 5;
        crash_store.save_raw_crash(
            raw_crash=raw_crash,
            dumps=DotDict,
            crash_id='crash_id'
        )
        crash_store.transaction.assert_called_with(
            crash_store._save_raw_crash_transaction,
            'crash_id'
        )

    def test_save_raw_crash_transaction_normal(self):
        connection = Mock()
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)
        crash_store._save_raw_crash_transaction(connection, 'some_crash_id')
        connection.channel.basic_publish.assert_called_once_with(
            exchange='',
            routing_key='socorro.normal',
            body='some_crash_id',
            properties=crash_store._basic_properties
        )

    def test_save_raw_crash_transaction_priority(self):
        connection = Mock()
        config = self._setup_config()
        config.routing_key = 'socorro.priority'
        crash_store = RabbitMQCrashStorage(config)
        crash_store._save_raw_crash_transaction(connection, 'some_crash_id')
        connection.channel.basic_publish.assert_called_once_with(
            exchange='',
            routing_key='socorro.priority',
            body='some_crash_id',
            properties=crash_store._basic_properties
        )

    def test_transaction_ack_crash(self):
        config = self._setup_config()
        connection = Mock()
        ack_token = DotDict()
        ack_token.delivery_tag = 1;

        crash_store = RabbitMQCrashStorage(config)
        crash_store._transaction_ack_crash(connection, ack_token)

        connection.channel.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_transaction_ack_crash_fails_gracefully(self):
        config = self._setup_config()
        config.logger = Mock()
        crash_store = RabbitMQCrashStorage(config)
        crash_store.acknowledgment_queue.put('b2')
        crash_store._consume_acknowledgement_queue()

        call_count = config.logger.error.call_count
        self.assertEquals(call_count, 2)

    def test_ack_crash(self):
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)
        crash_store.acknowledgment_queue = Mock()

        crash_store.ack_crash('crash_id')

        crash_store.acknowledgment_queue.put.assert_called_once_with(
            'crash_id'
        )
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

    def test_save_raw_crash(self):
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)

        crash_store.save_raw_crash(
            raw_crash=DotDict(),
            dumps=DotDict(),
            crash_id='crash_id'
        )
        config.logger.reset_mock()

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

        raw_crash = DotDict()
        raw_crash.legacy_processing = 5;
        crash_store.save_raw_crash(
            raw_crash=raw_crash,
            dumps=DotDict,
            crash_id='crash_id'
        )


    def test_transaction_ack_crash(self):
        config = self._setup_config()
        connection = Mock()
        ack_token = DotDict()
        ack_token.delivery_tag = 1;

        crash_store = RabbitMQCrashStorage(config)
        crash_store._transaction_ack_crash(connection, ack_token)

        connection.channel.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_ack_crash(self):
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)
        crash_store.acknowledgment_queue = Mock()

        crash_store.ack_crash('crash_id')

        crash_store.acknowledgment_queue.put.assert_called_once_with(
            'crash_id'
        )
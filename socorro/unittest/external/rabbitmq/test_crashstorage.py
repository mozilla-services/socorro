from configman.dotdict import DotDict
from mock import Mock, MagicMock, patch

from socorro.external.rabbitmq.crashstorage import RabbitMQCrashStorage
from socorro.external.crashstorage_base import Redactor


class TestCrashStorage(object):
    def _setup_config(self):
        config = DotDict()
        config.backoff_delays = (0, 0, 0)
        config.logger = Mock()
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

    def test__save_raw_crash_normal(self):
        connection = Mock()
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)
        crash_store._save_raw_crash(connection, 'some_crash_id')
        connection.channel.basic_publish.assert_called_once_with(
            exchange='',
            routing_key='socorro.normal',
            body='some_crash_id',
            properties=crash_store._basic_properties
        )

    def test__save_raw_crash_priority(self):
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

    def test__ack_crash(self):
        config = self._setup_config()
        connection = Mock()
        ack_token = DotDict()
        ack_token.delivery_tag = 1
        crash_id = 'some-crash-id'

        crash_store = RabbitMQCrashStorage(config)
        crash_store._ack_crash(connection, crash_id, ack_token)

        connection.channel.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_ack_crash_fails_gracefully(self):
        config = self._setup_config()
        config.logger = Mock()
        crash_store = RabbitMQCrashStorage(config)
        crash_store.acknowledgment_queue.put('b2')
        crash_store._consume_acknowledgement_queue()

        config.logger.warning.assert_called_once_with(
            'RabbitMQCrashStorage tried to acknowledge crash %s'
            ', which was not in the cache',
            'b2',
            exc_info=True
        )

    def test_ack_crash(self):
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)
        crash_store.acknowledgment_queue = Mock()

        crash_store.ack_crash('crash_id')

        crash_store.acknowledgment_queue.put.assert_called_once_with(
            'crash_id'
        )

    def test_new_crash_standard_queue(self):
        """ Tests queue with standard queue items only
        """
        config = self._setup_config()
        crash_store = RabbitMQCrashStorage(config)
        crash_store.rabbitmq.config.standard_queue_name = 'socorro.normal'
        crash_store.rabbitmq.config.reprocessing_queue_name = 'socorro.reprocessing'
        crash_store.rabbitmq.config.priority_queue_name = 'socorro.priority'

        test_queue = [
            ('1', '1', 'normal_crash_id'),
            (None, None, None),
            (None, None, None),
        ]

        def basic_get(queue):
            if len(test_queue) == 0:
                return
            if queue == 'socorro.priority':
                return (None, None, None)
            elif queue == 'socorro.reprocessing':
                return (None, None, None)
            elif queue == 'socorro.normal':
                return test_queue.pop()

        crash_store.rabbitmq.return_value.__enter__.return_value  \
            .channel.basic_get = MagicMock(side_effect=basic_get)

        expected = ['normal_crash_id']
        for result in crash_store.new_crashes():
            assert expected.pop() == result

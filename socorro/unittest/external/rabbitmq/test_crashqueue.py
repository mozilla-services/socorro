# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest.mock import MagicMock, Mock

from configman.dotdict import DotDict

from socorro.external.rabbitmq.crashqueue import RabbitMQCrashQueue


class TestRabbitMQCrashQueue(object):
    def _setup_config(self):
        config = DotDict()
        config.rabbitmq_class = MagicMock()
        config.priority_queue_name = 'priority'
        config.standard_queue_name = 'standard'
        config.reprocessing_queue_name = 'reprocessing'
        return config

    def test_ack_crash_fails_gracefully(self, caplogpp):
        caplogpp.set_level('WARNING')

        config = self._setup_config()
        crash_queue = RabbitMQCrashQueue(config)
        crash_queue.acknowledgment_queue.put('b2')
        crash_queue._consume_acknowledgement_queue()

        recs = [(rec.message, rec.exc_info) for rec in caplogpp.records]
        assert (
            recs[0][0] == (
                'RabbitMQCrashQueue tried to acknowledge crash b2, which was not in cache'
            )
        )
        assert recs[0][1] is not None

    def test_ack_crash(self):
        config = self._setup_config()
        crash_queue = RabbitMQCrashQueue(config)
        crash_queue.acknowledgment_queue = Mock()

        crash_queue.ack_crash('crash_id')

        crash_queue.acknowledgment_queue.put.assert_called_once_with('crash_id')

    def test__ack_crash(self):
        config = self._setup_config()
        connection = Mock()
        ack_token = DotDict()
        ack_token.delivery_tag = 1
        crash_id = 'some-crash-id'

        crash_queue = RabbitMQCrashQueue(config)
        crash_queue._ack_crash(connection, crash_id, ack_token)

        connection.channel.basic_ack.assert_called_once_with(delivery_tag=1)

    def test_iter(self):
        """Test queue with standard queue items only."""
        config = self._setup_config()
        crash_queue = RabbitMQCrashQueue(config)
        crash_queue.rabbitmq.config.standard_queue_name = 'socorro.normal'
        crash_queue.rabbitmq.config.reprocessing_queue_name = 'socorro.reprocessing'
        crash_queue.rabbitmq.config.priority_queue_name = 'socorro.priority'

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

        crash_queue.rabbitmq.return_value.__enter__.return_value.channel.basic_get = MagicMock(side_effect=basic_get)  # noqa

        expected = ['normal_crash_id']
        for result in iter(crash_queue):
            assert expected.pop() == result

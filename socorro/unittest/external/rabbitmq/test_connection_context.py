# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from threading import currentThread

from mock import Mock, call, patch
import pytest

from socorro.external.rabbitmq.connection_context import (
    Connection,
    ConnectionContext,
    ConnectionContextPooled
)
from socorro.lib.util import DotDict
from socorro.unittest.testbase import TestCase


class TestConnection(TestCase):
    """Test PostgreSQLBase class. """

    def test_constructor(self):
        faked_connection_object = Mock()
        config = DotDict()
        conn = Connection(
            config,
            faked_connection_object
        )
        assert conn.config is config
        assert conn.connection is faked_connection_object
        faked_connection_object.channel.called_once_with()

        assert faked_connection_object.channel.return_value.queue_declare.call_count == 3
        expected = [
            call(queue='socorro.normal', durable=True),
            call(queue='socorro.priority', durable=True),
            call(queue='socorro.reprocessing', durable=True),
        ]
        assert faked_connection_object.channel.return_value.queue_declare.call_args_list == expected

    def test_close(self):
        faked_connection_object = Mock()
        config = DotDict()
        conn = Connection(
            config,
            faked_connection_object
        )
        conn.close()
        faked_connection_object.close.assert_called_once_with()


class TestConnectionContext(TestCase):

    def _setup_config(self):
        config = DotDict()
        config.host = 'localhost'
        config.virtual_host = '/'
        config.port = '5672'
        config.rabbitmq_user = 'guest'
        config.rabbitmq_password = 'guest'
        config.standard_queue_name = 'dwight'
        config.priority_queue_name = 'wilma'
        config.reprocessing_queue_name = 'betty'
        config.rabbitmq_connection_wrapper_class = Connection

        config.executor_identity = lambda: 'MainThread'

        return config

    def test_constructor(self):
        conn_context_functor = ConnectionContext(self._setup_config)
        assert conn_context_functor.config is conn_context_functor.local_config

    def test_connection(self):
        config = self._setup_config()
        pika_string = 'socorro.external.rabbitmq.connection_context.pika'
        with patch(pika_string) as mocked_pika_module:
            conn_context_functor = ConnectionContext(config)
            conn = conn_context_functor.connection()
            mocked_pika_module.credentials.PlainCredentials \
                .assert_called_once_with('guest', 'guest')
            mocked_pika_module.ConnectionParameters.assert_called_once_with(
                host=conn_context_functor.config.host,
                port=conn_context_functor.config.port,
                virtual_host=conn_context_functor.config.virtual_host,
                credentials=mocked_pika_module.credentials. \
                    PlainCredentials.return_value
            )
            mocked_pika_module.BlockingConnection.assert_called_one_with(
                mocked_pika_module.ConnectionParameters.return_value
            )
            assert isinstance(conn, Connection)
            assert conn.config is config
            assert conn.connection is mocked_pika_module.BlockingConnection.return_value
            assert conn.channel is conn.connection.channel.return_value

        expected = [
            call(queue='dwight', durable=True),
            call(queue='wilma', durable=True),
            call(queue='betty', durable=True),
        ]
        assert conn.channel.queue_declare.call_args_list == expected

    def test_call_and_close_connecton(self):
        config = self._setup_config()
        pika_string = 'socorro.external.rabbitmq.connection_context.pika'
        with patch(pika_string):
            conn_context_functor = ConnectionContext(config)
            with conn_context_functor() as conn_context:
                assert isinstance(conn_context, Connection)
            conn_context.connection.close.assert_called_once_with()


class TestConnectionContextPooled(TestCase):

    def _setup_config(self):
        config = DotDict()
        config.host = 'localhost'
        config.virtual_host = '/'
        config.port = '5672'
        config.rabbitmq_user = 'guest'
        config.rabbitmq_password = 'guest'
        config.standard_queue_name = 'dwight'
        config.priority_queue_name = 'wilma'
        config.reprocessing_queue_name = 'betty'
        config.rabbitmq_connection_wrapper_class = Connection
        config.logger = Mock()

        config.executor_identity = lambda: 'MainThread'

        return config

    def test_constructor(self):
        conn_context_functor = ConnectionContextPooled(self._setup_config)
        assert conn_context_functor.config is conn_context_functor.local_config
        assert len(conn_context_functor.pool) == 0

    def test_connection(self):
        config = self._setup_config()
        pika_string = 'socorro.external.rabbitmq.connection_context.pika'
        with patch(pika_string):
            conn_context_functor = ConnectionContextPooled(config)
            conn = conn_context_functor.connection()
            assert conn is conn_context_functor.pool[currentThread().getName()]
            conn = conn_context_functor.connection('dwight')
            assert conn is conn_context_functor.pool['dwight']
            # get the same connection again to make sure it really is the same
            conn = conn_context_functor.connection()
            assert conn is conn_context_functor.pool[currentThread().getName()]

    def test_close_connection(self):
        config = self._setup_config()
        pika_string = 'socorro.external.rabbitmq.connection_context.pika'
        with patch(pika_string):
            conn_context_functor = ConnectionContextPooled(config)
            conn = conn_context_functor.connection('dwight')
            assert conn is conn_context_functor.pool['dwight']
            conn_context_functor.close_connection(conn)
            # should be no change
            assert conn is conn_context_functor.pool['dwight']
            assert len(conn_context_functor.pool) == 1

            conn_context_functor.close_connection(conn, True)
            with pytest.raises(KeyError):
                conn_context_functor.pool['dwight']()
            assert len(conn_context_functor.pool) == 0

    def test_close(self):
        config = self._setup_config()
        pika_string = 'socorro.external.rabbitmq.connection_context.pika'
        with patch(pika_string):
            conn_context_functor = ConnectionContextPooled(config)
            conn_context_functor.connection()
            conn_context_functor.connection('dwight')
            conn_context_functor.connection('wilma')
            conn_context_functor.close()
            assert len(conn_context_functor.pool) == 0

    def test_force_reconnect(self):
        config = self._setup_config()
        pika_string = 'socorro.external.rabbitmq.connection_context.pika'
        with patch(pika_string):
            conn_context_functor = ConnectionContextPooled(config)
            conn = conn_context_functor.connection()
            assert conn is conn_context_functor.pool[currentThread().getName()]
            conn_context_functor.force_reconnect()
            assert len(conn_context_functor.pool) == 0
            conn2 = conn_context_functor.connection()
            assert not conn == conn2

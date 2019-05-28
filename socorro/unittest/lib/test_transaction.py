# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import pytest

from socorro.lib.transaction import (
    retry,
    transaction_context
)


class Test_transaction_context(object):
    def test_commit_called(self):
        connection_context = mock.MagicMock()

        with transaction_context(connection_context):
            pass

        # Assert rollback() gets called because an exception was thrown in the
        # context
        assert connection_context.return_value.__enter__.return_value.commit.called

    def test_rollback_called(self):
        connection_context = mock.MagicMock()

        exc = Exception('omg')

        with pytest.raises(Exception) as exc_info:
            with transaction_context(connection_context):
                raise exc

        # Assert rollback() gets called because an exception was thrown in the
        # context
        assert connection_context.return_value.__enter__.return_value.rollback.called

        # Assert the exception is rethrown
        assert exc_info.value == exc


class Test_retry(object):
    def test_fine(self):
        conn = object()
        connection_context = mock.MagicMock()
        connection_context.return_value.__enter__.return_value = conn
        quit_check = mock.MagicMock()
        fun = mock.MagicMock()

        retry(
            connection_context,
            quit_check,
            fun
        )

        # Assert fun was called with the connection as the first argument
        fun.assert_called_with(conn)

        # Assert quit_check was not called at all
        assert not quit_check.called

    def test_retry_once(self):
        with mock.patch('socorro.lib.transaction.time.sleep') as sleep_mock:
            sleep_mock.return_value = None

            conn = object()
            connection_context = mock.MagicMock()
            connection_context.return_value.__enter__.return_value = conn
            quit_check = mock.MagicMock()

            exc = Exception('omg!')

            def fun(conn, call_count):
                # The first time this is called, raise an exception; use
                # call_count to maintain state between calls
                if len(call_count) == 0:
                    call_count.append(1)
                    raise exc
                call_count.append(1)
                return 1

            call_count = []
            retry(
                connection_context,
                quit_check,
                fun,
                call_count=call_count
            )

            # Assert fun was called twice
            assert len(call_count) == 2

            # Assert quit_check was called once
            assert quit_check.call_count == 1

    def test_retry_and_die(self):
        with mock.patch('socorro.lib.transaction.time.sleep') as sleep_mock:
            sleep_mock.return_value = None

            conn = object()
            connection_context = mock.MagicMock()
            connection_context.return_value.__enter__.return_value = conn
            quit_check = mock.MagicMock()

            exc = Exception('omg!')

            def fun(conn, call_count):
                # Raise exceptions to simulate failing; use call_count to keep
                # track
                call_count.append(1)
                raise exc

            call_count = []
            with pytest.raises(Exception) as exc_info:
                retry(
                    connection_context,
                    quit_check,
                    fun,
                    call_count=call_count
                )

            # Assert retry runs out of backoffs and throws the last error
            assert exc_info.value == exc

            # Assert fun was called six times
            assert len(call_count) == 6

            # quit_check gets called for every backoff but last, so 5 times
            assert quit_check.call_count == 5

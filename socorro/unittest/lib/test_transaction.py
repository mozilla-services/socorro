# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import pytest

from socorro.lib.transaction import transaction_context


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

        exc = Exception("omg")

        with pytest.raises(Exception) as exc_info:
            with transaction_context(connection_context):
                raise exc

        # Assert rollback() gets called because an exception was thrown in the
        # context
        assert connection_context.return_value.__enter__.return_value.rollback.called

        # Assert the exception is rethrown
        assert exc_info.value == exc

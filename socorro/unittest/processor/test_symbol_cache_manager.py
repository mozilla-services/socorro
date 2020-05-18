# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from unittest import mock

import pytest

from socorro.processor.symbol_cache_manager import (
    EventHandler,
    from_string_to_parse_size,
)


@pytest.mark.skipif(os.uname()[0] != "Linux", reason="only run if on Linux")
class TestEventHandler:
    def test_init(self):
        mocked_monitor = mock.Mock()

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)

        assert handler.verbosity == 17
        assert handler.monitor is mocked_monitor

    def test_process_IN_DELETE_1(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = True
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        assert mocked_monitor._remove_cached.call_count == 0

    def test_process_IN_DELETE_2(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = False
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(event.pathname)

    def test_process_IN_CREATE_1(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = True
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        assert mocked_monitor._update_cache.call_count == 0

    def test_process_IN_CREATE_2(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = False
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._update_cache.called_once_with(event.pathname)

    def test_process_IN_MOVED_TO_1(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = True
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        assert mocked_monitor._remove_cached.call_count == 0

    def test_process_IN_MOVED_TO_2(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = False
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(event.pathname)

    def test_process_IN_OPEN_1(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = True
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        assert mocked_monitor._remove_cached.call_count == 0

    def test_process_IN_OPEN_2(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = False
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(event.pathname)

    def test_process_IN_MODIFY_1(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = True
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        assert mocked_monitor._remove_cached.call_count == 0

    def test_process_IN_MODIFY_2(self):
        mocked_monitor = mock.Mock()

        event = mock.Mock()
        event.dir = False
        event.pathname = "hello"

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(event.pathname, True)


class Test_from_string_to_parse_size:
    def test_bad_input(self):
        with pytest.raises(ValueError):
            from_string_to_parse_size(17)

        with pytest.raises(ValueError):
            from_string_to_parse_size(None)

        with pytest.raises(ValueError):
            from_string_to_parse_size("")

        # bad conversion
        with pytest.raises(ValueError):
            from_string_to_parse_size("g1")

        # unknown size suffix
        with pytest.raises(ValueError):
            from_string_to_parse_size("1g")

    def test_ok(self):
        assert from_string_to_parse_size("1") == 1
        # WHY LOWER CASE?
        assert from_string_to_parse_size("1k") == 1024
        assert from_string_to_parse_size("1M") == 1048576
        assert from_string_to_parse_size("1G") == 1073741824

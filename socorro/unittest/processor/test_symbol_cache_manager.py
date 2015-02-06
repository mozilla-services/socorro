# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime, timedelta

from mock import Mock
from nose.tools import eq_, ok_, assert_raises
from socorro.unittest.testbase import TestCase

from configman import ConfigurationManager
from configman.dotdict import DotDict

from socorro.processor.symbol_cache_manager import (
    EventHandler,
    from_string_to_parse_size,
)

#==============================================================================
class TestEventHandler(TestCase):

    #--------------------------------------------------------------------------
    def test_init(self):
        mocked_monitor = Mock()

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)

        eq_(handler.verbosity, 17)
        ok_(handler.monitor is mocked_monitor)

    #--------------------------------------------------------------------------
    def test_process_IN_DELETE_1(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = True
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        eq_(mocked_monitor._remove_cached.call_count, 0)

    #--------------------------------------------------------------------------
    def test_process_IN_DELETE_2(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = False
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(
            event.pathname
        )

    #--------------------------------------------------------------------------
    def test_process_IN_CREATE_1(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = True
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        eq_(mocked_monitor._update_cache.call_count, 0)

    #--------------------------------------------------------------------------
    def test_process_IN_CREATE_2(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = False
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._update_cache.called_once_with(
            event.pathname
        )

    #--------------------------------------------------------------------------
    def test_process_IN_MOVED_TO_1(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = True
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        eq_(mocked_monitor._remove_cached.call_count, 0)

    #--------------------------------------------------------------------------
    def test_process_IN_MOVED_TO_2(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = False
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(
            event.pathname
        )

    #--------------------------------------------------------------------------
    def test_process_IN_OPEN_1(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = True
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        eq_(mocked_monitor._remove_cached.call_count, 0)

    #--------------------------------------------------------------------------
    def test_process_IN_OPEN_2(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = False
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(
            event.pathname
        )

    #--------------------------------------------------------------------------
    def test_process_IN_MODIFY_1(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = True
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        eq_(mocked_monitor._remove_cached.call_count, 0)

    #--------------------------------------------------------------------------
    def test_process_IN_MODIFY_2(self):
        mocked_monitor = Mock()

        event = Mock()
        event.dir = False
        event.pathname = 'hello'

        # the call to be tested
        handler = EventHandler(mocked_monitor, 17)
        handler.process_IN_DELETE(event)

        mocked_monitor._remove_cached.called_once_with(
            event.pathname,
            True
        )


#==============================================================================
class Test_from_string_to_parse_size(TestCase):

    #--------------------------------------------------------------------------
    def test_bad_input(self):
        self.assertRaises(
            ValueError,
            from_string_to_parse_size,
            17
        )
        self.assertRaises(
            ValueError,
            from_string_to_parse_size,
            None
        )
        self.assertRaises(
            ValueError,
            from_string_to_parse_size,
            ""
        )
        # bad conversion
        self.assertRaises(
            ValueError,
            from_string_to_parse_size,
            "g1"
        )
        # unknown size suffix
        self.assertRaises(
            ValueError,
            from_string_to_parse_size,
            "1g"
        )

    #--------------------------------------------------------------------------
    def test_ok(self):
        eq_(from_string_to_parse_size("1"), 1)
        eq_(from_string_to_parse_size("1k"), 1024)  # WHY LOWER CASE?
        eq_(from_string_to_parse_size("1M"), 1048576)
        eq_(from_string_to_parse_size("1G"), 1073741824)


#==============================================================================
class Test_SymbolLRUCacheManager(TestCase):


    #--------------------------------------------------------------------------
    def get_config(self):
        config = DotDict()

        config.symbol_cache_path = '/tmp'
        config.symbol_cache_size = 1024
        config.verbosity = 0


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import patch, call, Mock
from nose.tools import eq_, ok_, assert_raises
from socorro.unittest.testbase import TestCase

from datetime import datetime

from configman.dotdict import DotDict

from socorro.external.statsd.crashstorage import (
    StatsdCrashStorage,
    StatsdBenchmarkingCrashStorage,
)
from socorro.external.statsd.dogstatsd import StatsClient

#==============================================================================
class TestStatsdCrashStorage(TestCase):

    #--------------------------------------------------------------------------
    def setup_config(self, prefix=None):
        config =  DotDict()
        config.statsd_class =  StatsClient
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.statsd_prefix = prefix if prefix else ''
        config.active_list = 'save_processed'

        return config

    #--------------------------------------------------------------------------
    def test_save_processed(self):
        config = self.setup_config()
        number_of_calls =  10

        with patch('socorro.external.statsd.dogstatsd.statsd') as statsd_obj:
            cs =  StatsdCrashStorage(config)
            for x in range(number_of_calls):
                cs.save_processed(x, {})

            statsd_obj.increment.assert_has_calls(
                [call('save_processed') for x in range(number_of_calls)]
            )

    #--------------------------------------------------------------------------
    def test_save_processed_with_prefix(self):
        config = self.setup_config()
        config.statsd_prefix = 'processor'
        number_of_calls =  10

        with patch('socorro.external.statsd.dogstatsd.statsd') as statsd_obj:
            cs =  StatsdCrashStorage(config)
            for x in range(number_of_calls):
                cs.save_processed(x, {})

            statsd_obj.increment.assert_has_calls(
                [call('processor.save_processed') for x in range(number_of_calls)]
            )

    #--------------------------------------------------------------------------
    def test_arbitrary_with_prefix(self):
        config = self.setup_config()
        config.statsd_prefix = 'processor'
        number_of_calls =  10

        with patch('socorro.external.statsd.dogstatsd.statsd') as statsd_obj:
            cs =  StatsdCrashStorage(config)
            for x in range(number_of_calls):
                cs.some_random_method(x, {})

            # the method is not in the active list so should be ignored
            statsd_obj.increment.assert_has_calls([])


#==============================================================================
class TestStatsdBenchmarkingCrashStorage(TestCase):

    #--------------------------------------------------------------------------
    def setup_config(self, prefix=None):
        config =  DotDict()
        config.statsd_class =  StatsClient
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.statsd_prefix = prefix if prefix else ''
        config.active_list = 'save_processed'
        config.wrapped_object_class =  Mock()

        return config

    #--------------------------------------------------------------------------
    @patch('socorro.external.statsd.dogstatsd.statsd')
    def test_save(self, statsd_obj):
        config = self.setup_config('timing')
        cs =  StatsdBenchmarkingCrashStorage(config)
        now_str = 'socorro.external.statsd.statsd_base.datetime'
        with patch(now_str) as now_mock:
            times =  [
                datetime(2015, 5, 4, 15, 10, 3),
                datetime(2015, 5, 4, 15, 10, 2),
                datetime(2015, 5, 4, 15, 10, 1),
                datetime(2015, 5, 4, 15, 10, 0),
            ]
            now_mock.now.side_effect =  lambda: times.pop()
            config.wrapped_object_class.__name__ =  \
                'SomeWrappedCrashStoreClass'

            # the call to be tested
            cs.save_raw_crash({}, [], 'some_id')

            statsd_timing = statsd_obj.timing
            statsd_timing.has_calls(
                [call(
                    'timing.SomeWrappedCrashStoreClass.save_raw_crash',
                    1000
                )]
            )
            config.wrapped_object_class.return_value.save_raw_crash.has_calls(
                [call({}, [], 'some_id')]
            )

    #--------------------------------------------------------------------------
    @patch('socorro.external.statsd.dogstatsd.statsd')
    def test_get(self, statsd_obj):
        config = self.setup_config('timing')
        cs =  StatsdBenchmarkingCrashStorage(config)
        now_str = 'socorro.external.statsd.statsd_base.datetime'
        with patch(now_str) as now_mock:
            times =  [
                datetime(2015, 5, 4, 15, 10, 3),
                datetime(2015, 5, 4, 15, 10, 2),
                datetime(2015, 5, 4, 15, 10, 1),
                datetime(2015, 5, 4, 15, 10, 0),
            ]
            now_mock.now.side_effect =  lambda: times.pop()
            wrapped_crashstore_instance = config.wrapped_object_class.return_value
            config.wrapped_object_class.__name__ =  \
                'SomeWrappedCrashStoreClass'
            raw_crash = {
                'crash_id': 'some_id',
                'data': 'payload',
            }
            wrapped_crashstore_instance.get_raw_crash.return_value = raw_crash

            # the call to be tested
            result =  cs.get_raw_crash('some_id')

            statsd_timing = statsd_obj.timing
            statsd_timing.has_calls(
                [call(
                    'timing.SomeWrappedCrashStoreClass.get_raw_crash',
                    1000
                )]
            )
            config.wrapped_object_class.return_value.save_raw_crash.has_calls(
                [call({}, [], 'some_id')]
            )
            eq_(result, raw_crash)

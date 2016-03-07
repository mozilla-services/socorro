# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import patch, call, Mock
from nose.tools import eq_, ok_, assert_raises
from socorro.unittest.testbase import TestCase

from datetime import datetime

from configman.dotdict import DotDict

from socorro.external.statsd.statsd_rule_benchmark import (
    StatsdRuleBenchmarkWrapper,
    CountAnythingRuleBase,
    CountStackWalkerTimeoutKills,
    CountStackWalkerFailures,
)
from socorro.external.statsd.statsd_base import StatsdCounter
from socorrolib.unittest.lib.test_transform_rules import (
    TestRuleTestLaughable,
    TestRuleTestDangerous
)
from socorrolib.lib import transform_rules
from socorro.external.statsd.dogstatsd import StatsClient

#==============================================================================
class TestStatsdCounterRule(TestCase):

    #--------------------------------------------------------------------------
    def setup_config(self, prefix=None):
        config = DotDict()
        config.chatty_rules = False
        config.chatty = False
        config.tag = 'test.rule'
        config.action = 'apply_all_rules'
        config.rules_list = DotDict()
        config.rules_list.class_list = [
            (
                'TestRuleTestLaughable',
                StatsdRuleBenchmarkWrapper,
                'TestRuleTestLaughable'
            ),
            (
                'TestRuleTestDangerous',
                StatsdRuleBenchmarkWrapper,
                'TestRuleTestDangerous'
            )
        ]
        config.TestRuleTestLaughable = DotDict()
        config.TestRuleTestLaughable.laughable = 'wilma'
        config.TestRuleTestLaughable.statsd_class =  StatsClient
        config.TestRuleTestLaughable.statsd_host = 'some_statsd_host'
        config.TestRuleTestLaughable.statsd_port =  3333
        config.TestRuleTestLaughable.statsd_prefix = prefix if prefix else ''
        config.TestRuleTestLaughable.wrapped_object_class = TestRuleTestLaughable
        config.TestRuleTestLaughable.active_list = 'act'

        config.TestRuleTestDangerous = DotDict()
        config.TestRuleTestDangerous.dangerous = 'dwight'
        config.TestRuleTestDangerous.statsd_class =  StatsClient
        config.TestRuleTestDangerous.statsd_host = 'some_statsd_host'
        config.TestRuleTestDangerous.statsd_port =  3333
        config.TestRuleTestDangerous.statsd_prefix = prefix if prefix else ''
        config.TestRuleTestDangerous.wrapped_object_class = TestRuleTestDangerous
        config.TestRuleTestDangerous.active_list = 'act'

        return config

    #--------------------------------------------------------------------------
    @patch('socorro.external.statsd.dogstatsd.statsd')
    def test_apply_all(self, statsd_obj):
        config = self.setup_config('processor')
        trs = transform_rules.TransformRuleSystem(config)

        ok_(isinstance(trs.rules[0], StatsdRuleBenchmarkWrapper))
        ok_(isinstance(trs.rules[0].wrapped_object, TestRuleTestLaughable))
        ok_(isinstance(trs.rules[1], StatsdRuleBenchmarkWrapper))
        ok_(isinstance(trs.rules[1].wrapped_object, TestRuleTestDangerous))

        now_str = 'socorro.external.statsd.statsd_base.datetime'
        with patch(now_str) as now_mock:
            times =  [
                datetime(2015, 5, 4, 15, 10, 3),
                datetime(2015, 5, 4, 15, 10, 2),
                datetime(2015, 5, 4, 15, 10, 1),
                datetime(2015, 5, 4, 15, 10, 0),
            ]
            ok_(trs.rules[0].predicate(None))
            statsd_obj.timing.has_calls([])
            ok_(trs.rules[1].action(None))
            statsd_obj.timing.has_calls([])

            trs.apply_all_rules()
            statsd_obj.timing.has_calls([
                call(
                    'timing.TestRuleTestLaughable.act',
                    1000  # 1 second
                ),
                call(
                    'timing.TestRuleTestDangerous.act',
                    1000  # 1 second
                ),
            ])

#==============================================================================
class TestStatsdCountAnythingRule(TestStatsdCounterRule):

    @patch('socorro.external.statsd.dogstatsd.statsd')
    def testCountAnythingRuleBase(self, statsd_obj):
        config = DotDict()
        config.counter_class = Mock()
        config.rule_name = 'dwight'
        config.statsd_class =  Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.statsd_prefix = ''
        config.active_list =  ['dwight']
        a_rule = CountAnythingRuleBase(config)

        raw_crash_mock =  Mock()
        raw_dumps_mock =  Mock()
        processed_crash_mock =  Mock()
        proc_meta_mock =  Mock()

        assert_raises(
            NotImplementedError,
            a_rule._predicate,
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta_mock
        )

        a_rule._action(
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta_mock
        )
        a_rule.counter._incr.assert_called_once_with(
            'dwight'
        )

    @patch('socorro.external.statsd.dogstatsd.statsd')
    def testCountStackWalkerTimeoutKills_success(self, statsd_obj):
        config = DotDict()
        config.counter_class = Mock()
        config.rule_name = 'stackwalker_timeout_kills'
        config.statsd_class =  Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.statsd_prefix =  ''
        config.active_list =  ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerTimeoutKills(config)

        raw_crash_mock =  Mock()
        raw_dumps_mock =  Mock()
        processed_crash_mock =  Mock()
        proc_meta =  DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
            'like, maybe, SIGKILL of the stackwalker',
            'or other such things.'
        ]

        ok_(
            a_rule._predicate(
                raw_crash_mock,
                raw_dumps_mock,
                processed_crash_mock,
                proc_meta
            )
        )

        a_rule._action(
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta
        )
        a_rule.counter._incr.assert_called_once_with(
            'stackwalker_timeout_kills'
        )

    @patch('socorro.external.statsd.dogstatsd.statsd')
    def testCountStackWalkerTimeoutKills_fail(self, statsd_obj):
        config = DotDict()
        config.counter_class = Mock()
        config.rule_name = 'stackwalker_timeout_kills'
        config.statsd_class =  Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.statsd_prefix =  ''
        config.active_list =  ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerTimeoutKills(config)

        raw_crash_mock =  Mock()
        raw_dumps_mock =  Mock()
        processed_crash_mock =  Mock()
        proc_meta =  DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
        ]

        ok_(
            not
            a_rule._predicate(
                raw_crash_mock,
                raw_dumps_mock,
                processed_crash_mock,
                proc_meta
            )
        )

    @patch('socorro.external.statsd.dogstatsd.statsd')
    def testCountStackWalkerFailures_success(self, statsd_obj):
        config = DotDict()
        config.counter_class = Mock()
        config.rule_name = 'stackwalker_timeout_kills'
        config.statsd_class =  Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.statsd_prefix =  ''
        config.active_list =  ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerFailures(config)

        raw_crash_mock =  Mock()
        raw_dumps_mock =  Mock()
        processed_crash_mock =  Mock()
        proc_meta =  DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
            'like, maybe when "MDSW failed"',
            'or other such things.'
        ]

        ok_(
            a_rule._predicate(
                raw_crash_mock,
                raw_dumps_mock,
                processed_crash_mock,
                proc_meta
            )
        )

        a_rule._action(
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta
        )
        a_rule.counter._incr.assert_called_once_with(
            'stackwalker_timeout_kills'
        )

    @patch('socorro.external.statsd.dogstatsd.statsd')
    def testCountStackWalkerFailures_fail(self, statsd_obj):
        config = DotDict()
        config.counter_class = Mock()
        config.rule_name = 'stackwalker_timeout_kills'
        config.statsd_class =  Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port =  3333
        config.statsd_prefix =  ''
        config.active_list =  ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerFailures(config)

        raw_crash_mock =  Mock()
        raw_dumps_mock =  Mock()
        processed_crash_mock =  Mock()
        proc_meta =  DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
        ]

        ok_(
            not
            a_rule._predicate(
                raw_crash_mock,
                raw_dumps_mock,
                processed_crash_mock,
                proc_meta
            )
        )

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
from mock import patch, Mock
import pytest

from socorro.external.statsd.dogstatsd import StatsClient
from socorro.external.statsd.statsd_base import StatsdBenchmarkingWrapper
from socorro.external.statsd.statsd_rule_benchmark import (
    CountAnythingRuleBase,
    CountStackWalkerTimeoutKills,
    CountStackWalkerFailures,
)
from socorro.unittest.lib.test_transform_rules import (
    RuleTestLaughable,
    RuleTestDangerous
)
from socorro.unittest.testbase import TestCase


class TestStatsdCountAnythingRule(TestCase):

    def setup_config(self, prefix=None):
        config = DotDict()
        config.tag = 'test.rule'
        config.action = 'apply_all_rules'
        config.rules_list = DotDict()
        config.rules_list.class_list = [
            (
                'RuleTestLaughable',
                StatsdBenchmarkingWrapper,
                'RuleTestLaughable'
            ),
            (
                'RuleTestDangerous',
                StatsdBenchmarkingWrapper,
                'RuleTestDangerous'
            )
        ]
        config.RuleTestLaughable = DotDict()
        config.RuleTestLaughable.laughable = 'wilma'
        config.RuleTestLaughable.statsd_class = StatsClient
        config.RuleTestLaughable.statsd_host = 'some_statsd_host'
        config.RuleTestLaughable.statsd_port = 3333
        config.RuleTestLaughable.statsd_prefix = prefix if prefix else ''
        config.RuleTestLaughable.wrapped_object_class = RuleTestLaughable
        config.RuleTestLaughable.active_list = 'act'

        config.RuleTestDangerous = DotDict()
        config.RuleTestDangerous.dangerous = 'dwight'
        config.RuleTestDangerous.statsd_class = StatsClient
        config.RuleTestDangerous.statsd_host = 'some_statsd_host'
        config.RuleTestDangerous.statsd_port = 3333
        config.RuleTestDangerous.statsd_prefix = prefix if prefix else ''
        config.RuleTestDangerous.wrapped_object_class = RuleTestDangerous
        config.RuleTestDangerous.active_list = 'act'

        return config

    @patch('socorro.external.statsd.dogstatsd.statsd')
    def testCountAnythingRuleBase(self, statsd_obj):
        config = DotDict()
        config.counter_class = Mock()
        config.rule_name = 'dwight'
        config.statsd_class = Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port = 3333
        config.statsd_prefix = ''
        config.active_list = ['dwight']
        a_rule = CountAnythingRuleBase(config)

        raw_crash_mock = Mock()
        raw_dumps_mock = Mock()
        processed_crash_mock = Mock()
        proc_meta_mock = Mock()

        with pytest.raises(NotImplementedError):
            a_rule._predicate(raw_crash_mock, raw_dumps_mock, processed_crash_mock, proc_meta_mock)

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
        config.statsd_class = Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port = 3333
        config.statsd_prefix = ''
        config.active_list = ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerTimeoutKills(config)

        raw_crash_mock = Mock()
        raw_dumps_mock = Mock()
        processed_crash_mock = Mock()
        proc_meta = DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
            'like, maybe, SIGKILL of the stackwalker',
            'or other such things.'
        ]

        assert a_rule._predicate(
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta
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
        config.statsd_class = Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port = 3333
        config.statsd_prefix = ''
        config.active_list = ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerTimeoutKills(config)

        raw_crash_mock = Mock()
        raw_dumps_mock = Mock()
        processed_crash_mock = Mock()
        proc_meta = DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
        ]

        assert not a_rule._predicate(
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta
        )

    @patch('socorro.external.statsd.dogstatsd.statsd')
    def testCountStackWalkerFailures_success(self, statsd_obj):
        config = DotDict()
        config.counter_class = Mock()
        config.rule_name = 'stackwalker_timeout_kills'
        config.statsd_class = Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port = 3333
        config.statsd_prefix = ''
        config.active_list = ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerFailures(config)

        raw_crash_mock = Mock()
        raw_dumps_mock = Mock()
        processed_crash_mock = Mock()
        proc_meta = DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
            'like, maybe when "MDSW failed"',
            'or other such things.'
        ]

        assert a_rule._predicate(
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta
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
        config.statsd_class = Mock()
        config.statsd_host = 'some_statsd_host'
        config.statsd_port = 3333
        config.statsd_prefix = ''
        config.active_list = ['stackwalker_timeout_kills']
        a_rule = CountStackWalkerFailures(config)

        raw_crash_mock = Mock()
        raw_dumps_mock = Mock()
        processed_crash_mock = Mock()
        proc_meta = DotDict()
        proc_meta.processor_notes = [
            'hello',
            'this is a list of notes from the processor',
            'it has information about the what the processor',
            'thought was important',
        ]

        assert not a_rule._predicate(
            raw_crash_mock,
            raw_dumps_mock,
            processed_crash_mock,
            proc_meta
        )

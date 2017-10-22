import ujson

from configman import ConfigurationManager
from configman.dotdict import DotDict
from mock import Mock, patch

from socorro.lib.transform_rules import TransformRuleSystem
from socorro.processor.processor_2015 import (
    Processor2015,
    rule_sets_from_string
)
from socorro.processor.general_transform_rules import (
    CPUInfoRule,
    OSInfoRule
)
from socorro.unittest.testbase import TestCase


rule_set_01 = [
    [
        'ruleset01',
        'socorro.processor.general_transform_rules.CPUInfoRule, '
        'socorro.processor.general_transform_rules.OSInfoRule '
    ]
]
rule_set_01_str = ujson.dumps(rule_set_01)


class TestProcessor2015(TestCase):
    def test_rule_sets_from_string_1(self):
        rule_set_config = rule_sets_from_string(rule_set_01_str)
        rc = rule_set_config.get_required_config()
        assert 'ruleset01' in rc
        expected = (
            'socorro.processor.general_transform_rules.CPUInfoRule, '
            'socorro.processor.general_transform_rules.OSInfoRule '
        )
        assert rc.ruleset01.rules_list.default == expected

    def test_Processor2015_init(self):
        cm = ConfigurationManager(
            definition_source=Processor2015.get_required_config(),
            values_source_list=[{'rule_sets': rule_set_01_str}],
        )
        config = cm.get_config()
        config.logger = Mock()

        p = Processor2015(config)

        assert isinstance(p.rule_system, DotDict)
        assert len(p.rule_system) == 1
        assert 'ruleset01' in p.rule_system
        assert isinstance(p.rule_system.ruleset01, TransformRuleSystem)
        trs = p.rule_system.ruleset01
        assert len(trs.rules) == 2
        assert isinstance(trs.rules[0], CPUInfoRule)
        assert isinstance(trs.rules[1], OSInfoRule)

    def test_process_crash_no_rules(self):
        cm = ConfigurationManager(
            definition_source=Processor2015.get_required_config(),
            values_source_list=[{'rule_sets': '[]'}],
        )
        config = cm.get_config()
        config.logger = Mock()
        config.processor_name = 'dwight'

        p = Processor2015(config)
        raw_crash = DotDict()
        raw_dumps = {}
        with patch('socorro.processor.processor_2015.utc_now') as faked_utcnow:
            faked_utcnow.return_value = '2015-01-01T00:00:00'
            processed_crash = p.process_crash(
                raw_crash,
                raw_dumps,
                DotDict()
            )

        assert processed_crash.success
        assert processed_crash.started_datetime == '2015-01-01T00:00:00'
        assert processed_crash.startedDateTime == '2015-01-01T00:00:00'
        assert processed_crash.completed_datetime == '2015-01-01T00:00:00'
        assert processed_crash.completeddatetime == '2015-01-01T00:00:00'
        assert processed_crash.processor_notes == 'dwight; Processor2015'

    def test_process_crash_existing_processed_crash(self):
        cm = ConfigurationManager(
            definition_source=Processor2015.get_required_config(),
            values_source_list=[{'rule_sets': '[]'}],
        )
        config = cm.get_config()
        config.logger = Mock()
        config.processor_name = 'dwight'

        p = Processor2015(config)
        raw_crash = DotDict()
        raw_dumps = {}
        processed_crash = DotDict()
        processed_crash.processor_notes = "we've been here before; yep"
        processed_crash.started_datetime = '2014-01-01T00:00:00'
        with patch('socorro.processor.processor_2015.utc_now') as faked_utcnow:
            faked_utcnow.return_value = '2015-01-01T00:00:00'
            processed_crash = p.process_crash(
                raw_crash,
                raw_dumps,
                processed_crash
            )

        assert processed_crash.success
        assert processed_crash.started_datetime == '2015-01-01T00:00:00'
        assert processed_crash.startedDateTime == '2015-01-01T00:00:00'
        assert processed_crash.completed_datetime == '2015-01-01T00:00:00'
        assert processed_crash.completeddatetime == '2015-01-01T00:00:00'
        expected = (
            "dwight; Processor2015; earlier processing: 2014-01-01T00:00:00; we've been here "
            "before; yep"
        )
        assert processed_crash.processor_notes == expected

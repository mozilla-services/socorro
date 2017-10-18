import ujson

from configman import ConfigurationManager
from configman.dotdict import DotDict
from mock import Mock, patch

from socorro.lib.transform_rules import TransformRuleSystem
from socorro.processor.processor_2015 import (
    Processor2015,
    rule_sets_from_string
)
from socorro.processor.skunk_classifiers import SetWindowPos
from socorro.processor.support_classifiers import (
    BitguardClassifier,
    OutOfDateClassifier
)
from socorro.unittest.testbase import TestCase


rule_set_01 = [
    [
        'ruleset01',
        'tag0.tag1',
        'socorro.lib.transform_rules.TransformRuleSystem',
        'apply_all_rules',
        'socorro.processor.support_classifiers.BitguardClassifier, '
        'socorro.processor.support_classifiers.OutOfDateClassifier'
    ]
]
rule_set_01_str = ujson.dumps(rule_set_01)

rule_set_02 = [
    [
        'ruleset01',
        'tag0.tag1',
        'socorro.lib.transform_rules.TransformRuleSystem',
        'apply_all_rules',
        'socorro.processor.support_classifiers.BitguardClassifier, '
        'socorro.processor.support_classifiers.OutOfDateClassifier'
    ],
    [
        'ruleset02',
        'tag2.tag3',
        'socorro.lib.transform_rules.TransformRuleSystem',
        'apply_until_action_succeeds',
        'socorro.processor.skunk_classifiers.SetWindowPos'
    ],
]
rule_set_02_str = ujson.dumps(rule_set_02)


class TestProcessor2015(TestCase):
    def test_rule_sets_from_string_1(self):
        rule_set_config = rule_sets_from_string(rule_set_01_str)
        rc = rule_set_config.get_required_config()
        assert 'ruleset01' in rc
        assert 'tag0.tag1' == rc.ruleset01.tag.default
        expected = 'socorro.lib.transform_rules.TransformRuleSystem'
        assert rc.ruleset01.rule_system_class.default == expected
        assert 'apply_all_rules' == rc.ruleset01.action.default
        expected = (
            'socorro.processor.support_classifiers.BitguardClassifier, '
            'socorro.processor.support_classifiers.OutOfDateClassifier'
        )
        assert rc.ruleset01.rules_list.default == expected

    def test_rule_sets_from_string_2(self):
        rule_set_config = rule_sets_from_string(rule_set_02_str)
        rc = rule_set_config.get_required_config()

        assert 'ruleset01' in rc
        assert 'tag0.tag1' == rc.ruleset01.tag.default
        expected = 'socorro.lib.transform_rules.TransformRuleSystem'
        assert rc.ruleset01.rule_system_class.default == expected
        assert 'apply_all_rules' == rc.ruleset01.action.default
        expected = (
            'socorro.processor.support_classifiers.BitguardClassifier, '
            'socorro.processor.support_classifiers.OutOfDateClassifier'
        )
        assert rc.ruleset01.rules_list.default == expected

        assert 'ruleset02' in rc
        assert 'tag2.tag3' == rc.ruleset02.tag.default
        expected = 'socorro.lib.transform_rules.TransformRuleSystem'
        assert rc.ruleset02.rule_system_class.default == expected
        assert 'apply_until_action_succeeds' == rc.ruleset02.action.default
        expected = (
            'socorro.processor.skunk_classifiers.SetWindowPos'
        )
        assert rc.ruleset02.rules_list.default == expected

    def test_Processor2015_init(self):
        cm = ConfigurationManager(
            definition_source=Processor2015.get_required_config(),
            values_source_list=[{'rule_sets': rule_set_02_str}],
        )
        config = cm.get_config()
        config.logger = Mock()

        p = Processor2015(config)

        assert isinstance(p.rule_system, DotDict)
        assert len(p.rule_system) == 2
        assert 'ruleset01' in p.rule_system
        assert isinstance(p.rule_system.ruleset01, TransformRuleSystem)
        trs = p.rule_system.ruleset01
        assert trs.act == trs.apply_all_rules
        assert len(trs.rules) == 2
        assert isinstance(trs.rules[0], BitguardClassifier)
        assert isinstance(trs.rules[1], OutOfDateClassifier)

        assert 'ruleset02' in p.rule_system
        assert isinstance(p.rule_system.ruleset02, TransformRuleSystem)
        trs = p.rule_system.ruleset02
        assert trs.act == trs.apply_until_action_succeeds
        assert len(trs.rules) == 1
        assert isinstance(trs.rules[0], SetWindowPos)

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

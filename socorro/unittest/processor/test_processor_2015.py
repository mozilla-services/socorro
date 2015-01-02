import ujson

from socorro.unittest.testbase import TestCase
from nose.tools import eq_, ok_
from mock import Mock, patch

from configman import ConfigurationManager
from configman.dotdict import DotDict

from socorro.processor.processor_2015 import (
    Processor2015,
    rule_sets_from_string
)
from socorro.lib.util import DotDict as SDotDict
from socorro.lib.transform_rules import TransformRuleSystem
from socorro.processor.support_classifiers import (
    BitguardClassifier,
    OutOfDateClassifier
)
from socorro.processor.skunk_classifiers import (
    SetWindowPos,
    UpdateWindowAttributes
)

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
        'socorro.processor.skunk_classifiers.SetWindowPos, '
        'socorro.processor.skunk_classifiers.UpdateWindowAttributes'
    ],
]
rule_set_02_str = ujson.dumps(rule_set_02)


class TestProcessor2015(TestCase):
    def test_rule_sets_from_string_1(self):
        rule_set_config = rule_sets_from_string(rule_set_01_str)
        rc = rule_set_config.get_required_config()
        ok_('ruleset01' in rc)
        eq_('tag0.tag1', rc.ruleset01.tag.default)
        eq_(
            'socorro.lib.transform_rules.TransformRuleSystem',
            rc.ruleset01.rule_system_class.default
        )
        eq_('apply_all_rules', rc.ruleset01.action.default)
        eq_(
            'socorro.processor.support_classifiers.BitguardClassifier, '
            'socorro.processor.support_classifiers.OutOfDateClassifier',
            rc.ruleset01.rules_list.default
        )

    def test_rule_sets_from_string_2(self):
        rule_set_config = rule_sets_from_string(rule_set_02_str)
        rc = rule_set_config.get_required_config()

        ok_('ruleset01' in rc)
        eq_('tag0.tag1', rc.ruleset01.tag.default)
        eq_(
            'socorro.lib.transform_rules.TransformRuleSystem',
            rc.ruleset01.rule_system_class.default
        )
        eq_('apply_all_rules', rc.ruleset01.action.default)
        eq_(
            'socorro.processor.support_classifiers.BitguardClassifier, '
            'socorro.processor.support_classifiers.OutOfDateClassifier',
            rc.ruleset01.rules_list.default
        )

        ok_('ruleset02' in rc)
        eq_('tag2.tag3', rc.ruleset02.tag.default)
        eq_(
            'socorro.lib.transform_rules.TransformRuleSystem',
            rc.ruleset02.rule_system_class.default
        )
        eq_('apply_until_action_succeeds', rc.ruleset02.action.default)
        eq_(
            'socorro.processor.skunk_classifiers.SetWindowPos, '
            'socorro.processor.skunk_classifiers.UpdateWindowAttributes',
            rc.ruleset02.rules_list.default
        )

    def test_Processor2015_init(self):
        cm = ConfigurationManager(
            definition_source=Processor2015.get_required_config(),
            values_source_list=[{'rule_sets': rule_set_02_str}],
        )
        config = cm.get_config()
        config.logger = Mock()

        p = Processor2015(config)

        ok_(isinstance(p.rule_system, DotDict))
        eq_(len(p.rule_system), 2)
        ok_('ruleset01' in p.rule_system)
        print p.rule_system.ruleset01
        ok_(isinstance(p.rule_system.ruleset01, TransformRuleSystem))
        trs = p.rule_system.ruleset01
        eq_(trs.act, trs.apply_all_rules)
        eq_(len(trs.rules), 2)
        ok_(isinstance(trs.rules[0], BitguardClassifier))
        ok_(isinstance(trs.rules[1], OutOfDateClassifier))

        ok_('ruleset02' in p.rule_system)
        ok_(isinstance(p.rule_system.ruleset02, TransformRuleSystem))
        trs = p.rule_system.ruleset02
        eq_(trs.act, trs.apply_until_action_succeeds)
        eq_(len(trs.rules), 2)
        ok_(isinstance(trs.rules[0], SetWindowPos))
        ok_(isinstance(trs.rules[1], UpdateWindowAttributes))

    def test_convert_raw_crash_to_processed_crash_no_rules(self):
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
            processed_crash = p.convert_raw_crash_to_processed_crash(
                raw_crash,
                raw_dumps
            )

        ok_(processed_crash.success)
        eq_(processed_crash.started_datetime, '2015-01-01T00:00:00')
        eq_(processed_crash.startedDateTime, '2015-01-01T00:00:00')
        eq_(processed_crash.completed_datetime, '2015-01-01T00:00:00')
        eq_(processed_crash.completeddatetime, '2015-01-01T00:00:00')
        eq_(processed_crash.processor_notes, 'dwight; Processor2015')

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_

from socorro.processor.rules.memory_report_extraction import (
    MemoryReportExtraction,
)
from socorro.unittest.testbase import TestCase
from socorro.unittest.processor.test_signature_utilities import (
    create_basic_fake_processor
)


class TestMemoryReportExtraction(TestCase):
    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        raw_crash = {}
        processed_crash = {}

        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        ok_(not predicate_result)

        processed_crash['memory_report'] = {}
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        ok_(not predicate_result)

        raw_crash['pid'] = None
        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        ok_(not predicate_result)

    def test_predicate(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        raw_crash = {}
        raw_crash['pid'] = 42

        processed_crash = {}
        processed_crash['memory_report'] = {
            'reports': [],
        }

        predicate_result = rule.predicate(raw_crash, {}, processed_crash, {})
        ok_(predicate_result)

    def test_action_success(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        processed_crash = {}
        processed_crash['memory_report'] = {
            'reports': [
                # ...
            ]
        }

        raw_crash = {}
        raw_crash['pid'] = 42

        action_result = rule.action(
            raw_crash, {}, processed_crash, {}
        )
        ok_(action_result)
        ok_(processed_crash['memory_measures'])

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import json
from nose.tools import eq_, ok_

from socorro.processor.rules.memory_report_extraction import (
    MemoryReportExtraction,
)
from socorro.unittest.testbase import TestCase
from socorro.unittest.processor.test_signature_utilities import (
    create_basic_fake_processor
)


HERE = os.path.dirname(__file__)


def get_example_file_data(filename):
    file_path = os.path.join(HERE, 'memory_reports', filename)
    with open(file_path) as f:
        return json.loads(f.read())


class TestMemoryReportExtraction(TestCase):
    def get_config(self):
        fake_processor = create_basic_fake_processor()
        return fake_processor.config

    def test_predicate_no_match(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        processed_crash = {}

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

        processed_crash['memory_report'] = {}
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

        processed_crash['json_dump'] = {
            'pid': None,
        }
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

    def test_predicate(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        processed_crash = {}
        processed_crash['memory_report'] = {'reports': []}
        processed_crash['json_dump'] = {'pid': 42}

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(predicate_result)

    def test_action_success(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        memory_report = get_example_file_data('good.json')

        processed_crash = {}
        processed_crash['memory_report'] = memory_report
        processed_crash['json_dump'] = {'pid': 11620}

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(action_result)
        ok_('memory_measures' in processed_crash)

        expected_res = {
            'explicit': 232227872,
            'ghost-windows': 7,
            'heap-allocated': 216793184,
            'heap-unclassified': 171114283,
            'private': 182346923,
            'resident': 330346496,
            'resident-unique': 253452288,
            'system-heap-allocated': 123456,
            'top-non-detached': 45678901,
            'vsize': 1481437184,
            'vsize-max-contiguous': 2834628,
        }
        eq_(processed_crash['memory_measures'], expected_res)

        # Test with a different pid.
        processed_crash['json_dump']['pid'] = 11717

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(action_result)
        ok_('memory_measures' in processed_crash)

        expected_res = {
            'explicit': 20655576,
            'ghost-windows': 0,
            'heap-allocated': 20655576,
            'heap-unclassified': 20655576,
            'private': 0,
            'resident': 123518976,
            'resident-unique': 56209408,
            'system-heap-allocated': 234567,
            'top-non-detached': 0,
            'vsize': 905883648,
            'vsize-max-contiguous': 5824618,
        }
        eq_(processed_crash['memory_measures'], expected_res)

    def test_action_failure_bad_kind(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        memory_report = get_example_file_data('bad_kind.json')

        processed_crash = {}
        processed_crash['memory_report'] = memory_report
        processed_crash['json_dump'] = {'pid': 11620}

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(not action_result)
        ok_('memory_measures' not in processed_crash)

        config.logger.info.assert_called_with(
            'Unable to extract measurements from memory report: '
            'bad kind for an explicit/ report: explicit/foo, 2'
        )

    def test_action_failure_bad_units(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        memory_report = get_example_file_data('bad_units.json')

        processed_crash = {}
        processed_crash['memory_report'] = memory_report
        processed_crash['json_dump'] = {'pid': 11620}

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(not action_result)
        ok_('memory_measures' not in processed_crash)

        config.logger.info.assert_called_with(
            'Unable to extract measurements from memory report: '
            'bad units for an explicit/ report: explicit/foo, 1'
        )

    def test_action_failure_bad_unrecognizable(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        memory_report = get_example_file_data('bad_unrecognizable.json')

        processed_crash = {}
        processed_crash['memory_report'] = memory_report
        processed_crash['json_dump'] = {'pid': 11620}

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(not action_result)
        ok_('memory_measures' not in processed_crash)

        config.logger.info.assert_called_with(
            'Unable to extract measurements from memory report: '
            'not a recognisable memory reports'
        )

    def test_action_failure_bad_pid(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        memory_report = get_example_file_data('good.json')

        processed_crash = {}
        processed_crash['memory_report'] = memory_report
        processed_crash['json_dump'] = {'pid': 12345}

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(not action_result)
        ok_('memory_measures' not in processed_crash)

        config.logger.info.assert_called_with(
            'Unable to extract measurements from memory report: '
            'no measurements found for pid 12345'
        )

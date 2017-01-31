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

    def test_predicate_success(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        processed_crash = {}
        processed_crash['memory_report'] = {
            'reports': [],
            'version': '',
            'hasMozMallocUsableSize': '',
        }
        processed_crash['json_dump'] = {'pid': 42}

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(predicate_result)

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

    def test_predicate_failure_bad_unrecognizable(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        memory_report = get_example_file_data('bad_unrecognizable.json')

        processed_crash = {}
        processed_crash['memory_report'] = memory_report
        processed_crash['json_dump'] = {'pid': 11620}

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        ok_(not predicate_result)

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
            'gfx_textures': 0,
            'ghost_windows': 7,
            'heap_allocated': 216793184,
            'heap_overhead': 14483360,
            'heap_unclassified': 171114283,
            'host_object_urls': 0,
            'images': 0,
            'js_main_runtime': 0,
            'private': 182346923,
            'resident': 330346496,
            'resident_unique': 253452288,
            'system_heap_allocated': 123456,
            'top_non_detached': 45678901,
            'vsize': 1481437184,
            'vsize_max_contiguous': 2834628,
        }
        eq_(processed_crash['memory_measures'], expected_res)

        # Test with a different pid.
        processed_crash['json_dump']['pid'] = 11717

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(action_result)
        ok_('memory_measures' in processed_crash)

        expected_res = {
            'explicit': 20655576,
            'gfx_textures': 123456,
            'ghost_windows': 0,
            'heap_allocated': 20655576,
            'heap_overhead': 0,
            'heap_unclassified': 20593000,
            'host_object_urls': 5,
            'images': 62576,
            'js_main_runtime': 600000,
            'private': 0,
            'resident': 123518976,
            'resident_unique': 56209408,
            'system_heap_allocated': 234567,
            'top_non_detached': 0,
            'vsize': 905883648,
            'vsize_max_contiguous': 5824618,
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

    def test_action_failure_key_error(self):
        config = self.get_config()
        rule = MemoryReportExtraction(config)

        memory_report = get_example_file_data('bad_missing_key.json')

        processed_crash = {}
        processed_crash['memory_report'] = memory_report
        processed_crash['json_dump'] = {'pid': 11620}

        action_result = rule.action({}, {}, processed_crash, {})
        ok_(not action_result)
        ok_('memory_measures' not in processed_crash)

        config.logger.info.assert_called_with(
            'Unable to extract measurements from memory report: '
            "key 'process' is missing from a report"
        )

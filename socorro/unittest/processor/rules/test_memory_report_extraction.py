# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import json

from socorro.processor.rules.memory_report_extraction import MemoryReportExtraction


HERE = os.path.dirname(__file__)


def get_example_file_data(filename):
    file_path = os.path.join(HERE, "memory_reports", filename)
    with open(file_path) as f:
        return json.loads(f.read())


class TestMemoryReportExtraction:
    def test_predicate_success(self):
        rule = MemoryReportExtraction()

        processed_crash = {
            "memory_report": {
                "reports": [],
                "version": "",
                "hasMozMallocUsableSize": "",
            },
            "json_dump": {"pid": 42},
        }

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert predicate_result

    def test_predicate_no_match(self):
        rule = MemoryReportExtraction()

        processed_crash = {}

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert not predicate_result

        processed_crash["memory_report"] = {}
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert not predicate_result

        processed_crash["json_dump"] = {"pid": None}
        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert not predicate_result

    def test_predicate_failure_bad_unrecognizable(self):
        rule = MemoryReportExtraction()

        memory_report = get_example_file_data("bad_unrecognizable.json")

        processed_crash = {
            "memory_report": memory_report,
            "json_dump": {"pid": 11620},
        }

        predicate_result = rule.predicate({}, {}, processed_crash, {})
        assert not predicate_result

    def test_action_success(self):
        rule = MemoryReportExtraction()

        memory_report = get_example_file_data("good.json")

        processed_crash = {
            "memory_report": memory_report,
            "json_dump": {"pid": 11620},
        }
        rule.action({}, {}, processed_crash, {})

        assert "memory_measures" in processed_crash

        expected_res = {
            "explicit": 232227872,
            "gfx_textures": 0,
            "ghost_windows": 7,
            "heap_allocated": 216793184,
            "heap_overhead": 14483360,
            "heap_unclassified": 171114283,
            "host_object_urls": 0,
            "images": 0,
            "js_main_runtime": 0,
            "private": 182346923,
            "resident": 330346496,
            "resident_unique": 253452288,
            "system_heap_allocated": 123456,
            "top_none_detached": 45678901,
            "vsize": 1481437184,
            "vsize_max_contiguous": 2834628,
        }
        assert processed_crash["memory_measures"] == expected_res

        # Test with a different pid
        processed_crash["json_dump"]["pid"] = 11717
        rule.action({}, {}, processed_crash, {})

        assert "memory_measures" in processed_crash

        expected_res = {
            "explicit": 20655576,
            "gfx_textures": 123456,
            "ghost_windows": 0,
            "heap_allocated": 20655576,
            "heap_overhead": 0,
            "heap_unclassified": 20593000,
            "host_object_urls": 5,
            "images": 62576,
            "js_main_runtime": 600000,
            "private": 0,
            "resident": 123518976,
            "resident_unique": 56209408,
            "system_heap_allocated": 234567,
            "top_none_detached": 0,
            "vsize": 905883648,
            "vsize_max_contiguous": 5824618,
        }
        assert processed_crash["memory_measures"] == expected_res

    def test_action_failure_bad_kind(self, caplogpp):
        caplogpp.set_level("DEBUG")

        rule = MemoryReportExtraction()

        memory_report = get_example_file_data("bad_kind.json")

        processed_crash = {
            "memory_report": memory_report,
            "json_dump": {"pid": 11620},
        }
        rule.action({}, {}, processed_crash, {})

        assert "memory_measures" not in processed_crash

        msgs = [rec.message for rec in caplogpp.records]
        assert msgs[0] == (
            "Unable to extract measurements from memory report: "
            "bad kind for an explicit/ report: explicit/foo, 2"
        )

    def test_action_failure_bad_units(self, caplogpp):
        caplogpp.set_level("DEBUG")

        rule = MemoryReportExtraction()

        memory_report = get_example_file_data("bad_units.json")

        processed_crash = {
            "memory_report": memory_report,
            "json_dump": {"pid": 11620},
        }
        rule.action({}, {}, processed_crash, {})

        assert "memory_measures" not in processed_crash

        msgs = [rec.message for rec in caplogpp.records]
        assert msgs[0] == (
            "Unable to extract measurements from memory report: "
            "bad units for an explicit/ report: explicit/foo, 1"
        )

    def test_action_failure_bad_pid(self, caplogpp):
        caplogpp.set_level("DEBUG")

        rule = MemoryReportExtraction()

        memory_report = get_example_file_data("good.json")

        processed_crash = {
            "memory_report": memory_report,
            "json_dump": {"pid": 12345},
        }
        rule.action({}, {}, processed_crash, {})

        assert "memory_measures" not in processed_crash

        msgs = [rec.message for rec in caplogpp.records]
        assert msgs[0] == (
            "Unable to extract measurements from memory report: "
            "no measurements found for pid 12345"
        )

    def test_action_failure_key_error(self, caplogpp):
        caplogpp.set_level("DEBUG")

        rule = MemoryReportExtraction()

        memory_report = get_example_file_data("bad_missing_key.json")

        processed_crash = {
            "memory_report": memory_report,
            "json_dump": {"pid": 11620},
        }
        rule.action({}, {}, processed_crash, {})

        assert "memory_measures" not in processed_crash

        msgs = [rec.message for rec in caplogpp.records]
        assert msgs[0] == (
            "Unable to extract measurements from memory report: "
            "key 'process' is missing from a report"
        )

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import datetime
from io import BytesIO
import json
from unittest import mock

import requests_mock
import pytest

from socorro.lib.libsocorrodataschema import get_schema
from socorro.processor.rules.mozilla import (
    AccessibilityRule,
    AddonsRule,
    BetaVersionRule,
    BreadcrumbsRule,
    ConvertModuleSignatureInfoRule,
    CopyFromRawCrashRule,
    DatesAndTimesRule,
    DistributionIdRule,
    ESRVersionRewrite,
    FenixVersionRewriteRule,
    MacBootArgsRule,
    MacCrashInfoRule,
    MajorVersionRule,
    MissingSymbolsRule,
    ModulesInStackRule,
    ModuleURLRewriteRule,
    MozCrashReasonRule,
    OSPrettyVersionRule,
    OutOfMemoryBinaryRule,
    PHCRule,
    PluginRule,
    ReportTypeRule,
    SignatureGeneratorRule,
    SubmittedFromRule,
    ThemePrettyNameRule,
    TopMostFilesRule,
    UtilityActorsNameRule,
)
from socorro.processor.pipeline import Status
from socorro.signature.generator import SignatureGenerator


PROCESSED_CRASH_SCHEMA = get_schema("processed_crash.schema.yaml")


canonical_standard_raw_crash = {
    "uuid": "00000000-0000-0000-0000-000002140504",
    "InstallTime": "1335439892",
    "AdapterVendorID": "0x1002",
    "TotalVirtualMemory": "4294836224",
    "Comments": "why did my browser crash?  #fail",
    "Theme": "classic/1.0",
    "Version": "12.0",
    "Vendor": "Mozilla",
    "EMCheckCompatibility": "true",
    "id": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
    "buildid": "20120420145725",
    "AvailablePageFile": "10641510400",
    "version": "12.0",
    "AdapterDeviceID": "0x7280",
    "ReleaseChannel": "release",
    "submitted_timestamp": "2012-05-08T23:26:33.454482+00:00",
    "URL": "http://www.mozilla.com",
    "Notes": (
        "AdapterVendorID: 0x1002, AdapterDeviceID: 0x7280, "
        "AdapterSubsysID: 01821043, "
        "AdapterDriverVersion: 8.593.100.0\nD3D10 Layers? D3D10 "
        "Layers- D3D9 Layers? D3D9 Layers- "
    ),
    "CrashTime": "1336519554",
    "AvailablePhysicalMemory": "2227773440",
    "StartupTime": "1336499438",
    "Add-ons": (
        "adblockpopups@jessehakanen.net:0.3,"
        "dmpluginff%40westbyte.com:1%2C4.8,"
        "firebug@software.joehewitt.com:1.9.1,"
        "killjasmin@pierros14.com:2.4,"
        "support@surfanonymous-free.com:1.0,"
        "uploader@adblockfilters.mozdev.org:2.1,"
        "{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}:20111107,"
        "{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}:2.0.3,"
        "anttoolbar@ant.com:2.4.6.4,"
        "{972ce4c6-7e08-4474-a285-3208198ce6fd}:12.0,"
        "elemhidehelper@adblockplus.org:1.2.1"
    ),
    "BuildID": "20120420145725",
    "SecondsSinceLastCrash": "86985",
    "ProductName": "Firefox",
    "AvailableVirtualMemory": "3812708352",
    "SystemMemoryUsePercentage": "48",
    "ProductID": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
    "Distributor": "Mozilla",
    "Distributor_version": "12.0",
}

canonical_processed_crash = {
    "json_dump": {
        "modules": [
            {
                "end_addr": "0x12e6000",
                "filename": "plugin-container.exe",
                "version": "26.0.0.5084",
                "debug_id": "8385BD80FD534F6E80CF65811735A7472",
                "debug_file": "plugin-container.pdb",
                "base_addr": "0x12e0000",
            },
            {
                "end_addr": "0x12e6000",
                "filename": "plugin-container.exe",
                "version": "26.0.0.5084",
                "debug_id": "8385BD80FD534F6E80CF65811735A7472",
                "debug_file": "plugin-container.pdb",
                "base_addr": "0x12e0000",
            },
            {
                "end_addr": "0x12e6000",
                "filename": "plugin-container.exe",
                "version": "26.0.0.5084",
                "debug_id": "8385BD80FD534F6E80CF65811735A7472",
                "debug_file": "plugin-container.pdb",
                "base_addr": "0x12e0000",
            },
        ],
    }
}


SCHEMA_WITH_ALL_TYPES = {
    "type": "object",
    "properties": {
        "accessibility": {
            "description": "Set to 'Active' by accessibility service",
            "type": "boolean",
            "source_annotation": "Accessibility",
        },
        "available_page_file": {
            "description": "Maximum amount of memory process can commit.",
            "type": "integer",
            "source_annotation": "AvailablePageFile",
        },
        "complex_structure": {
            "description": "A complex structure.",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "shoes": {
                    "type": "object",
                    "properties": {
                        "brand": {"type": "string"},
                    },
                },
            },
            "source_annotation": "ComplexStructure",
        },
        "uptime_ts": {
            "description": "Uptime in seconds as a float.",
            "type": "number",
            "source_annotation": "UptimeTS",
        },
        "url": {
            "description": "URL the user was visiting when the crash happened.",
            "type": ["string", "null"],
            "source_annotation": "URL",
        },
    },
}


SCHEMA_WITH_DEFAULT = {
    "type": "object",
    "properties": {
        "process_type": {
            "description": "Type of the process that crashed.",
            "default": "parent",
            "examples": ["any", "parent", "plugin", "content", "gpu"],
            "type": "string",
            "source_annotation": "ProcessType",
        },
    },
}


class TestCopyFromRawCrashRule:
    def get_copy_item(self, rule, annotation):
        for copy_item in rule.fields:
            if copy_item.annotation == annotation:
                return copy_item

        raise Exception(f"no CopyItem for {annotation}")

    def test_empty(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)

        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert raw_crash == {}
        assert processed_crash == {}
        assert status.notes == []

    def test_boolean(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "Accessibility")

        for value in ("1", "true", "TRUE"):
            raw_crash = {copy_item.annotation: value}
            dumps = {}
            processed_crash = {}
            status = Status()
            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

            assert processed_crash == {copy_item.key: True}
            assert status.notes == []

        for value in ("0", "false", "FALSE"):
            raw_crash = {copy_item.annotation: value}
            dumps = {}
            processed_crash = {}
            status = Status()
            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

            assert processed_crash == {copy_item.key: False}
            assert status.notes == []

    def test_invalid_boolean(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "Accessibility")

        raw_crash = {copy_item.annotation: "foo"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {}
        assert status.notes == [f"{copy_item.annotation} has non-boolean value foo"]

    def test_integer(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "AvailablePageFile")

        raw_crash = {copy_item.annotation: "1"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {copy_item.key: 1}
        assert status.notes == []

    def test_invalid_integer(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "AvailablePageFile")

        raw_crash = {copy_item.annotation: "foo"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {}
        assert status.notes == [f"{copy_item.annotation} has a non-int value"]

    def test_number(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "UptimeTS")

        raw_crash = {copy_item.annotation: "10.0"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {copy_item.key: 10.0}
        assert status.notes == []

    def test_invalid_number(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "UptimeTS")

        raw_crash = {copy_item.annotation: "foo"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {}
        assert status.notes == [f"{copy_item.annotation} has a non-float value"]

    def test_string(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "URL")

        raw_crash = {copy_item.annotation: "some string"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {copy_item.key: "some string"}
        assert status.notes == []

    def test_object(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "ComplexStructure")

        json_data = {
            "name": "Dennis",
            "age": 37,
            "shoes": {
                "brand": "brownstone",
            },
        }

        raw_crash = {copy_item.annotation: json.dumps(json_data)}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {copy_item.key: json_data}
        assert status.notes == []

    def test_object_invalid_json(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "ComplexStructure")

        raw_crash = {copy_item.annotation: "{"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert copy_item.key not in processed_crash
        assert status.notes == ["ComplexStructure value is malformed json"]

    def test_object_invalid_value(self, tmp_path):
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_ALL_TYPES)
        copy_item = self.get_copy_item(rule, "ComplexStructure")

        json_data = {
            "name": 42,
            "age": 37,
            "shoes": {
                "brand": "brownstone",
            },
        }

        raw_crash = {copy_item.annotation: json.dumps(json_data)}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert copy_item.key not in processed_crash
        assert status.notes == ["ComplexStructure value is malformed complex_structure"]

    def test_default(self, tmp_path):
        # Verify that the default is used if the annotation is missing
        rule = CopyFromRawCrashRule(schema=SCHEMA_WITH_DEFAULT)
        copy_item = self.get_copy_item(rule, "ProcessType")

        raw_crash = {copy_item.annotation: "gpu"}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {copy_item.key: "gpu"}
        assert status.notes == []

        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {copy_item.key: copy_item.default}
        assert status.notes == []


class TestConvertModuleSignatureInfoRule:
    def test_no_value(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = ConvertModuleSignatureInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert raw_crash == {}
        assert processed_crash == {}

    def test_string_value(self, tmp_path):
        raw_crash = {"ModuleSignatureInfo": "{}"}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = ConvertModuleSignatureInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert raw_crash == {"ModuleSignatureInfo": "{}"}
        assert processed_crash == {}

    def test_object_value(self, tmp_path):
        raw_crash = {"ModuleSignatureInfo": {"foo": "bar"}}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = ConvertModuleSignatureInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert raw_crash == {"ModuleSignatureInfo": '{"foo": "bar"}'}
        assert processed_crash == {}

    def test_object_value_with_dict(self, tmp_path):
        raw_crash = {"ModuleSignatureInfo": {"foo": "bar"}}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = ConvertModuleSignatureInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert raw_crash == {"ModuleSignatureInfo": '{"foo": "bar"}'}
        assert processed_crash == {}


class TestSubmittedFromRule:
    @pytest.mark.parametrize(
        "submitted_from, submitted_from_infobar, expected_submitted_from, expected_submitted_from_infobar",
        [
            # If neither are specified
            (None, None, "Unknown", False),
            # Test SubmittedFromInfobar variations
            (None, True, "Infobar", True),
            (None, "true", "Infobar", True),
            (None, "1", "Infobar", True),
            (None, "0", "Unknown", False),
            (None, False, "Unknown", False),
            (None, "false", "Unknown", False),
            # Test SubmittedFrom variations
            ("Infobar", None, "Infobar", True),
            ("Auto", None, "Auto", False),
        ],
    )
    def test_action(
        self,
        tmp_path,
        submitted_from,
        submitted_from_infobar,
        expected_submitted_from,
        expected_submitted_from_infobar,
    ):
        raw_crash = {}

        # Crash reports should have one or the other, but not both, but the world is
        # weird and it's not a property we care enough to enforce
        if submitted_from is not None:
            raw_crash["SubmittedFrom"] = submitted_from
        if submitted_from_infobar is not None:
            raw_crash["SubmittedFromInfobar"] = submitted_from_infobar

        dumps = {}
        processed_crash = {}
        status = Status()
        rule = SubmittedFromRule()
        rule.action(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash == {
            "submitted_from": expected_submitted_from,
            "submitted_from_infobar": expected_submitted_from_infobar,
        }


class TestPluginRule:
    def test_browser_hang(self, tmp_path):
        raw_crash = {
            "ProcessType": "parent",
        }
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = PluginRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "plugin_filename" not in processed_crash
        assert "plugin_name" not in processed_crash
        assert "plugin_version" not in processed_crash

    def test_plugin_bits(self, tmp_path):
        raw_crash = {
            "ProcessType": "plugin",
            "PluginName": "name1",
            "PluginFilename": "filename1",
            "PluginVersion": "1.0",
        }
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = PluginRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        expected = {
            "plugin_name": "name1",
            "plugin_filename": "filename1",
            "plugin_version": "1.0",
        }
        assert processed_crash == expected


class TestAccessibilityRule:
    def test_not_there(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = AccessibilityRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["accessibility"] is False

    def test_active(self, tmp_path):
        raw_crash = {"Accessibility": "Active"}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = AccessibilityRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["accessibility"] is True


class TestAddonsRule:
    def test_action_nothing_unexpected(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {}
        status = Status()

        addons_rule = AddonsRule()
        addons_rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        # the raw crash & dumps should not have changed
        assert raw_crash == canonical_standard_raw_crash
        assert dumps == {}

        expected_addon_list = [
            "adblockpopups@jessehakanen.net:0.3",
            "dmpluginff@westbyte.com:1,4.8",
            "firebug@software.joehewitt.com:1.9.1",
            "killjasmin@pierros14.com:2.4",
            "support@surfanonymous-free.com:1.0",
            "uploader@adblockfilters.mozdev.org:2.1",
            "{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}:20111107",
            "{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}:2.0.3",
            "anttoolbar@ant.com:2.4.6.4",
            "{972ce4c6-7e08-4474-a285-3208198ce6fd}:12.0",
            "elemhidehelper@adblockplus.org:1.2.1",
        ]
        assert processed_crash["addons"] == expected_addon_list
        assert processed_crash["addons_checked"] is True

    def test_action_colon_in_addon_version(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["Add-ons"] = "adblockpopups@jessehakanen.net:0:3:1"
        raw_crash["EMCheckCompatibility"] = "Nope"
        dumps = {}
        processed_crash = {}
        status = Status()

        addons_rule = AddonsRule()
        addons_rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        expected_addon_list = ["adblockpopups@jessehakanen.net:0:3:1"]
        assert processed_crash["addons"] == expected_addon_list
        assert processed_crash["addons_checked"] is False

    def test_action_addon_is_nonsense(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["Add-ons"] = "naoenut813teq;mz;<[`19ntaotannn8999anxse `"
        dumps = {}
        processed_crash = {}
        status = Status()

        addons_rule = AddonsRule()
        addons_rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        expected_addon_list = ["naoenut813teq;mz;<[`19ntaotannn8999anxse `:NO_VERSION"]
        assert processed_crash["addons"] == expected_addon_list
        assert processed_crash["addons_checked"] is True


class TestDatesAndTimesRule:
    def test_get_truncate_or_warn(self):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        status = Status()
        ret = DatesAndTimesRule._get_truncate_or_warn(
            raw_crash, "submitted_timestamp", status, "", 50
        )
        assert ret == "2012-05-08T23:26:33.454482+00:00"
        assert status.notes == []

        status = Status()
        ret = DatesAndTimesRule._get_truncate_or_warn(
            raw_crash,
            "terrible_timestamp",
            status,
            "2012-05-08T23:26:33.454482+00:00",
            "50",
        )
        assert ret == "2012-05-08T23:26:33.454482+00:00"
        assert status.notes == ["WARNING: raw_crash missing terrible_timestamp"]

        raw_crash["submitted_timestamp"] = 17
        status = Status()
        ret = DatesAndTimesRule._get_truncate_or_warn(
            raw_crash,
            "submitted_timestamp",
            status,
            "2012-05-08T23:26:33.454482+00:00",
            "50",
        )
        assert ret == "2012-05-08T23:26:33.454482+00:00"
        try:
            val = 42
            val[:1]
        except TypeError as err:
            type_error_value = str(err)
        assert status.notes == [
            "WARNING: raw_crash[submitted_timestamp] contains unexpected "
            "value: 17; %s" % type_error_value
        ]

    def test_everything_we_hoped_for(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {
            "startup_time": raw_crash["StartupTime"],
        }
        status = Status()

        rule = DatesAndTimesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert (
            processed_crash["submitted_timestamp"] == raw_crash["submitted_timestamp"]
        )
        assert (
            processed_crash["date_processed"] == processed_crash["submitted_timestamp"]
        )
        assert processed_crash["crash_time"] == 1336519554
        assert processed_crash["client_crash_date"] == "2012-05-08T23:25:54+00:00"
        assert processed_crash["install_age"] == 1079662
        assert processed_crash["uptime"] == 20116
        assert processed_crash["last_crash"] == 86985

    def test_no_crash_time(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        del raw_crash["CrashTime"]
        dumps = {}
        processed_crash = {
            "startup_time": raw_crash["StartupTime"],
        }
        status = Status()

        rule = DatesAndTimesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        expected = datetime.datetime.fromisoformat(raw_crash["submitted_timestamp"])
        expected_timestamp = int(expected.timestamp())
        assert (
            processed_crash["submitted_timestamp"] == raw_crash["submitted_timestamp"]
        )
        assert (
            processed_crash["date_processed"] == processed_crash["submitted_timestamp"]
        )
        assert processed_crash["crash_time"] == expected_timestamp
        assert processed_crash["client_crash_date"] == "2012-05-08T23:26:33+00:00"
        assert processed_crash["install_age"] == 1079701
        assert processed_crash["uptime"] == 20155
        assert processed_crash["last_crash"] == 86985

        assert status.notes == [
            "WARNING: raw_crash missing CrashTime",
            "client_crash_date is unknown",
        ]

    def test_no_startup_time(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        del raw_crash["StartupTime"]
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = DatesAndTimesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert (
            processed_crash["submitted_timestamp"] == raw_crash["submitted_timestamp"]
        )
        assert (
            processed_crash["date_processed"] == processed_crash["submitted_timestamp"]
        )
        assert processed_crash["crash_time"] == 1336519554
        assert processed_crash["client_crash_date"] == "2012-05-08T23:25:54+00:00"
        assert processed_crash["install_age"] == 1079662
        assert processed_crash["uptime"] == 0
        assert processed_crash["last_crash"] == 86985
        assert status.notes == []

    def test_bad_install_time(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["InstallTime"] = "feed the goats"
        dumps = {}
        processed_crash = {
            "startup_time": raw_crash["StartupTime"],
        }
        status = Status()

        rule = DatesAndTimesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert (
            processed_crash["submitted_timestamp"] == raw_crash["submitted_timestamp"]
        )
        assert (
            processed_crash["date_processed"] == processed_crash["submitted_timestamp"]
        )
        assert processed_crash["crash_time"] == 1336519554
        assert processed_crash["client_crash_date"] == "2012-05-08T23:25:54+00:00"
        assert processed_crash["install_age"] == 1336519554
        assert processed_crash["uptime"] == 20116
        assert processed_crash["last_crash"] == 86985
        assert status.notes == ['non-integer value of "InstallTime"']

    def test_bad_seconds_since_last_crash(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["SecondsSinceLastCrash"] = "feed the goats"
        dumps = {}
        processed_crash = {"startup_time": raw_crash["StartupTime"]}
        status = Status()

        rule = DatesAndTimesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert (
            processed_crash["submitted_timestamp"] == raw_crash["submitted_timestamp"]
        )
        assert (
            processed_crash["date_processed"] == processed_crash["submitted_timestamp"]
        )
        assert processed_crash["crash_time"] == 1336519554
        assert processed_crash["client_crash_date"] == "2012-05-08T23:25:54+00:00"
        assert processed_crash["install_age"] == 1079662
        assert processed_crash["uptime"] == 20116
        assert processed_crash["last_crash"] is None
        assert status.notes == ['non-integer value of "SecondsSinceLastCrash"']

    def test_absent_seconds_since_last_crash(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash.pop("SecondsSinceLastCrash")
        dumps = {}
        processed_crash = {"startup_time": raw_crash["StartupTime"]}
        status = Status()

        rule = DatesAndTimesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert (
            processed_crash["submitted_timestamp"] == raw_crash["submitted_timestamp"]
        )
        assert (
            processed_crash["date_processed"] == processed_crash["submitted_timestamp"]
        )
        assert processed_crash["crash_time"] == 1336519554
        assert processed_crash["client_crash_date"] == "2012-05-08T23:25:54+00:00"
        assert processed_crash["install_age"] == 1079662
        assert processed_crash["uptime"] == 20116
        assert processed_crash["last_crash"] is None
        assert status.notes == []


class TestMacBootArgsRule:
    @pytest.mark.parametrize(
        "processed, expected",
        [
            ({}, False),
            ({"json_dump": {}}, False),
            ({"json_dump": {"mac_boot_args": None}}, False),
            ({"json_dump": {"mac_boot_args": ""}}, False),
            ({"json_dump": {"mac_boot_args": "-v"}}, True),
        ],
    )
    def test_predicate(self, tmp_path, processed, expected):
        raw_crash = {}
        dumps = {}
        status = Status()
        rule = MacBootArgsRule()

        result = rule.predicate(raw_crash, dumps, processed, str(tmp_path), status)

        assert result == expected

    @pytest.mark.parametrize(
        "processed, mac_boot_args, has_mac_boot_args",
        [
            ({"json_dump": {"mac_boot_args": "-v"}}, "-v", True),
            ({"json_dump": {"mac_boot_args": "  -v  "}}, "-v", True),
        ],
    )
    def test_valid_value(self, tmp_path, processed, mac_boot_args, has_mac_boot_args):
        raw_crash = {}
        dumps = {}
        status = Status()
        rule = MacBootArgsRule()

        rule.act(raw_crash, dumps, processed, str(tmp_path), status)

        assert processed["mac_boot_args"] == mac_boot_args
        assert processed["has_mac_boot_args"] == has_mac_boot_args

    def test_not_string(self, tmp_path):
        raw_crash = {}
        processed = {"json_dump": {"mac_boot_args": 5}}
        dumps = {}
        status = Status()
        rule = MacBootArgsRule()

        rule.act(raw_crash, dumps, processed, str(tmp_path), status)

        assert "mac_boot_args" not in processed
        assert "has_mac_boot_args" not in processed
        assert "MacBootArgsRule: mac_boot_args is int and not str" in status.notes


class TestMacCrashInfoRule:
    @pytest.mark.parametrize(
        "processed, expected",
        [
            # These shouldn't result in a mac_crash_info
            ({}, False),
            ({"json_dump": {}}, False),
            ({"json_dump": {"mac_crash_info": None}}, False),
            ({"json_dump": {"mac_crash_info": {}}}, False),
            ({"json_dump": {"mac_crash_info": {"num_records": 0}}}, False),
            # This should
            ({"json_dump": {"mac_crash_info": {"num_records": 1}}}, True),
        ],
    )
    def test_mac_crash_info_variations(self, tmp_path, processed, expected):
        raw_crash = {}
        dumps = {}
        status = Status()
        rule = MacCrashInfoRule()

        rule.action(raw_crash, dumps, processed, str(tmp_path), status)

        assert ("mac_crash_info" in processed) == expected

    def test_mac_crash_info_action(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "json_dump": {
                "mac_crash_info": {
                    "num_records": 1,
                    "records": [
                        {"thread": None},
                    ],
                },
            }
        }
        status = Status()

        rule = MacCrashInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["mac_crash_info"] == (
            '{"num_records": 1, "records": [{"thread": null}]}'
        )


class TestMajorVersionRule:
    @pytest.mark.parametrize(
        "version, expected",
        [
            (None, 0),
            ("", 0),
            ("abc", 0),
            ("50", 50),
            ("50.1", 50),
            ("50.1.0", 50),
            ("50.0b4", 50),
        ],
    )
    def test_major_version(self, tmp_path, version, expected):
        raw_crash = {}
        if version is not None:
            raw_crash["Version"] = version
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = MajorVersionRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["major_version"] == expected


class TestBreadcrumbRule:
    def test_basic(self, tmp_path):
        raw_crash = {"Breadcrumbs": json.dumps([{"timestamp": "2021-01-07T16:09:31"}])}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = BreadcrumbsRule(schema=PROCESSED_CRASH_SCHEMA)
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["breadcrumbs"] == [{"timestamp": "2021-01-07T16:09:31"}]

    def test_sentry_style(self, tmp_path):
        raw_crash = {
            "Breadcrumbs": json.dumps(
                {"values": [{"timestamp": "2021-01-07T16:09:31"}]}
            )
        }
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = BreadcrumbsRule(schema=PROCESSED_CRASH_SCHEMA)
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["breadcrumbs"] == [{"timestamp": "2021-01-07T16:09:31"}]

    def test_missing(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = BreadcrumbsRule(schema=PROCESSED_CRASH_SCHEMA)
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash == {}

    def test_malformed(self, tmp_path):
        raw_crash = {"Breadcrumbs": "{}"}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = BreadcrumbsRule(schema=PROCESSED_CRASH_SCHEMA)
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {}
        assert status.notes == ["Breadcrumbs: malformed: {} is not of type 'array'"]


class TestModuleURLRewriteRule:
    @pytest.mark.parametrize(
        "processed, expected",
        [
            # No json_dump.mosules
            ({}, False),
            ({"json_dump": {}}, False),
            # modules is empty
            ({"json_dump": {"modules": []}}, False),
            # modules is non-empty, so the rule can do stuff
            ({"json_dump": {"modules": [{}]}}, True),
        ],
    )
    def test_predicate(self, tmp_path, processed, expected):
        status = Status()

        rule = ModuleURLRewriteRule()
        assert rule.predicate({}, {}, processed, str(tmp_path), status) == expected

    def test_action_no_modules(self, tmp_path):
        processed = {"json_dump": {"modules": []}}
        status = Status()

        # The rule shouldn't change the processed crash at all
        expected = copy.deepcopy(processed)

        rule = ModuleURLRewriteRule()
        rule.act({}, {}, processed, str(tmp_path), status)
        assert processed == expected

    def test_rewrite_no_url(self, tmp_path):
        processed = {
            "json_dump": {
                "modules": [
                    {
                        "base_addr": "0x7ff766020000",
                        "code_id": "604BABCD107000",
                        "debug_file": "firefox.pdb",
                        "debug_id": "3C81DFD6564358244C4C44205044422E1",
                        "end_addr": "0x7ff766127000",
                        "filename": "firefox.exe",
                        "loaded_symbols": True,
                        "symbol_disk_cache_hit": False,
                        "symbol_fetch_time": 52.86800003051758,
                        "version": "88.0.0.7741",
                    },
                ]
            }
        }
        status = Status()

        # The rule shouldn't change the processed crash at all
        expected = copy.deepcopy(processed)

        rule = ModuleURLRewriteRule()
        rule.act({}, {}, processed, str(tmp_path), status)
        assert processed == expected

    @pytest.mark.parametrize(
        "url, expected",
        [
            # localhost urls get removed
            (
                "http://localhost:8000/bucket/v1/firefox.pdb/3C81DFD6564358244C4C44205044422E1/firefox.sym",
                None,
            ),
            # symbols.mozilla.org urls have querystring removed
            (
                "https://symbols.mozilla.org/firefox.pdb/3C81DFD6564358244C4C44205044422E1/firefox.sym?foo=bar",
                "https://symbols.mozilla.org/firefox.pdb/3C81DFD6564358244C4C44205044422E1/firefox.sym",
            ),
            (
                "https://symbols.mozilla.org/try/firefox.pdb/3C81DFD6564358244C4C44205044422E1/firefox.sym?foo=bar",
                "https://symbols.mozilla.org/try/firefox.pdb/3C81DFD6564358244C4C44205044422E1/firefox.sym",
            ),
            # everything else is left alone
            (
                "https://example.com/firefox.pdb/3C81DFD6564358244C4C44205044422E1/firefox.sym?foo=bar",
                "https://example.com/firefox.pdb/3C81DFD6564358244C4C44205044422E1/firefox.sym?foo=bar",
            ),
        ],
    )
    def test_rewrite(self, tmp_path, url, expected):
        processed = {
            "json_dump": {
                "modules": [
                    {
                        "base_addr": "0x7ff766020000",
                        "code_id": "604BABCD107000",
                        "debug_file": "firefox.pdb",
                        "debug_id": "3C81DFD6564358244C4C44205044422E1",
                        "end_addr": "0x7ff766127000",
                        "filename": "firefox.exe",
                        "loaded_symbols": True,
                        "symbol_disk_cache_hit": False,
                        "symbol_fetch_time": 52.86800003051758,
                        "symbol_url": url,
                        "version": "88.0.0.7741",
                    },
                ]
            }
        }
        status = Status()

        rule = ModuleURLRewriteRule()
        rule.act({}, {}, processed, str(tmp_path), status)
        assert processed["json_dump"]["modules"][0]["symbol_url"] == expected


class TestMozCrashReasonRule:
    def test_no_mozcrashreason(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = MozCrashReasonRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash == {}

    def test_good_mozcrashreason(self, tmp_path):
        raw_crash = {"MozCrashReason": "MOZ_CRASH(OOM)"}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = MozCrashReasonRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash == {
            "moz_crash_reason_raw": "MOZ_CRASH(OOM)",
            "moz_crash_reason": "MOZ_CRASH(OOM)",
        }

    @pytest.mark.parametrize(
        "bad_reason",
        [
            "byte index 21548 is not a char boundary",
            (
                'Failed to load module "jar:file..."'
                + "do not use eval with system privileges: jar:file..."
            ),
        ],
    )
    def test_bad_mozcrashreason(self, tmp_path, bad_reason):
        rule = MozCrashReasonRule()

        raw_crash = {"MozCrashReason": bad_reason}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule.action(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash == {
            "moz_crash_reason_raw": bad_reason,
            "moz_crash_reason": "sanitized--see moz_crash_reason_raw",
        }


class TestOutOfMemoryBinaryRule:
    def test_extract_memory_info(self):
        status = Status()

        with mock.patch(
            "socorro.processor.rules.mozilla.gzip.open"
        ) as mocked_gzip_open:
            ret = json.dumps({"mysterious": ["awesome", "memory"]})
            mocked_gzip_open.return_value = BytesIO(ret.encode("utf-8"))
            rule = OutOfMemoryBinaryRule()
            # Stomp on the value to make it easier to test with
            rule.MAX_SIZE_UNCOMPRESSED = 1024
            memory = rule._extract_memory_info("a_pathname", status)
            mocked_gzip_open.assert_called_with("a_pathname", "rb")
            assert memory == {"mysterious": ["awesome", "memory"]}

    def test_extract_memory_info_too_big(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["JavaStackTrace"] = "this is a Java Stack trace"
        dumps = {"memory_report": "a_pathname"}
        processed_crash = {}
        status = Status()

        with mock.patch(
            "socorro.processor.rules.mozilla.gzip.open"
        ) as mocked_gzip_open:
            opened = mock.Mock()
            opened.read.return_value = json.dumps({"some": "notveryshortpieceofjson"})

            def gzip_open(filename, mode):
                assert mode == "rb"
                return opened

            mocked_gzip_open.side_effect = gzip_open
            rule = OutOfMemoryBinaryRule()

            # Stomp on the value to make it easier to test with
            rule.MAX_SIZE_UNCOMPRESSED = 5

            memory = rule._extract_memory_info("a_pathname", status)
            expected_error_message = (
                "Uncompressed memory info too large 35 "
                + f"(max: {rule.MAX_SIZE_UNCOMPRESSED})"
            )
            assert memory == {"ERROR": expected_error_message}
            assert status.notes == [expected_error_message]
            opened.close.assert_called_with()

            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
            assert "memory_report" not in processed_crash
            assert processed_crash["memory_report_error"] == expected_error_message

    def test_extract_memory_info_with_trouble(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["JavaStackTrace"] = "this is a Java Stack trace"
        dumps = {"memory_report": "a_pathname"}
        processed_crash = {}
        status = Status()

        with mock.patch(
            "socorro.processor.rules.mozilla.gzip.open"
        ) as mocked_gzip_open:
            mocked_gzip_open.side_effect = IOError
            rule = OutOfMemoryBinaryRule()

            memory = rule._extract_memory_info("a_pathname", status)
            assert memory["ERROR"] == "error in gzip for a_pathname: OSError()"
            assert status.notes == ["error in gzip for a_pathname: OSError()"]

            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
            assert "memory_report" not in processed_crash
            assert (
                processed_crash["memory_report_error"]
                == "error in gzip for a_pathname: OSError()"
            )

    def test_extract_memory_info_with_json_trouble(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["JavaStackTrace"] = "this is a Java Stack trace"
        dumps = {"memory_report": "a_pathname"}
        processed_crash = {}
        status = Status()

        with mock.patch(
            "socorro.processor.rules.mozilla.gzip.open"
        ) as mocked_gzip_open:
            with mock.patch(
                "socorro.processor.rules.mozilla.json.loads"
            ) as mocked_json_loads:
                mocked_json_loads.side_effect = ValueError

                rule = OutOfMemoryBinaryRule()
                memory = rule._extract_memory_info("a_pathname", status)
                mocked_gzip_open.assert_called_with("a_pathname", "rb")
                assert memory == {"ERROR": "error in json for a_pathname: ValueError()"}
                assert status.notes == ["error in json for a_pathname: ValueError()"]
                mocked_gzip_open.return_value.close.assert_called_with()

                rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
                assert "memory_report" not in processed_crash
                expected = "error in json for a_pathname: ValueError()"
                assert processed_crash["memory_report_error"] == expected

    def test_everything_we_hoped_for(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["JavaStackTrace"] = "this is a Java Stack trace"
        dumps = {"memory_report": str(tmp_path / "a_pathname")}
        processed_crash = {}
        status = Status()

        class MyOutOfMemoryBinaryRule(OutOfMemoryBinaryRule):
            @staticmethod
            def _extract_memory_info(dump_pathname, status):
                assert dump_pathname == dumps["memory_report"]
                assert status.notes == []
                return "mysterious-awesome-memory"

        rule = MyOutOfMemoryBinaryRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["memory_report"] == "mysterious-awesome-memory"

    def test_this_is_not_the_crash_you_are_looking_for(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["JavaStackTrace"] = "this is a Java Stack trace"
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = OutOfMemoryBinaryRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "memory_report" not in processed_crash


class TestFenixVersionRewriteRule:
    @pytest.mark.parametrize(
        "product, version, expected",
        [
            # Change this
            ("Fenix", "Nightly 200312 12:12", True),
            # Don't change these
            ("Fenix", "1.0", False),
            ("Firefox", "75.0", False),
            ("Firefox", "Nightly 75.0", False),
        ],
    )
    def test_predicate(self, tmp_path, product, version, expected):
        raw_crash = {
            "ProductName": product,
            "Version": version,
        }
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = FenixVersionRewriteRule()
        ret = rule.predicate(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert ret == expected

    def test_act(self, tmp_path):
        raw_crash = {
            "ProductName": "Fenix",
            "Version": "Nightly 200315 05:05",
        }
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = FenixVersionRewriteRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert raw_crash["Version"] == "0.0a1"
        assert status.notes == ["Changed version from 'Nightly 200315 05:05' to 0.0a1"]


class TestESRVersionRewrite:
    def test_everything_we_hoped_for(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["ReleaseChannel"] = "esr"
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = ESRVersionRewrite()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert raw_crash["Version"] == "12.0esr"

        # processed_crash should be unchanged
        assert processed_crash == {}

    def test_this_is_not_the_crash_you_are_looking_for(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["ReleaseChannel"] = "not_esr"
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = ESRVersionRewrite()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert raw_crash["Version"] == "12.0"

        # processed_crash should be unchanged
        assert processed_crash == {}

    def test_this_is_really_broken(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        raw_crash["ReleaseChannel"] = "esr"
        del raw_crash["Version"]
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = ESRVersionRewrite()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "Version" not in raw_crash
        assert status.notes == ['"Version" missing from esr release raw_crash']

        # processed_crash should be unchanged
        assert processed_crash == {}


class TestTopMostFilesRule:
    def test_file_in_frame(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "crashing_thread": 0,
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {"function": "<unknown>"},
                            {"file": "MozPromise.h", "function": "MozPromise"},
                        ]
                    }
                ],
            },
        }
        status = Status()

        rule = TopMostFilesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["topmost_filenames"] == "MozPromise.h"

    def test_file_in_inlines(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "crashing_thread": 0,
            "json_dump": {
                "threads": [
                    {
                        "frames": [
                            {"function": "<unknown>"},
                            {
                                "file": "MozPromise.h",
                                "inlines": [
                                    {
                                        "file": "RTCRtpTransceiver.cpp",
                                        "function": "RTCRtpTransceiver",
                                    },
                                ],
                                "function": "MozPromise",
                            },
                        ],
                    },
                ],
            },
        }
        status = Status()

        rule = TopMostFilesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["topmost_filenames"] == "RTCRtpTransceiver.cpp"

    def test_missing_json_dump(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = TopMostFilesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "topmost_filenames" not in processed_crash

    def test_missing_crashing_thread(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {
            "json_dump": {
                "crash_info": {"crashing_thread": 0},
                "crashing_thread": {
                    "frames": [
                        {"source": "not-the-right-file.dll"},
                        {"file": "not-the-right-file.cpp"},
                    ]
                },
                "threads": [
                    {
                        "frames": [
                            {"function": "<unknown>"},
                            {"file": "MozPromise.h", "function": "MozPromise"},
                        ]
                    }
                ],
            }
        }
        status = Status()

        rule = TopMostFilesRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "topmost_filenames" not in processed_crash


class TestMissingSymbolsRule:
    def test_basic(self, tmp_path, debug_id_helper):
        raw_crash = {}
        dumps = {}
        debug_id_1 = debug_id_helper.generate()
        debug_id_2 = debug_id_helper.generate()
        debug_id_3 = debug_id_helper.generate()
        debug_id_4 = debug_id_helper.generate()
        processed_crash = {
            "json_dump": {
                "modules": [
                    {
                        "filename": "libxul.dll",
                        "version": None,
                        "debug_id": debug_id_1,
                        "missing_symbols": True,
                    },
                    {
                        "filename": "libnss3.dll",
                        "version": "1.0",
                        "debug_id": debug_id_2,
                        "missing_symbols": True,
                    },
                    {
                        "filename": "mozglue.dll",
                        "debug_id": debug_id_3,
                        "missing_symbols": None,
                    },
                    {
                        "filename": "somethingmozglue.dll",
                        "debug_id": debug_id_4,
                        "missing_symbols": False,
                    },
                ],
            },
        }
        status = Status()

        rule = MissingSymbolsRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert (
            processed_crash["missing_symbols"]
            == f"libnss3.dll/1.0/{debug_id_2};libxul.dll/None/{debug_id_1}"
        )

    @pytest.mark.parametrize(
        "processed_crash",
        [
            {},
            {"modules": None},
            {"modules": []},
            {"modules": [{}]},
            {"modules": [{"missing_symbols": True}]},
            {"modules": [{"filename": "libxul.dll"}]},
            {"modules": [{"filename": "libxul.dll", "version": "1.0"}]},
        ],
    )
    def test_missing_things(self, tmp_path, processed_crash):
        status = Status()
        rule = MissingSymbolsRule()

        rule.act({}, {}, processed_crash, str(tmp_path), status)
        assert "missing_symbols" not in processed_crash

    @pytest.mark.parametrize(
        "item, expected",
        [
            (
                {"filename": "libxul.so", "missing_symbols": True},
                "libxul.so/None/" + MissingSymbolsRule.NULL_DEBUG_ID,
            ),
            (
                {
                    "filename": "libxul_2.dll",
                    "version": "1.0",
                    "debug_id": "51C36FAFFD214DB4A0D91D93B38336CEA",
                    "missing_symbols": True,
                },
                "libxul_2.dll/1.0/51C36FAFFD214DB4A0D91D93B38336CEA",
            ),
            # With a code id
            (
                {
                    "filename": "ntdll.dll",
                    "version": "10.0.14393.6343",
                    "debug_id": "0879DB9512094636AA777326F6A5C01E1",
                    "code_id": "6502749b182000",
                    "missing_symbols": True,
                },
                "ntdll.dll/10.0.14393.6343/0879DB9512094636AA777326F6A5C01E1/6502749b182000",
            ),
            # Clean up fields
            (
                {
                    "filename": " l\nib (foo)",
                    "version": "1.0/5",
                    "debug_id": "this is bad",
                    "code_id": "ou812",
                    "missing_symbols": True,
                },
                "libfoo/1.0\\/5/bad/812",
            ),
        ],
    )
    def test_format_module(self, item, expected):
        rule = MissingSymbolsRule()
        assert rule.format_module(item) == expected


class TestModulesInStackRule:
    def test_basic(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "crashing_thread": 0,
            "json_dump": {
                "modules": [
                    {"filename": "libxul.dll", "debug_id": "ABCDEF"},
                    {"filename": "libnss3.dll", "debug_id": "012345"},
                    {"filename": "mozglue.dll", "debug_id": "ABC345"},
                ],
                "crash_info": {"crashing_thread": 0},
                "threads": [
                    {"frames": [{"module": "libxul.dll"}, {"module": "mozglue.dll"}]}
                ],
            },
        }
        status = Status()

        rule = ModulesInStackRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert (
            processed_crash["modules_in_stack"]
            == "libxul.dll/ABCDEF;mozglue.dll/ABC345"
        )

    @pytest.mark.parametrize(
        "processed_crash",
        [
            {"crashing_thread": None},
            {"crashing_thread": None, "json_dump": {}},
            {"crashing_thread": None, "json_dump": {"crash_info": {}}},
            {"crashing_thread": 0, "json_dump": {"crash_info": {"crashing_thread": 0}}},
            {
                "crashing_thread": 10,
                "json_dump": {"crash_info": {"crashing_thread": 10}, "threads": []},
            },
            {
                "crashing_thread": 0,
                "json_dump": {"crash_info": {"crashing_thread": 0}, "threads": [{}]},
            },
            {
                "crashing_thread": 0,
                "json_dump": {
                    "crash_info": {"crashing_thread": 0},
                    "threads": [{"frames": []}],
                },
            },
            {
                "crashing_thread": 0,
                "modules": [],
                "json_dump": {
                    "crash_info": {"crashing_thread": 0},
                    "threads": [{"frames": [{"module": "libxul.so"}]}],
                },
            },
        ],
    )
    def test_missing_things(self, tmp_path, processed_crash):
        status = Status()
        rule = ModulesInStackRule()

        rule.act({}, {}, processed_crash, str(tmp_path), status)
        assert "modules_in_stack" not in processed_crash

    @pytest.mark.parametrize(
        "item, expected",
        [
            ({}, "/"),
            ({"filename": "libxul.so"}, "libxul.so/"),
            ({"debug_id": "ABCDEF"}, "/ABCDEF"),
            ({"filename": "libxul.so", "debug_id": "ABCDEF"}, "libxul.so/ABCDEF"),
            (
                {"filename": "libxul_2.dll", "debug_id": "ABCDEF0123456789"},
                "libxul_2.dll/ABCDEF0123456789",
            ),
            ({"filename": " l\nib (foo)", "debug_id": "this is bad"}, "libfoo/bad"),
        ],
    )
    def test_format_module(self, item, expected):
        rule = ModulesInStackRule()
        assert rule.format_module(item) == expected


class TestBetaVersionRule:
    API_URL = "http://example.com/api/VersionString"

    def build_rule(self):
        return BetaVersionRule(version_string_api=self.API_URL)

    @pytest.mark.parametrize(
        "product, channel, expected",
        [
            ("Firefox", "beta", True),
            # Unsupported products and channels yield false
            ("Firefox", "nightly", False),
            ("Fenix", "beta", False),
        ],
    )
    def test_predicate(self, tmp_path, product, channel, expected):
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "product": product,
            "release_channel": channel,
            "version": "3.0",
            "build": "20001001101010",
        }
        status = Status()

        rule = self.build_rule()
        assert (
            rule.predicate(raw_crash, dumps, processed_crash, str(tmp_path), status)
            == expected
        )

    def test_beta_channel_known_version(self, tmp_path):
        # Beta channel with known version gets converted correctly
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "product": "Firefox",
            "release_channel": "beta",
            "version": "3.0",
            "build": "20001001101010",
        }
        status = Status()

        rule = self.build_rule()
        with requests_mock.Mocker() as req_mock:
            req_mock.get(
                self.API_URL + "?product=Firefox&channel=beta&build_id=20001001101010",
                json={"hits": [{"version_string": "3.0b1"}], "total": 1},
            )
            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["version"] == "3.0b1"
        assert status.notes == []

    def test_release_channel(self, tmp_path):
        """Release channel doesn't trigger rule"""
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "product": "Firefox",
            "version": "2.0",
            "release_channel": "release",
            "build": "20000801101010",
        }
        status = Status()

        rule = self.build_rule()
        with requests_mock.Mocker():
            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["version"] == "2.0"
        assert status.notes == []

    def test_nightly_channel(self, tmp_path):
        """Nightly channel doesn't trigger rule"""
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "product": "Firefox",
            "version": "5.0a1",
            "release_channel": "nightly",
            "build": "20000105101010",
        }
        status = Status()

        rule = self.build_rule()
        with requests_mock.Mocker():
            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["version"] == "5.0a1"
        assert status.notes == []

    def test_bad_buildid(self, tmp_path):
        """Invalid buildids don't cause errors"""
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "product": "Firefox",
            "release_channel": "beta",
            "version": "5.0",
            "build": '2",381,,"',
        }
        status = Status()

        rule = self.build_rule()
        with requests_mock.Mocker() as req_mock:
            # NOTE(willkg): Is it possible to validate the buildid and
            # reject it without doing an HTTP round-trip?
            req_mock.get(
                self.API_URL + '?product=Firefox&channel=beta&build_id=2",381,,"',
                json={"hits": [], "total": 0},
            )
            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["version"] == "5.0b0"
        assert status.notes == [
            "release channel is beta but no version data was found - "
            'added "b0" suffix to version number'
        ]

    def test_beta_channel_unknown_version(self, tmp_path):
        """Beta crash that Socorro doesn't know about gets b0"""
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "product": "Firefox",
            "version": "3.0.1",
            "release_channel": "beta",
            "build": "220000101101011",
        }
        status = Status()

        rule = self.build_rule()
        with requests_mock.Mocker() as req_mock:
            req_mock.get(
                self.API_URL + "?product=Firefox&channel=beta&build_id=220000101101011",
                json={"hits": [], "total": 0},
            )
            rule.action(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["version"] == "3.0.1b0"
        assert status.notes == [
            "release channel is beta but no version data was found - "
            + 'added "b0" suffix to version number'
        ]

    def test_aurora_channel(self, tmp_path):
        """Test aurora channel lookup"""
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "product": "Firefox",
            "version": "3.0",
            "release_channel": "aurora",
            "build": "20001001101010",
        }
        status = Status()

        rule = self.build_rule()
        with requests_mock.Mocker() as req_mock:
            req_mock.get(
                self.API_URL
                + "?product=Firefox&channel=aurora&build_id=20001001101010",
                json={"hits": [{"version_string": "3.0b1"}], "total": 0},
            )
            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["version"] == "3.0b1"
        assert status.notes == []


class TestOsPrettyName:
    @pytest.mark.parametrize(
        "os_name, os_version, expected",
        [
            # Known windows versions
            ("Windows NT", "6.1.7601 Service Pack 2", "Windows 7"),
            ("Windows NT", "6.3.9600 Service Pack 1", "Windows 8.1"),
            ("Windows NT", "10.0.17758", "Windows 10"),
            ("Windows NT", "10.0.21996", "Windows 11"),
            # Unknown windows version
            ("Windows NT", "15.2", "Windows Unknown"),
            # A valid version of Mac OS X
            ("Mac OS X", "10.18.324", "OS X 10.18"),
            # An invalid version of Mac OS X
            ("Mac OS X", "9.1", "OS X Unknown"),
            # Mac OS >= 11
            ("Mac OS X", "11.2.1 20D74", "macOS 11"),
            # Generic Linux
            ("Linux", "0.0.12.13", "Linux"),
            # Linux with - in version
            ("Linux", "5.17-0.1 #2 SMP PREEMPT", "Linux"),
            # Linux with - in version
            ("Linux", "3.14-2-686-pae #1 SMP Debian 3.14.15-2", "Linux"),
            # Android versions
            ("Android", None, "Android"),
            ("Android", "23", "Android 23"),
        ],
    )
    def test_everything_we_hoped_for(self, tmp_path, os_name, os_version, expected):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {"os_name": os_name, "os_version": os_version}
        status = Status()

        rule = OSPrettyVersionRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["os_pretty_version"] == expected

    def test_lsb_release(self, tmp_path):
        # If this is Linux and there's data in json_dump.lsb_release.description,
        # use that
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {
            "os_name": "Linux",
            "os_version": "0.0.0 Linux etc",
            "json_dump": {"lsb_release": {"description": "Ubuntu 18.04 LTS"}},
        }
        status = Status()

        rule = OSPrettyVersionRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["os_pretty_version"] == "Ubuntu 18.04 LTS"

    @pytest.mark.parametrize(
        "os_name, os_version, expected",
        [
            ("Linux", None, "Linux"),
            (None, None, None),
            ("Windows NT", "NaN", "Windows NT"),
            ("Linux", "5.abc", "Linux"),
            ("Linux", "5.", "Linux"),
            ("Linux", "5", "Linux"),
        ],
    )
    def test_junk_data(self, tmp_path, os_name, os_version, expected):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        # Now try some bogus processed_crashes.
        processed_crash = {}
        if os_name is not None:
            processed_crash["os_name"] = os_name
        if os_version is not None:
            processed_crash["os_version"] = os_version
        status = Status()

        rule = OSPrettyVersionRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["os_pretty_version"] == expected

    def test_none(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {"os_name": None, "os_version": None}
        status = Status()

        rule = OSPrettyVersionRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["os_pretty_version"] is None


class TestThemePrettyNameRule:
    def test_everything_we_hoped_for(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {}
        processed_crash["addons"] = [
            "adblockpopups@jessehakanen.net:0.3",
            "dmpluginff@westbyte.com:1,4.8",
            "firebug@software.joehewitt.com:1.9.1",
            "killjasmin@pierros14.com:2.4",
            "support@surfanonymous-free.com:1.0",
            "uploader@adblockfilters.mozdev.org:2.1",
            "{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}:20111107",
            "{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}:2.0.3",
            "anttoolbar@ant.com:2.4.6.4",
            "{972ce4c6-7e08-4474-a285-3208198ce6fd}:12.0",
            "elemhidehelper@adblockplus.org:1.2.1",
        ]
        status = Status()

        rule = ThemePrettyNameRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        # the raw crash & dumps should not have changed
        assert raw_crash == canonical_standard_raw_crash
        assert dumps == {}

        expected_addon_list = [
            "adblockpopups@jessehakanen.net:0.3",
            "dmpluginff@westbyte.com:1,4.8",
            "firebug@software.joehewitt.com:1.9.1",
            "killjasmin@pierros14.com:2.4",
            "support@surfanonymous-free.com:1.0",
            "uploader@adblockfilters.mozdev.org:2.1",
            "{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}:20111107",
            "{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}:2.0.3",
            "anttoolbar@ant.com:2.4.6.4",
            "{972ce4c6-7e08-4474-a285-3208198ce6fd} (default theme):12.0",
            "elemhidehelper@adblockplus.org:1.2.1",
        ]
        assert processed_crash["addons"] == expected_addon_list

    def test_missing_key(self, tmp_path):
        processed_crash = {}
        status = Status()

        rule = ThemePrettyNameRule()

        # Test with missing key.
        res = rule.predicate({}, {}, processed_crash, str(tmp_path), status)
        assert res is False

        # Test with empty list.
        processed_crash["addons"] = []
        res = rule.predicate({}, {}, processed_crash, str(tmp_path), status)
        assert res is False

        # Test with key missing from list.
        processed_crash["addons"] = [
            "adblockpopups@jessehakanen.net:0.3",
            "dmpluginff@westbyte.com:1,4.8",
        ]
        res = rule.predicate({}, {}, processed_crash, str(tmp_path), status)
        assert res is False

    def test_with_malformed_addons_field(self, tmp_path):
        processed_crash = {}
        processed_crash["addons"] = [
            "addon_with_no_version",
            "{972ce4c6-7e08-4474-a285-3208198ce6fd}",
            "elemhidehelper@adblockplus.org:1.2.1",
        ]
        status = Status()

        rule = ThemePrettyNameRule()
        rule.act({}, {}, processed_crash, str(tmp_path), status)
        expected_addon_list = [
            "addon_with_no_version",
            "{972ce4c6-7e08-4474-a285-3208198ce6fd} (default theme)",
            "elemhidehelper@adblockplus.org:1.2.1",
        ]
        assert processed_crash["addons"] == expected_addon_list


class TestSignatureGeneratorRule:
    def test_signature(self, tmp_path):
        rule = SignatureGeneratorRule()
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        processed_crash = {
            "json_dump": {
                "crash_info": {"crashing_thread": 0},
                "crashing_thread": 0,
                "threads": [
                    {
                        "frames": [
                            {
                                "frame": 0,
                                "function": "Alpha<Bravo<Charlie>, Delta>::Echo<Foxtrot>",
                                "file": "foo.cpp",
                            },
                            {
                                "frame": 1,
                                "function": "std::something::something",
                                "file": "foo.rs",
                            },
                        ]
                    }
                ],
            }
        }
        status = Status()

        rule.action(raw_crash, {}, processed_crash, str(tmp_path), status)
        assert processed_crash["signature"] == "Alpha<T>::Echo<T>"
        assert (
            processed_crash["proto_signature"]
            == "Alpha<T>::Echo<T> | std::something::something"
        )
        assert status.notes == []

    def test_empty_raw_and_processed_crashes(self, tmp_path):
        rule = SignatureGeneratorRule()
        raw_crash = {}
        processed_crash = {}
        status = Status()

        rule.action(raw_crash, {}, processed_crash, str(tmp_path), status)

        # NOTE(willkg): This is what the current pipeline yields. If any of
        # those parts change, this might change, too. The point of this test is
        # that we can pass in empty dicts and the SignatureGeneratorRule and
        # the generation rules in the default pipeline don't fall over.
        assert processed_crash["signature"] == "EMPTY: no frame data available"
        assert "proto_signature" not in processed_crash
        assert status.notes == [
            "SignatureGenerationRule: CSignatureTool: no frame data for crashing thread (0)"
        ]

    def test_rule_fail_and_capture_error(self, tmp_path, sentry_helper):
        exc_value = Exception("Cough")

        class BadRule:
            def predicate(self, raw_crash, processed_crash):
                raise exc_value

        rule = SignatureGeneratorRule()

        # NOTE(willkg): this just verifies we captured an exception with Sentry--it
        # doesn't configure Sentry the way the processor does so we shouldn't test
        # whether things are scrubbed correctly
        with sentry_helper.init() as sentry_client:
            # Override the regular SigntureGenerator with one with a BadRule
            # in the pipeline
            rule.generator = SignatureGenerator(
                ruleset=[BadRule], error_handler=rule._error_handler
            )

            raw_crash = {}
            processed_crash = {}
            status = Status()

            rule.action(raw_crash, {}, processed_crash, str(tmp_path), status)

            # NOTE(willkg): The signature is an empty string because there are no
            # working rules that add anything to it.
            assert processed_crash["signature"] == ""
            assert "proto_signature" not in processed_crash
            assert status.notes == ["BadRule: Rule failed: Cough"]

            (event,) = sentry_client.envelope_payloads
            # NOTE(willkg): Some of the extra bits come from the processor app and since
            # we're testing SignatureGenerator in isolation, those don't get added to
            # the sentry scope
            assert event["extra"] == {"signature_rule": "BadRule", "sys.argv": mock.ANY}
            assert event["exception"]["values"][0]["type"] == "Exception"


class TestPHCRule:
    def test_predicate(self, tmp_path):
        rule = PHCRule()
        assert rule.predicate({}, {}, {}, str(tmp_path), Status()) is False

    @pytest.mark.parametrize(
        "base_address, expected",
        [(None, None), ("", None), ("foo", None), ("10", "0xa"), ("100", "0x64")],
    )
    def test_phc_base_address(self, tmp_path, base_address, expected):
        raw_crash = {"PHCKind": "FreedPage"}
        if base_address is not None:
            raw_crash["PHCBaseAddress"] = base_address

        rule = PHCRule()
        processed_crash = {}
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        if expected is None:
            assert "phc_base_address" not in processed_crash
        else:
            assert processed_crash["phc_base_address"] == expected

    @pytest.mark.parametrize(
        "usable_size, expected", [(None, None), ("", None), ("foo", None), ("10", 10)]
    )
    def test_phc_usable_size(self, tmp_path, usable_size, expected):
        raw_crash = {"PHCKind": "FreedPage"}
        if usable_size is not None:
            raw_crash["PHCUsableSize"] = usable_size

        rule = PHCRule()
        processed_crash = {}
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        if expected is None:
            assert "phc_usable_size" not in processed_crash
        else:
            assert processed_crash["phc_usable_size"] == expected

    def test_copied_values(self, tmp_path):
        raw_crash = {
            "PHCKind": "FreedPage",
            "PHCUsableSize": "8",
            "PHCBaseAddress": "10",
            "PHCAllocStack": "100,200",
            "PHCFreeStack": "300,400",
        }
        rule = PHCRule()
        processed_crash = {}
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash == {
            "phc_kind": "FreedPage",
            "phc_usable_size": 8,
            "phc_base_address": "0xa",
            "phc_alloc_stack": "100,200",
            "phc_free_stack": "300,400",
        }


class TestDistributionIdRule:
    def test_no_annotation_and_no_telemetry(self, tmp_path):
        raw_crash = {}
        processed_crash = {}
        rule = DistributionIdRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["distribution_id"] == "unknown"

    def test_annotation(self, tmp_path):
        raw_crash = {"DistributionID": "mint"}
        processed_crash = {}
        rule = DistributionIdRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["distribution_id"] == "mint"

    @pytest.mark.parametrize(
        "telemetry_value",
        [
            # Invalid JSON
            "null",
            "foo{",
            # Valid JSON, but missing value
            "{}",
            '{"partner": {}}',
        ],
    )
    def test_telemetry_values_unknown(self, tmp_path, telemetry_value):
        raw_crash = {"TelemetryEnvironment": telemetry_value}
        processed_crash = {}

        rule = DistributionIdRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["distribution_id"] == "unknown"

    def test_telemetry_value_mozilla(self, tmp_path):
        raw_crash = {"TelemetryEnvironment": '{"partner": {"distributionId": null}}'}
        processed_crash = {}

        rule = DistributionIdRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["distribution_id"] == "mozilla"

    def test_telemetry_value_mint(self, tmp_path):
        raw_crash = {"TelemetryEnvironment": '{"partner": {"distributionId": "mint"}}'}
        processed_crash = {}

        rule = DistributionIdRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["distribution_id"] == "mint"


class TestUtilityActorsNameRule:
    def test_no_data(self, tmp_path):
        raw_crash = {}
        processed_crash = {}

        rule = UtilityActorsNameRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash == {}

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("", []),
            ("abc", ["abc"]),
            ("abc,def", ["abc", "def"]),
            ("abc,,def", ["abc", "def"]),
            ("  abc, def", ["abc", "def"]),
        ],
    )
    def test_data(self, tmp_path, value, expected):
        raw_crash = {
            "UtilityActorsName": value,
        }
        processed_crash = {}

        rule = UtilityActorsNameRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["utility_actors_name"] == expected


class TestReportTypeRule:
    def test_crash(self, tmp_path):
        raw_crash = {}
        processed_crash = {}

        rule = ReportTypeRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash == {"report_type": "crash"}

    def test_ipc_channel_error_is_hang(self, tmp_path):
        raw_crash = {}
        processed_crash = {"ipc_channel_error": "ShutDownKill"}

        rule = ReportTypeRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["report_type"] == "hang"

    def test_async_shutdown_timeout_is_hang(self, tmp_path):
        raw_crash = {}
        processed_crash = {
            "async_shutdown_timeout": (
                '{"phase":"AddonManager: Waiting to start provider shutdown.",'
                + '"conditions":[{"name":"EnvironmentAddonBuilder",'
                + '"state":"Awaiting AddonManagerPrivate.databaseReady",'
                + '"filename":"resource://gre/modules/TelemetryEnvironment.sys.mjs",'
                + '"lineNumber":603,"stack":['
                + '"resource://gre/modules/TelemetryEnvironment.sys.mjs:init:603",'
                + '"resource://gre/modules/TelemetryEnvironment.sys.mjs:EnvironmentCache:974",'
                + '"resource://gre/modules/TelemetryEnvironment.sys.mjs:getGlobal:79",'
                + '"resource://gre/modules/TelemetryEnvironment.sys.mjs:getcurrentEnvironment:86",'
                + '"resource://gre/modules/TelemetryStartup.sys.mjs:annotateEnvironment:39",'
                + '"resource://gre/modules/TelemetryStartup.sys.mjs:TelemetryStartup.prototype.observe:28"]}]}'
            )
        }

        rule = ReportTypeRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["report_type"] == "hang"

    @pytest.mark.parametrize(
        "json_dump, expected",
        [
            (None, "crash"),
            ({"crash_info": None}, "crash"),
            ({"crash_info": {"crashing_thread": None}}, "crash"),
            ({"crash_info": {"crashing_thread": "jim"}}, "crash"),
            ({"crash_info": {"crashing_thread": 10}}, "crash"),
            ({"crash_info": {"crashing_thread": 0}, "threads": None}, "crash"),
            ({"crash_info": {"crashing_thread": 0}, "threads": []}, "crash"),
            ({"crash_info": {"crashing_thread": 0}, "threads": [{}]}, "crash"),
            (
                {"crash_info": {"crashing_thread": 0}, "threads": [{"frames": [{}]}]},
                "crash",
            ),
            (
                {
                    "crash_info": {"crashing_thread": 0},
                    "threads": [{"frames": [{"function": None}]}],
                },
                "crash",
            ),
            (
                {
                    "crash_info": {"crashing_thread": 0},
                    "threads": [
                        {
                            "frames": [
                                {
                                    "function": "mozilla::(anonymous namespace)::RunWatchdog(void*)"
                                }
                            ]
                        }
                    ],
                },
                "hang",
            ),
        ],
    )
    def test_shutdownhang(self, tmp_path, json_dump, expected):
        raw_crash = {}
        processed_crash = {}
        if json_dump is not None:
            processed_crash["json_dump"] = json_dump

        rule = ReportTypeRule()
        rule.action(raw_crash, {}, processed_crash, str(tmp_path), Status())
        assert processed_crash["report_type"] == expected

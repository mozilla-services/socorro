# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
import pytest

from socorro.processor.rules.general import (
    CPUInfoRule,
    CollectorInfoRule,
    CrashReportKeysRule,
    DeNoneRule,
    DeNullRule,
    IdentifierRule,
    OSInfoRule,
)
from socorro.unittest.processor import get_basic_processor_meta


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
        "system_info": {
            "os_ver": "6.1.7601 Service Pack 1 ",
            "cpu_count": 4,
            "cpu_info": "GenuineIntel family 6 model 42 stepping 7",
            "cpu_arch": "x86",
            "os": "Windows NT",
        }
    }
}


class TestDeNoneRule:
    @pytest.mark.parametrize(
        "raw_crash, expected",
        [
            ({}, {}),
            ({"foo": "bar"}, {"foo": "bar"}),
            ({"foo": None}, {}),
            ({"foo": "bar", "baz": None}, {"foo": "bar"}),
        ],
    )
    def test_denone(self, raw_crash, expected):
        rule = DeNoneRule()
        rule.action(raw_crash, None, {}, {})
        assert raw_crash == expected

    def test_denone_with_dotdict(self):
        # We want to explicitly test with DotDict since it might have different deletion
        # things
        raw_crash = DotDict({"foo": "bar", "baz": None})
        expected = DotDict({"foo": "bar"})

        rule = DeNoneRule()
        rule.action(raw_crash, None, {}, {})
        assert raw_crash == expected


class TestDeNullRule:
    @pytest.mark.parametrize(
        "data, expected",
        [
            # no nulls--just making sure things are good
            ("abc", "abc"),
            (b"abc", b"abc"),
            (123, 123),
            # has nulls
            ("abc\u0000", "abc"),
            ("abc\0", "abc"),
            ("ab\0c\0", "abc"),
            (b"abc\0", b"abc"),
            (b"a\0bc\0", b"abc"),
        ],
    )
    def test_de_null(self, data, expected):
        rule = DeNullRule()
        assert rule.de_null(data) == expected

    def test_rule_with_dict(self):
        raw_crash = {"key1": "val1", b"\0key2": b"val2\0", "\0key3": "\0val3"}

        rule = DeNullRule()
        rule.act(raw_crash, {}, {}, get_basic_processor_meta())

        assert raw_crash == {"key1": "val1", b"key2": b"val2", "key3": "val3"}

    def test_rule_with_dotdict(self):
        # NOTE(willkg): DotDict doesn't like bytes keys
        raw_crash = DotDict({"key1": "val1", "\0key2": b"val2\0", "\0key3": "\0val3"})

        rule = DeNullRule()
        rule.act(raw_crash, {}, {}, get_basic_processor_meta())

        assert raw_crash == DotDict({"key1": "val1", "key2": b"val2", "key3": "val3"})


class TestIdentifierRule:
    def test_everything_we_hoped_for(self):
        uuid = "00000000-0000-0000-0000-000002140504"
        raw_crash = {"uuid": uuid}
        dumps = {}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        rule = IdentifierRule()
        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert processed_crash["crash_id"] == uuid
        assert processed_crash["uuid"] == uuid

    def test_uuid_missing(self):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        rule = IdentifierRule()
        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        # raw crash and processed crashes should be unchanged
        assert raw_crash == {}
        assert processed_crash == {}


class TestCPUInfoRule:
    def test_cpu_count(self):
        raw_crash = {}
        dumps = {}
        processor_meta = get_basic_processor_meta()

        rule = CPUInfoRule()

        processed_crash = {"json_dump": {"system_info": {"cpu_count": 4}}}
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash["cpu_count"] == 4

    def test_cpu_count_no_json_dump(self):
        raw_crash = {}
        dumps = {}
        processor_meta = get_basic_processor_meta()

        rule = CPUInfoRule()

        processed_crash = {}
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash["cpu_count"] == 0

    def test_cpu_info(self):
        raw_crash = {}
        dumps = {}
        processor_meta = get_basic_processor_meta()

        rule = CPUInfoRule()

        processed_crash = {
            "json_dump": {
                "system_info": {
                    "cpu_info": "GenuineIntel family 6 model 42 stepping 7",
                }
            }
        }
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert (
            processed_crash["cpu_info"] == "GenuineIntel family 6 model 42 stepping 7"
        )

    def test_cpu_info_no_json_dump(self):
        raw_crash = {}
        dumps = {}
        processor_meta = get_basic_processor_meta()

        rule = CPUInfoRule()

        processed_crash = {}
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash["cpu_info"] == "unknown"

    def test_cpu_arch_no_json_dump(self):
        raw_crash = {}
        dumps = {}
        processor_meta = get_basic_processor_meta()

        rule = CPUInfoRule()

        # If there's no information, then it should be "unknown"
        processed_crash = {}
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash["cpu_arch"] == "unknown"

    def test_cpu_arch_from_json_dump(self):
        raw_crash = {}
        dumps = {}
        processor_meta = get_basic_processor_meta()

        rule = CPUInfoRule()

        # If it's in the minidump-stackwalk output, use that
        processed_crash = {"json_dump": {"system_info": {"cpu_arch": "x86"}}}
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash["cpu_arch"] == "x86"

    @pytest.mark.parametrize(
        "android_cpu_abi, expected",
        [
            ("x86", "x86"),
            ("arm64-v8a", "arm64"),
            ("x86_64", "amd64"),
            ("value not in map", "value not in map"),
        ],
    )
    def test_cpu_arch_from_android_cpu_abi(self, android_cpu_abi, expected):
        raw_crash = {"Android_CPU_ABI": android_cpu_abi}
        processed_crash = {}
        dumps = {}
        processor_meta = get_basic_processor_meta()

        rule = CPUInfoRule()
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash["cpu_arch"] == expected


class TestOSInfoRule:
    def test_everything_we_hoped_for(self):
        raw_crash = {}
        processed_crash = {
            "json_dump": {
                "system_info": {
                    "os": "Windows NT",
                    "os_ver": "6.1.7601 Service Pack 1",
                }
            }
        }
        processor_meta = get_basic_processor_meta()

        rule = OSInfoRule()

        # the call to be tested
        rule.act(raw_crash, {}, processed_crash, processor_meta)

        assert processed_crash["os_name"] == "Windows NT"
        assert processed_crash["os_version"] == "6.1.7601 Service Pack 1"

        # raw crash should be unchanged
        assert raw_crash == {}

    def test_stuff_missing(self):
        raw_crash = {}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        rule = OSInfoRule()

        # the call to be tested
        rule.act(raw_crash, {}, processed_crash, processor_meta)

        # processed crash should have empties
        assert processed_crash["os_name"] == "Unknown"
        assert processed_crash["os_version"] == ""

        # raw crash should be unchanged
        assert raw_crash == {}


class TestCollectorInfoRule:
    def test_basic(self):
        raw_crash = {
            "collector_notes": ["some notes"],
        }
        dumps = {}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        rule = CollectorInfoRule()
        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash == raw_crash


class TestCrashReportKeysRule:
    def test_basic(self):
        raw_crash = {
            "Product": "Firefox",
            "Version": "95.0",
            "ReleaseChannel": "nightly",
            "ipc_channel_error": "ouch",
        }
        dumps = {
            "upload_file_minidump": "fake data",
            "upload_file_minidump_flash1": "fake data",
        }
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        rule = CrashReportKeysRule()

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert processor_meta["processor_notes"] == []
        assert processed_crash == {
            "crash_report_keys": [
                "Product",
                "ReleaseChannel",
                "Version",
                "ipc_channel_error",
                "upload_file_minidump",
                "upload_file_minidump_flash1",
            ],
        }

    @pytest.mark.parametrize(
        "key, expected",
        [
            ("ipc_channel_error", "ipc_channel_error"),
            ("ReleaseProcess", "ReleaseProcess"),
            ("ContentSandboxWin32kState", "ContentSandboxWin32kState"),
            ("Add-ons", "Add-ons"),
            # Long keys can be valid, but are truncated to 100 characters
            ("a" * 150, "a" * 100),
        ],
    )
    def test_sanitize_valid(self, key, expected):
        rule = CrashReportKeysRule()

        assert rule.sanitize(key) == expected

    @pytest.mark.parametrize(
        "key",
        [
            # Keys have to have at least one character
            "",
            # Spaces aren't valid
            "   abc   ",
            # Dollar sign isn't valid
            "abc$def",
            # Unicode isn't valid
            "\u0001F44D",
        ],
    )
    def test_sanitize_invalid(self, key):
        rule = CrashReportKeysRule()

        assert rule.sanitize(key) is None

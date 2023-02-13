# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import json
from unittest import mock

from markus.testing import MetricsMock

from socorro.lib.libsocorrodataschema import get_schema, validate_instance
from socorro.processor.pipeline import Pipeline, Status
from socorro.processor.rules.breakpad import (
    CrashingThreadInfoRule,
    MinidumpSha256HashRule,
    MinidumpStackwalkRule,
    TruncateStacksRule,
)


PROCESSED_CRASH_SCHEMA = get_schema("processed_crash.schema.yaml")


example_uuid = "00000000-0000-0000-0000-000002140504"
canonical_standard_raw_crash = {
    "uuid": example_uuid,
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


canonical_stackwalker_output = {
    "crash_info": {
        "address": "0x0",
        "crashing_thread": 0,
        "type": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
    },
    "crashing_thread": {
        "frames": [
            {
                "file": "hg:hg.mozilla.org/releases/mozilla-release:memory/mozjemalloc/jemalloc.c:44234f451065",  # noqa
                "frame": 0,
                "function": "arena_malloc",
                "function_offset": "0x1e3",
                "line": 3067,
                "module": "libmozglue.dylib",
                "module_offset": "0x7883",
                "offset": "0x10000e883",
                "registers": {
                    "r10": "0x0000000000000003",
                    "r11": "0x0000000117fa0400",
                    "r12": "0x0000000000000020",
                    "r13": "0x0000000100200210",
                    "r14": "0x0000000000000000",
                    "r15": "0x0000000100200040",
                    "r8": "0x0000000100200040",
                    "r9": "0x000000000000000e",
                    "rax": "0x0000000100200220",
                    "rbp": "0x0000000000000020",
                    "rbx": "0x0000000000000020",
                    "rcx": "0x0000000000000000",
                    "rdi": "0x0000000100200218",
                    "rdx": "0x0000000000000000",
                    "rip": "0x000000010000e883",
                    "rsi": "0x0000000000000020",
                    "rsp": "0x00007fff5fbfc170",
                },
                "trust": "context",
            },
            {
                "file": "hg:hg.mozilla.org/releases/mozilla-release:memory/mozjemalloc/jemalloc.c:44234f451065",  # noqa
                "frame": 1,
                "function": "je_realloc",
                "function_offset": "0x5a1",
                "line": 4752,
                "module": "libmozglue.dylib",
                "module_offset": "0x2141",
                "offset": "0x100009141",
                "trust": "cfi",
            },
            {
                "frame": 2,
                "function": "malloc_zone_realloc",
                "function_offset": "0x5b",
                "module": "libSystem.B.dylib",
                "module_offset": "0x8b7a",
                "offset": "0x7fff82a27b7a",
                "trust": "context",
            },
            {
                "file": "hg:hg.mozilla.org/releases/mozilla-release:memory/mozjemalloc/jemalloc.c:44234f451065",  # noqa
                "frame": 1,
                "function": "je_realloc",
                "function_offset": "0x5a1",
                "line": 4752,
                "module": "libmozglue.dylib",
                "module_offset": "0x2141",
                "offset": "0x100009141",
                "trust": "cfi",
            },
            {
                "frame": 2,
                "function": "malloc_zone_realloc",
                "function_offset": "0x5b",
                "module": "libSystem.B.dylib",
                "module_offset": "0x8b7a",
                "offset": "0x7fff82a27b7a",
            },
        ]
    },
    "status": "OK",
    "system_info": {
        "cpu_arch": "amd64",
        "cpu_count": 2,
        "cpu_info": "family 6 model 23 stepping 10",
        "os": "Mac OS X",
        "os_ver": "10.6.8 10K549",
    },
    "thread_count": 48,
    # ...
}
canonical_stackwalker_output_str = json.dumps(canonical_stackwalker_output)


class TestCrashingThreadInfoRule:
    def test_valid_data(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {
            "json_dump": {
                "crash_info": {
                    "crashing_thread": 0,
                    "address": "0x0",
                    "type": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                },
                "crashing_thread": {
                    "thread_name": "MainThread",
                },
            }
        }
        validate_instance(processed_crash, PROCESSED_CRASH_SCHEMA)
        status = Status()

        rule = CrashingThreadInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["crashing_thread"] == 0
        assert processed_crash["crashing_thread_name"] == "MainThread"
        assert processed_crash["address"] == "0x0"
        assert processed_crash["reason"] == "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS"

    def test_json_dump_missing(self, tmp_path):
        """If there's no dump data, then this rule doesn't do anything"""
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {}
        validate_instance(instance=processed_crash, schema=PROCESSED_CRASH_SCHEMA)
        status = Status()

        rule = CrashingThreadInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == {}
        assert status.notes == []

    def test_empty_json_dump(self, tmp_path):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {"json_dump": {}}
        validate_instance(instance=processed_crash, schema=PROCESSED_CRASH_SCHEMA)
        status = Status()

        rule = CrashingThreadInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["crashing_thread"] is None
        assert processed_crash["crashing_thread_name"] is None
        assert processed_crash["address"] is None
        assert processed_crash["reason"] == ""


class TestTruncateStacksRule:
    def test_truncate_json_dump(self, tmp_path):
        frames = [
            {
                "frame": 0,
                "file": "hg:hg.mozilla.org/000",
                "function": "js::something",
                "function_offset": "0x00",
                "line": 1000,
                "module": "xul.dll",
                "module_offset": "0x000000",
                "offset": "0x00000000",
                "registers": {
                    "eax": "0x00000001",
                    "ebp": "0x00000002",
                    "ebx": "0x00000003",
                    "ecx": "0x00000004",
                    "edi": "0x00000005",
                    "edx": "0x00000006",
                    "efl": "0x00000007",
                    "eip": "0x00000008",
                    "esi": "0x00000009",
                    "esp": "0x0000000a",
                },
                "trust": "context",
            },
            {
                "frame": 1,
                "file": "hg:hg.mozilla.org/bbb",
                "function": "js::somethingelse",
                "function_offset": "0xbb",
                "line": 1001,
                "module": "xul.dll",
                "module_offset": "0xbbbbbb",
                "offset": "0xbbbbbbbb",
                "trust": "frame_pointer",
            },
        ]

        # Now we make the stack 1,002 frames long
        frame_template = frames[-1]
        for i in range(1000):
            new_frame = copy.deepcopy(frame_template)
            new_frame["frame"] = i + 2
            frames.append(new_frame)

        raw_crash = {}
        dumps = {}
        processed_crash = {
            "json_dump": {
                "crashing_thread": {
                    "threads_index": 0,
                    "frame_count": len(frames),
                    "frames": copy.deepcopy(frames),
                },
                "threads": [
                    {
                        "frame_count": len(frames),
                        "frames": copy.deepcopy(frames),
                    },
                    {
                        "frame_count": 100,
                        "frames": copy.deepcopy(frames)[0:100],
                    },
                ],
                "modules": [],
            }
        }

        validate_instance(instance=processed_crash, schema=PROCESSED_CRASH_SCHEMA)
        status = Status()

        rule = TruncateStacksRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        json_dump = processed_crash["json_dump"]

        # Check crashing thread is truncated
        assert len(json_dump["crashing_thread"]["frames"]) == 500
        assert json_dump["crashing_thread"]["truncated"] is True
        assert json_dump["threads"][0]["frames"][250] == {
            "truncated": {"msg": "502 frames truncated"}
        }

        # Check thread 0 is truncated
        assert len(json_dump["threads"][0]["frames"]) == 500
        assert json_dump["threads"][0]["truncated"] is True
        assert json_dump["threads"][0]["frames"][250] == {
            "truncated": {"msg": "502 frames truncated"}
        }

        # Check thread 1 is not truncated
        assert len(json_dump["threads"][1]["frames"]) == 100
        assert "truncated" not in json_dump["threads"][1]

        validate_instance(instance=processed_crash, schema=PROCESSED_CRASH_SCHEMA)

    def test_truncate_upload_file_minidump_browser(self, tmp_path):
        frames = [
            {
                "frame": 0,
                "file": "hg:hg.mozilla.org/000",
                "function": "js::something",
                "function_offset": "0x00",
                "line": 1000,
                "module": "xul.dll",
                "module_offset": "0x000000",
                "offset": "0x00000000",
                "registers": {
                    "eax": "0x00000001",
                    "ebp": "0x00000002",
                    "ebx": "0x00000003",
                    "ecx": "0x00000004",
                    "edi": "0x00000005",
                    "edx": "0x00000006",
                    "efl": "0x00000007",
                    "eip": "0x00000008",
                    "esi": "0x00000009",
                    "esp": "0x0000000a",
                },
                "trust": "context",
            },
            {
                "frame": 1,
                "file": "hg:hg.mozilla.org/bbb",
                "function": "js::somethingelse",
                "function_offset": "0xbb",
                "line": 1001,
                "module": "xul.dll",
                "module_offset": "0xbbbbbb",
                "offset": "0xbbbbbbbb",
                "trust": "frame_pointer",
            },
        ]

        # Now we make the stack 1,002 frames long
        frame_template = frames[-1]
        for i in range(1000):
            new_frame = copy.deepcopy(frame_template)
            new_frame["frame"] = i + 2
            frames.append(new_frame)

        raw_crash = {}
        dumps = {}
        processed_crash = {
            "upload_file_minidump_browser": {
                "json_dump": {
                    "crashing_thread": {
                        "threads_index": 0,
                        "frame_count": len(frames),
                        "frames": copy.deepcopy(frames),
                    },
                    "threads": [
                        {
                            "frame_count": len(frames),
                            "frames": copy.deepcopy(frames),
                        },
                        {
                            "frame_count": 100,
                            "frames": copy.deepcopy(frames)[0:100],
                        },
                    ],
                    "modules": [],
                }
            }
        }

        validate_instance(instance=processed_crash, schema=PROCESSED_CRASH_SCHEMA)
        status = Status()

        rule = TruncateStacksRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        json_dump = processed_crash["upload_file_minidump_browser"]["json_dump"]

        # Check crashing thread is truncated
        assert len(json_dump["crashing_thread"]["frames"]) == 500
        assert json_dump["crashing_thread"]["truncated"] is True
        assert json_dump["threads"][0]["frames"][250] == {
            "truncated": {"msg": "502 frames truncated"}
        }

        # Check thread 0 is truncated
        assert len(json_dump["threads"][0]["frames"]) == 500
        assert json_dump["threads"][0]["truncated"] is True
        assert json_dump["threads"][0]["frames"][250] == {
            "truncated": {"msg": "502 frames truncated"}
        }

        # Check thread 1 is not truncated
        assert len(json_dump["threads"][1]["frames"]) == 100
        assert "truncated" not in json_dump["threads"][1]

        validate_instance(instance=processed_crash, schema=PROCESSED_CRASH_SCHEMA)


class TestMinidumpSha256HashRule:
    def test_no_dump_checksum(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = MinidumpSha256HashRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["minidump_sha256_hash"] == ""

    def test_copy_over(self, tmp_path):
        raw_crash = {"metadata": {"dump_checksums": {"upload_file_minidump": "hash"}}}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = MinidumpSha256HashRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["minidump_sha256_hash"] == "hash"


class ProcessCompletedMock:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        assert isinstance(stdout, bytes)
        self.stdout = stdout
        assert isinstance(stderr, bytes)
        self.stderr = stderr


MINIMAL_STACKWALKER_OUTPUT = {
    "status": "OK",
    "crash_info": {
        "address": "0x0",
        "assertion": None,
        "crashing_thread": 0,
        "type": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
    },
    "crashing_thread": {
        "frame_count": 1,
        "last_error_value": "ERROR_SUCCESS",
        "thread_index": 0,
        "thread_name": None,
        "frames": [
            {
                "file": None,
                "frame": 0,
                "function": "NtWaitForMultipleObjects",
                "function_offset": "0x000000000000000a",
                "line": None,
                "missing_symbols": False,
                "module": "ntdll.dll",
                "module_offset": "0x0000000000069d5a",
                "offset": "0x0000000077539d5a",
                "registers": {
                    "r10": "0xfefefefefefefeff",
                    "r11": "0x8080808080808080",
                    "r12": "0x0000000000000000",
                    "r13": "0x000000000086c180",
                    "r14": "0x0000000000000000",
                    "r15": "0x0000000080000000",
                    "r8": "0x0000000000000000",
                    "r9": "0x0000000000000008",
                    "rax": "0x0000000000000058",
                    "rbp": "0x0000000000000002",
                    "rbx": "0x000000000086c210",
                    "rcx": "0x0000000000000002",
                    "rdi": "0x0000000000000002",
                    "rdx": "0x000000000086c180",
                    "rip": "0x0000000077539d5a",
                    "rsi": "0x0000000000000001",
                    "rsp": "0x000000000086c0d8",
                },
                "trust": "context",
            },
        ],
    },
    "lsb_release": None,
    "mac_crash_info": None,
    "main_module": 0,
    "modules": [
        {
            "base_addr": "0x00000000774d0000",
            "cert_subject": "Microsoft Windows",
            "code_id": "5E0EB67F19f000",
            "corrupt_symbols": False,
            "debug_file": "ntdll.pdb",
            "debug_id": "0A682A2081CD49B19C5CB941603074381",
            "end_addr": "0x000000007766f000",
            "filename": "ntdll.dll",
            "loaded_symbols": True,
            "missing_symbols": False,
            "symbol_url": "https://symbols.mozilla.org/try/ntdll.pdb/0A682A2081CD49B19C5CB941603074381/ntdll.sym",
            "version": "6.1.7601.24545",
        },
    ],
    "system_info": {
        "cpu_arch": "amd64",
        "cpu_count": 2,
        "cpu_info": "family 6 model 23 stepping 10",
        "cpu_microcode_version": None,
        "os": "Windows NT",
        "os_ver": "6.1.7601 Service Pack 1",
    },
    "thread_count": 1,
    "threads": [
        {
            "frame_count": 1,
            "last_error_value": "ERROR_SUCCESS",
            "thread_name": None,
            "frames": [
                {
                    "file": None,
                    "frame": 0,
                    "function": "NtWaitForMultipleObjects",
                    "function_offset": "0x000000000000000a",
                    "line": None,
                    "missing_symbols": False,
                    "module": "ntdll.dll",
                    "module_offset": "0x0000000000069d5a",
                    "offset": "0x0000000077539d5a",
                    "registers": {
                        "r10": "0xfefefefefefefeff",
                        "r11": "0x8080808080808080",
                        "r12": "0x0000000000000000",
                        "r13": "0x000000000086c180",
                        "r14": "0x0000000000000000",
                        "r15": "0x0000000080000000",
                        "r8": "0x0000000000000000",
                        "r9": "0x0000000000000008",
                        "rax": "0x0000000000000058",
                        "rbp": "0x0000000000000002",
                        "rbx": "0x000000000086c210",
                        "rcx": "0x0000000000000002",
                        "rdi": "0x0000000000000002",
                        "rdx": "0x000000000086c180",
                        "rip": "0x0000000077539d5a",
                        "rsi": "0x0000000000000001",
                        "rsp": "0x000000000086c0d8",
                    },
                    "trust": "context",
                },
            ],
        },
    ],
    "unloaded_modules": [],
}
MINIMAL_STACKWALKER_OUTPUT_STR = json.dumps(MINIMAL_STACKWALKER_OUTPUT)


class TestMinidumpStackwalkRule:
    # NOTE(willkg): this tests the mechanics of the rule that runs minidump-stackwalk,
    # but doesn't test minidump-stackwalk itself
    def build_rule(self):
        config = Pipeline.required_config.minidumpstackwalk

        return MinidumpStackwalkRule(
            dump_field="upload_file_minidump",
            symbols_urls=config.symbols_urls.default,
            command_path=config.command_path.default,
            command_line=config.command_line.default,
            kill_timeout=5,
            symbol_tmp_path="/tmp/symbols/tmp",
            symbol_cache_path="/tmp/symbols/cache",
        )

    def test_everything_we_hoped_for(self, tmp_path):
        rule = self.build_rule()

        dumppath = tmp_path / "dumpfile.dmp"
        dumppath.write_text("abcde")

        raw_crash = {"uuid": example_uuid}
        dumps = {rule.dump_field: str(dumppath)}
        processed_crash = {}
        status = Status()

        with MetricsMock() as mm:
            with mock.patch(
                "socorro.processor.rules.breakpad.subprocess"
            ) as mock_subprocess:
                mock_subprocess.run.return_value = ProcessCompletedMock(
                    returncode=0,
                    stdout=MINIMAL_STACKWALKER_OUTPUT_STR.encode("utf-8"),
                    stderr=b"",
                )

                rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

            expected_output = copy.deepcopy(MINIMAL_STACKWALKER_OUTPUT)

            assert processed_crash["mdsw_return_code"] == 0
            assert processed_crash["mdsw_status_string"] == "OK"
            assert processed_crash["success"] is True
            assert processed_crash["json_dump"] == expected_output
            assert processed_crash["stackwalk_version"] == rule.stackwalk_version

            mm.assert_incr(
                "processor.minidumpstackwalk.run",
                tags=["outcome:success", "exitcode:0"],
            )

    def test_stackwalker_timeout(self, tmp_path):
        # NOTE(willkg): we run the stackwalker with a "timeout --signal KILL ..." When
        # stackwalker exceeds the amount of time alotted, timeout kills it with a
        # SIGKILL (9) and subprocess denotes that using a negative exit code of -9.
        # This tests that.
        rule = self.build_rule()

        dumppath = tmp_path / "dumpfile.dmp"
        dumppath.write_text("abcde")

        raw_crash = {"uuid": example_uuid}
        dumps = {rule.dump_field: str(dumppath)}
        processed_crash = {}
        status = Status()

        with MetricsMock() as mm:
            with mock.patch(
                "socorro.processor.rules.breakpad.subprocess"
            ) as mock_subprocess:
                mock_subprocess.run.return_value = ProcessCompletedMock(
                    returncode=-9, stdout=b"{}\n", stderr=b""
                )

                rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

            assert processed_crash["mdsw_return_code"] == -9
            assert processed_crash["mdsw_status_string"] == "unknown error"
            assert processed_crash["stackwalk_version"] == rule.stackwalk_version
            assert processed_crash["success"] is False
            assert status.notes == [
                "MinidumpStackwalkRule: minidump-stackwalk: timeout (SIGKILL)"
            ]

            mm.assert_incr(
                "processor.minidumpstackwalk.run",
                tags=["outcome:fail", "exitcode:-9"],
            )

    def test_stackwalker_bad_output(self, tmp_path):
        rule = self.build_rule()

        dumppath = tmp_path / "dumpfile.dmp"
        dumppath.write_text("abcde")

        raw_crash = {"uuid": example_uuid}
        dumps = {rule.dump_field: str(dumppath)}
        processed_crash = {}
        status = Status()

        with mock.patch(
            "socorro.processor.rules.breakpad.subprocess"
        ) as mock_subprocess:
            mock_subprocess.run.return_value = ProcessCompletedMock(
                returncode=-1, stdout=b"{ff", stderr=b"boo hiss"
            )

            rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["mdsw_return_code"] == -1
        assert processed_crash["mdsw_status_string"] == "unknown error"
        assert processed_crash["mdsw_stderr"] == "boo hiss"
        assert processed_crash["stackwalk_version"] == rule.stackwalk_version
        assert not processed_crash["success"]
        assert (
            status.notes[0]
            == "MinidumpStackwalkRule: minidump-stackwalk: failed: -1: unknown error"
        )

    def test_empty_minidump_shortcut(self, tmp_path):
        rule = self.build_rule()

        # Write a 0-byte minidump file with the correct name
        dumppath = tmp_path / "upload_file_minidump"
        dumppath.write_text("")

        raw_crash = {"uuid": example_uuid}
        dumps = {rule.dump_field: str(dumppath)}
        processed_crash = {}
        status = Status()

        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash["mdsw_status_string"] == "EmptyMinidump"
        assert processed_crash["mdsw_stderr"] == "Shortcut for 0-bytes minidump."

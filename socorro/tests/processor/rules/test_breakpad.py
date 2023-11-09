# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import json
from unittest import mock

from markus.testing import MetricsMock
import pytest

from socorro.lib.libsocorrodataschema import get_schema, validate_instance
from socorro.processor.pipeline import Status
from socorro.processor.rules.breakpad import (
    execute_process,
    CrashingThreadInfoRule,
    MinidumpSha256HashRule,
    MinidumpStackwalkRule,
    PossibleBitFlipsRule,
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
        "address": "0x0000000000000000",
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


def test_execute_process():
    ret = execute_process("echo foo")
    assert ret["stdout"] == b"foo\n"
    assert ret["stderr"] == b""
    assert ret["returncode"] == 0


def test_execute_process_timeout():
    ret = execute_process("sleep 10", timeout=1)
    assert ret["stdout"] == b""
    assert ret["stderr"] == b""
    assert ret["returncode"] == -9


class TestCrashingThreadInfoRule:
    @pytest.mark.parametrize(
        "json_dump, expected",
        [
            # Test basic case
            (
                {
                    "crash_info": {
                        "crashing_thread": 0,
                        "address": "0x00007fff0b54a5d7",
                        "type": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                    },
                    "crashing_thread": {
                        "thread_name": "MainThread",
                    },
                },
                {
                    "crashing_thread": 0,
                    "crashing_thread_name": "MainThread",
                    "address": "0x00007fff0b54a5d7",
                    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                },
            ),
            # json_dump is missing
            (
                None,
                {},
            ),
            # empty json_dump
            (
                {},
                {
                    "crashing_thread": None,
                    "crashing_thread_name": None,
                    "address": None,
                    "reason": "",
                },
            ),
        ],
    )
    def test_scenarios(self, tmp_path, json_dump, expected):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        if json_dump is None:
            processed_crash = {}
        else:
            processed_crash = {"json_dump": json_dump}
            expected["json_dump"] = json_dump
        validate_instance(processed_crash, PROCESSED_CRASH_SCHEMA)
        status = Status()

        rule = CrashingThreadInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == expected

    @pytest.mark.parametrize(
        "json_dump, expected",
        [
            # use "address" value if "adjusted_address" doesn't exist
            (
                {
                    "crash_info": {
                        "crashing_thread": 0,
                        "address": "0x00007fff0b54a5d7",
                        "type": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                    },
                    "crashing_thread": {
                        "thread_name": "MainThread",
                    },
                },
                {
                    "crashing_thread": 0,
                    "crashing_thread_name": "MainThread",
                    "address": "0x00007fff0b54a5d7",
                    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                },
            ),
            # use "address" value if "adjusted_address" is null
            (
                {
                    "crash_info": {
                        "crashing_thread": 0,
                        "address": "0x00007fff0b54a5d7",
                        "adjusted_address": None,
                        "type": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                    },
                    "crashing_thread": {
                        "thread_name": "MainThread",
                    },
                },
                {
                    "crashing_thread": 0,
                    "crashing_thread_name": "MainThread",
                    "address": "0x00007fff0b54a5d7",
                    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                },
            ),
            # use null (32-bit) if adjusted_address.kind is "null-pointer"
            (
                {
                    "crash_info": {
                        "crashing_thread": 0,
                        "address": "0x00000048",
                        "adjusted_address": {
                            "kind": "null-pointer",
                            "offset": "0x00000048",
                        },
                        "type": "EXCEPTION_ACCESS_VIOLATION_READ",
                    },
                    "crashing_thread": {
                        "thread_name": "MainThread",
                    },
                },
                {
                    "crashing_thread": 0,
                    "crashing_thread_name": "MainThread",
                    "address": "0x00000000",
                    "reason": "EXCEPTION_ACCESS_VIOLATION_READ",
                },
            ),
            # use null (64-bit) if adjusted_address.kind is "null-pointer"
            (
                {
                    "crash_info": {
                        "crashing_thread": 0,
                        "address": "0x0000000000000048",
                        "adjusted_address": {
                            "kind": "null-pointer",
                            "offset": "0x0000000000000048",
                        },
                        "type": "EXCEPTION_ACCESS_VIOLATION_READ",
                    },
                    "crashing_thread": {
                        "thread_name": "MainThread",
                    },
                },
                {
                    "crashing_thread": 0,
                    "crashing_thread_name": "MainThread",
                    "address": "0x0000000000000000",
                    "reason": "EXCEPTION_ACCESS_VIOLATION_READ",
                },
            ),
            # use adjusted_address.address if adjusted_address.kind is "non-canonical"
            (
                {
                    "crash_info": {
                        "crashing_thread": 0,
                        "address": "0xffffffffffffffff",
                        "adjusted_address": {
                            "address": "0xe5e5e5e5e5e5e61d",
                            "kind": "non-canonical",
                        },
                        "type": "EXCEPTION_ACCESS_VIOLATION_READ",
                    },
                    "crashing_thread": {
                        "thread_name": "MainThread",
                    },
                },
                {
                    "crashing_thread": 0,
                    "crashing_thread_name": "MainThread",
                    "address": "0xe5e5e5e5e5e5e61d",
                    "reason": "EXCEPTION_ACCESS_VIOLATION_READ",
                },
            ),
        ],
    )
    def test_address_scenarios(self, tmp_path, json_dump, expected):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        if json_dump is None:
            processed_crash = {}
        else:
            processed_crash = {"json_dump": json_dump}
            expected["json_dump"] = json_dump
        validate_instance(processed_crash, PROCESSED_CRASH_SCHEMA)
        status = Status()

        rule = CrashingThreadInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert processed_crash == expected


class TestPossibleBitFlipsRule:
    def test_no_data(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        status = Status()

        rule = PossibleBitFlipsRule()

        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "possible_bit_flips_max_confidence" not in processed_crash

    def test_null(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {"json_dump": {"crash_info": {"possible_bit_flips": None}}}
        status = Status()

        rule = PossibleBitFlipsRule()

        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "possible_bit_flips_max_confidence" not in processed_crash

    def test_empty_array(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {"json_dump": {"crash_info": {"possible_bit_flips": []}}}
        status = Status()

        rule = PossibleBitFlipsRule()

        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        assert "possible_bit_flips_max_confidence" not in processed_crash

    def test_max(self, tmp_path):
        raw_crash = {}
        dumps = {}
        processed_crash = {
            "json_dump": {
                "crash_info": {
                    "possible_bit_flips": [
                        {
                            "address": "0x00007ffdaf60bf90",
                            "confidence": 0.625,
                            "details": {
                                "is_null": False,
                                "nearby_registers": 1,
                                "poison_registers": False,
                                "was_low": False,
                                "was_non_canonical": False,
                            },
                            "source_register": None,
                        },
                        {
                            "address": "0x00007ffdaf60ef90",
                            "confidence": 0.25,
                            "details": {
                                "is_null": False,
                                "nearby_registers": 0,
                                "poison_registers": False,
                                "was_low": False,
                                "was_non_canonical": False,
                            },
                            "source_register": None,
                        },
                    ]
                }
            }
        }
        status = Status()

        rule = PossibleBitFlipsRule()

        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)

        # NOTE(willkg): max is int(0.625 * 100)
        assert processed_crash["possible_bit_flips_max_confidence"] == 62


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
        "address": "0x0000000000000000",
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
    def test_everything_we_hoped_for(self, tmp_path):
        rule = MinidumpStackwalkRule(
            symbol_tmp_path=str(tmp_path / "tmp"),
            symbol_cache_path=str(tmp_path / "cache"),
        )

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

                # We mocked the subprocess, so we have to generate the output files we're
                # expecting.
                output_path = tmp_path / f"{example_uuid}.{rule.dump_field}.json"
                output_path.write_text(MINIMAL_STACKWALKER_OUTPUT_STR)
                log_path = tmp_path / f"{example_uuid}.{rule.dump_field}.log"
                log_path.write_text("")

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
        rule = MinidumpStackwalkRule(
            symbol_tmp_path=str(tmp_path / "tmp"),
            symbol_cache_path=str(tmp_path / "cache"),
        )

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
        rule = MinidumpStackwalkRule(
            symbol_tmp_path=str(tmp_path / "tmp"),
            symbol_cache_path=str(tmp_path / "cache"),
        )

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

            # We mocked the subprocess, so we have to generate the output files we're
            # expecting.
            output_path = tmp_path / f"{example_uuid}.{rule.dump_field}.json"
            output_path.write_text("{ff")
            log_path = tmp_path / f"{example_uuid}.{rule.dump_field}.log"
            log_path.write_text("boo hiss")

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
        rule = MinidumpStackwalkRule(
            symbol_tmp_path=str(tmp_path / "tmp"),
            symbol_cache_path=str(tmp_path / "cache"),
        )

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

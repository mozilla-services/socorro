# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from contextlib import contextmanager
import copy
import json
from unittest import mock

from markus.testing import MetricsMock

from socorro.processor.processor_pipeline import ProcessorPipeline
from socorro.processor.rules.breakpad import (
    BreakpadStackwalkerRule2015,
    CrashingThreadRule,
    JitCrashCategorizeRule,
    MinidumpSha256Rule,
)
from socorro.unittest.processor import get_basic_processor_meta


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
    "Winsock_LSP": (
        "MSAFD Tcpip [TCP/IPv6] : 2 : 1 :  \n "
        "MSAFD Tcpip [UDP/IPv6] : 2 : 2 : "
        "%SystemRoot%\\system32\\mswsock.dll \n "
        "MSAFD Tcpip [RAW/IPv6] : 2 : 3 :  \n "
        "MSAFD Tcpip [TCP/IP] : 2 : 1 : "
        "%SystemRoot%\\system32\\mswsock.dll \n "
        "MSAFD Tcpip [UDP/IP] : 2 : 2 :  \n "
        "MSAFD Tcpip [RAW/IP] : 2 : 3 : "
        "%SystemRoot%\\system32\\mswsock.dll \n "
        "\u041f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a "
        "\u0443\u0441\u043b\u0443\u0433 RSVP TCPv6 : 2 : 1 :  \n "
        "\u041f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a "
        "\u0443\u0441\u043b\u0443\u0433 RSVP TCP : 2 : 1 : "
        "%SystemRoot%\\system32\\mswsock.dll \n "
        "\u041f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a "
        "\u0443\u0441\u043b\u0443\u0433 RSVP UDPv6 : 2 : 2 :  \n "
        "\u041f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a "
        "\u0443\u0441\u043b\u0443\u0433 RSVP UDP : 2 : 2 : "
        "%SystemRoot%\\system32\\mswsock.dll"
    ),
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


class MyBreakpadStackwalkerRule2015(BreakpadStackwalkerRule2015):
    @contextmanager
    def _temp_raw_crash_json_file(self, raw_crash, crash_id):
        yield "%s.json" % raw_crash["uuid"]


class TestCrashingThreadRule:
    def test_everything_we_hoped_for(self):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {"json_dump": copy.deepcopy(canonical_stackwalker_output)}
        processor_meta = get_basic_processor_meta()

        rule = CrashingThreadRule()
        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert processed_crash["crashedThread"] == 0

    def test_stuff_missing(self):
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {}
        processed_crash = {"json_dump": {}}
        processor_meta = get_basic_processor_meta()

        rule = CrashingThreadRule()
        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert processed_crash["crashedThread"] is None
        assert processor_meta["processor_notes"] == [
            "MDSW did not identify the crashing thread"
        ]


class TestMinidumpSha256HashRule:
    def test_hash_not_in_raw_crash(self):
        raw_crash = {}
        dumps = {}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        rule = MinidumpSha256Rule()
        assert (
            rule.predicate(raw_crash, dumps, processed_crash, processor_meta) is False
        )

    def test_hash_in_raw_crash(self):
        raw_crash = {"MinidumpSha256Hash": "hash"}
        dumps = {}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        rule = MinidumpSha256Rule()
        assert rule.predicate(raw_crash, dumps, processed_crash, processor_meta) is True

        rule.act(raw_crash, dumps, processed_crash, processor_meta)
        assert processed_crash["minidump_sha256_hash"] == "hash"


canonical_external_output = {"key": "value"}
canonical_external_output_str = json.dumps(canonical_external_output)


class TestBreakpadTransformRule2015:
    def build_rule(self):
        pprcb = ProcessorPipeline.required_config.breakpad

        return BreakpadStackwalkerRule2015(
            dump_field="upload_file_minidump",
            symbols_urls=pprcb.symbols_urls.default,
            command_pathname=pprcb.command_pathname.default,
            command_line=pprcb.command_line.default,
            kill_timeout=5,
            symbol_tmp_path="/tmp/symbols/tmp",
            symbol_cache_path="/tmp/symbols/cache",
            tmp_storage_path="/tmp",
        )

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_everything_we_hoped_for(self, mocked_subprocess_module):
        rule = self.build_rule()

        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = (
            canonical_stackwalker_output_str
        )
        mocked_subprocess_handle.wait.return_value = 0

        with MetricsMock() as mm:
            rule.act(raw_crash, dumps, processed_crash, processor_meta)

            assert processed_crash["json_dump"] == canonical_stackwalker_output
            assert processed_crash["mdsw_return_code"] == 0
            assert processed_crash["mdsw_status_string"] == "OK"
            assert processed_crash["success"] is True

            mm.assert_incr(
                "processor.breakpadstackwalkerrule.run",
                tags=["outcome:success", "exitcode:0"],
            )

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_stackwalker_fails(self, mocked_subprocess_module):
        rule = self.build_rule()

        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "{}\n"
        mocked_subprocess_handle.wait.return_value = 124

        with MetricsMock() as mm:
            rule.act(raw_crash, dumps, processed_crash, processor_meta)

            assert processed_crash["json_dump"] == {}
            assert processed_crash["mdsw_return_code"] == 124
            assert processed_crash["mdsw_status_string"] == "unknown error"
            assert processed_crash["success"] is False
            assert processor_meta["processor_notes"] == ["MDSW timeout (SIGKILL)"]

            mm.assert_incr(
                "processor.breakpadstackwalkerrule.run",
                tags=["outcome:fail", "exitcode:124"],
            )

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_stackwalker_fails_2(self, mocked_subprocess_module):
        rule = self.build_rule()

        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {}
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        # This will cause json.loads to throw an error
        mocked_subprocess_handle.stdout.read.return_value = "{ff"
        mocked_subprocess_handle.wait.return_value = -1

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert processed_crash["json_dump"] == {}
        assert processed_crash["mdsw_return_code"] == -1
        assert processed_crash["mdsw_status_string"] == "unknown error"
        assert not processed_crash["success"]
        assert (
            f"{rule.command_pathname} output failed in json: "
            + "Unexpected character found when decoding 'false'"
        ) in processor_meta["processor_notes"][0]
        assert (
            processor_meta["processor_notes"][1] == "MDSW failed with -1: unknown error"
        )

    @mock.patch("socorro.processor.rules.breakpad.os.unlink")
    def test_temp_file_context(self, mocked_unlink):
        rule = self.build_rule()
        with rule._temp_raw_crash_json_file("foo.json", example_uuid):
            pass
        mocked_unlink.assert_called_once_with(
            "/tmp/%s.MainThread.TEMPORARY.json" % example_uuid
        )
        mocked_unlink.reset_mock()

        try:
            with rule._temp_raw_crash_json_file("foo.json", example_uuid):
                raise KeyError("oops")
        except KeyError:
            pass
        mocked_unlink.assert_called_once_with(
            "/tmp/%s.MainThread.TEMPORARY.json" % example_uuid
        )
        mocked_unlink.reset_mock()


class TestJitCrashCategorizeRule:
    def build_rule(self):
        pprcj = ProcessorPipeline.required_config.jit
        return JitCrashCategorizeRule(
            dump_field=pprcj.dump_field.default,
            command_pathname=pprcj.command_pathname.default,
            command_line=pprcj.command_line.default,
            kill_timeout=5,
        )

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_everything_we_hoped_for(self, mocked_subprocess_module):
        rule = self.build_rule()

        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows 386",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"not_module": "not-a-module"}, {"module": "a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "EXTRA-SPECIAL"
        mocked_subprocess_handle.wait.return_value = 0

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert processor_meta["processor_notes"] == []
        assert processed_crash["classifications"]["jit"]["category"] == "EXTRA-SPECIAL"
        assert processed_crash["classifications"]["jit"]["category_return_code"] == 0

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_success_all_types_of_signatures(self, mocked_subprocess_module):
        rule = self.build_rule()

        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        base_processed_crash = {
            "product": "Firefox",
            "os_name": "Windows 386",
            "cpu_arch": "x86",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"not_module": "not-a-module"}, {"module": "a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "EXTRA-SPECIAL"
        mocked_subprocess_handle.wait.return_value = 0

        signatures = [
            "EnterBaseline",
            "moz::something | EnterBaseline",
            "EnterIon",
            "js::jit::FastInvoke",
            "Foo::Bar__js::jit::IonCannon",
            "Small | js::irregexp::ExecuteCode<T>",
        ]
        for signature in signatures:
            processed_crash = copy.deepcopy(base_processed_crash)
            processed_crash["signature"] = signature
            rule.act(raw_crash, dumps, processed_crash, processor_meta)

            assert processor_meta["processor_notes"] == []
            assert (
                processed_crash["classifications"]["jit"]["category"] == "EXTRA-SPECIAL"
            )
            assert (
                processed_crash["classifications"]["jit"]["category_return_code"] == 0
            )

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_subprocess_fail(self, mocked_subprocess_module):
        rule = self.build_rule()
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows 386",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"not_module": "not-a-module"}, {"module": "a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = None
        mocked_subprocess_handle.wait.return_value = -1

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert processor_meta["processor_notes"] == []
        assert processed_crash["classifications"]["jit"]["category"] is None
        assert processed_crash["classifications"]["jit"]["category_return_code"] == -1

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_wrong_os(self, mocked_subprocess_module):
        rule = self.build_rule()
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {
            "product": "Firefox",
            "os_name": "MS-DOS",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"not_module": "not-a-module"}, {"module": "a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "EXTRA-SPECIAL"
        mocked_subprocess_handle.wait.return_value = 0

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert "classifications.jit.category" not in processed_crash
        assert "classifications.jit.category_return_code" not in processed_crash

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_wrong_product(self, mocked_subprocess_module):
        rule = self.build_rule()
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {
            "product": "Firefrenzy",
            "os_name": "Windows NT",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"not_module": "not-a-module"}, {"module": "a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "EXTRA-SPECIAL"
        mocked_subprocess_handle.wait.return_value = 0

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert "classifications.jit.category" not in processed_crash
        assert "classifications.jit.category_return_code" not in processed_crash

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_wrong_cpu(self, mocked_subprocess_module):
        rule = self.build_rule()
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows NT",
            "cpu_arch": "VAX 750",
            "signature": "EnterBaseline",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"not_module": "not-a-module"}, {"module": "a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "EXTRA-SPECIAL"
        mocked_subprocess_handle.wait.return_value = 0

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert "classifications.jit.category" not in processed_crash
        assert "classifications.jit.category_return_code" not in processed_crash

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_wrong_signature(self, mocked_subprocess_module):
        rule = self.build_rule()
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows NT",
            "cpu_arch": "x86",
            "signature": "this-is-not-a-JIT-signature",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"not_module": "not-a-module"}, {"module": "a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "EXTRA-SPECIAL"
        mocked_subprocess_handle.wait.return_value = 0

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert "classifications.jit.category" not in processed_crash
        assert "classifications.jit.category_return_code" not in processed_crash

    @mock.patch("socorro.processor.rules.breakpad.subprocess")
    def test_module_on_stack_top(self, mocked_subprocess_module):
        rule = self.build_rule()
        raw_crash = copy.deepcopy(canonical_standard_raw_crash)
        dumps = {rule.dump_field: "a_fake_dump.dump"}
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows NT",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            "json_dump": {
                "crashing_thread": {
                    "frames": [{"module": "a-module"}, {"not_module": "not-a-module"}]
                }
            },
        }
        processor_meta = get_basic_processor_meta()

        mocked_subprocess_handle = mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = "EXTRA-SPECIAL"
        mocked_subprocess_handle.wait.return_value = 0

        rule.act(raw_crash, dumps, processed_crash, processor_meta)

        assert "classifications.jit.category" not in processed_crash
        assert "classifications.jit.category_return_code" not in processed_crash

    def test_predicate_no_json_dump(self):
        rule = self.build_rule()
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows NT",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
        }

        assert rule.predicate({}, {}, processed_crash, {}) is True

    def test_predicate_no_crashing_thread(self):
        rule = self.build_rule()
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows NT",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            # No "crashing_thread" key
            "json_dump": {},
        }

        assert rule.predicate({}, {}, processed_crash, {}) is True

    def test_predicate_no_frames(self):
        rule = self.build_rule()
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows NT",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            "json_dump": {
                # No "frames" key
                "crashing_thread": {}
            },
        }

        assert rule.predicate({}, {}, processed_crash, {}) is True

    def test_predicate_empty_frames(self):
        rule = self.build_rule()
        processed_crash = {
            "product": "Firefox",
            "os_name": "Windows NT",
            "cpu_arch": "x86",
            "signature": "EnterBaseline",
            "json_dump": {
                "crashing_thread": {
                    # There is a "frames" key, but nothing in the list
                    "frames": []
                }
            },
        }

        assert rule.predicate({}, {}, processed_crash, {}) is True

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from contextlib import contextmanager
import copy
import ujson

from configman.dotdict import DotDict as CDotDict
from mock import Mock, patch

from socorro.lib.util import DotDict
from socorro.processor.breakpad_transform_rules import (
    BreakpadStackwalkerRule2015,
    CrashingThreadRule,
    ExternalProcessRule,
    JitCrashCategorizeRule
)
from socorro.unittest.testbase import TestCase

example_uuid = '00000000-0000-0000-0000-000002140504'
canonical_standard_raw_crash = DotDict({
    "uuid": example_uuid,
    "InstallTime": "1335439892",
    "AdapterVendorID": "0x1002",
    "TotalVirtualMemory": "4294836224",
    "Comments": "why did my browser crash?  #fail",
    "Theme": "classic/1.0",
    "Version": "12.0",
    "Email": "noreply@mozilla.com",
    "Vendor": "Mozilla",
    "EMCheckCompatibility": "true",
    "Throttleable": "1",
    "id": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
    "buildid": "20120420145725",
    "AvailablePageFile": "10641510400",
    "version": "12.0",
    "AdapterDeviceID": "0x7280",
    "ReleaseChannel": "release",
    "submitted_timestamp": "2012-05-08T23:26:33.454482+00:00",
    "URL": "http://www.mozilla.com",
    "timestamp": 1336519593.454627,
    "Notes": "AdapterVendorID: 0x1002, AdapterDeviceID: 0x7280, "
             "AdapterSubsysID: 01821043, "
             "AdapterDriverVersion: 8.593.100.0\nD3D10 Layers? D3D10 "
             "Layers- D3D9 Layers? D3D9 Layers- ",
    "CrashTime": "1336519554",
    "Winsock_LSP": "MSAFD Tcpip [TCP/IPv6] : 2 : 1 :  \n "
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
                   "%SystemRoot%\\system32\\mswsock.dll",
    "FramePoisonBase": "00000000f0de0000",
    "AvailablePhysicalMemory": "2227773440",
    "FramePoisonSize": "65536",
    "StartupTime": "1336499438",
    "Add-ons": "adblockpopups@jessehakanen.net:0.3,"
               "dmpluginff%40westbyte.com:1%2C4.8,"
               "firebug@software.joehewitt.com:1.9.1,"
               "killjasmin@pierros14.com:2.4,"
               "support@surfanonymous-free.com:1.0,"
               "uploader@adblockfilters.mozdev.org:2.1,"
               "{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}:20111107,"
               "{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}:2.0.3,"
               "anttoolbar@ant.com:2.4.6.4,"
               "{972ce4c6-7e08-4474-a285-3208198ce6fd}:12.0,"
               "elemhidehelper@adblockplus.org:1.2.1",
    "BuildID": "20120420145725",
    "SecondsSinceLastCrash": "86985",
    "ProductName": "Firefox",
    "legacy_processing": 0,
    "AvailableVirtualMemory": "3812708352",
    "SystemMemoryUsePercentage": "48",
    "ProductID": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
    "Distributor": "Mozilla",
    "Distributor_version": "12.0",

})


cannonical_stackwalker_output = {
    u'crash_info': {
        u'address': u'0x0',
        u'crashing_thread': 0,
        u'type': u'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS'
    },
    u'crashing_thread': {
        u'frames': [
            {
                u'file': u'hg:hg.mozilla.org/releases/mozilla-release:'
                         'memory/mozjemalloc/jemalloc.c:44234f451065',
                u'frame': 0,
                u'function': u'arena_malloc',
                u'function_offset': u'0x1e3',
                u'line': 3067,
                u'module': u'libmozglue.dylib',
                u'module_offset': u'0x7883',
                u'offset': u'0x10000e883',
                u'registers': {
                    u'r10': u'0x0000000000000003',
                    u'r11': u'0x0000000117fa0400',
                    u'r12': u'0x0000000000000020',
                    u'r13': u'0x0000000100200210',
                    u'r14': u'0x0000000000000000',
                    u'r15': u'0x0000000100200040',
                    u'r8': u'0x0000000100200040',
                    u'r9': u'0x000000000000000e',
                    u'rax': u'0x0000000100200220',
                    u'rbp': u'0x0000000000000020',
                    u'rbx': u'0x0000000000000020',
                    u'rcx': u'0x0000000000000000',
                    u'rdi': u'0x0000000100200218',
                    u'rdx': u'0x0000000000000000',
                    u'rip': u'0x000000010000e883',
                    u'rsi': u'0x0000000000000020',
                    u'rsp': u'0x00007fff5fbfc170'
                },
                u'trust': u'context'
            },
            {
                u'file': u'hg:hg.mozilla.org/releases/mozilla-release:'
                         'memory/mozjemalloc/jemalloc.c:44234f451065',
                u'frame': 1,
                u'function': u'je_realloc',
                u'function_offset': u'0x5a1',
                u'line': 4752,
                u'module': u'libmozglue.dylib',
                u'module_offset': u'0x2141',
                u'offset': u'0x100009141',
                u'trust': u'cfi'
            },
            {
                u'frame': 2,
                u'function': u'malloc_zone_realloc',
                u'function_offset': u'0x5b',
                u'module': u'libSystem.B.dylib',
                u'module_offset': u'0x8b7a',
                u'offset': u'0x7fff82a27b7a',
                u'trust': u'context'
            },
            {
                u'file': u'hg:hg.mozilla.org/releases/mozilla-release'
                         ':memory/mozjemalloc/jemalloc.c:44234f451065',
                u'frame': 1,
                u'function': u'je_realloc',
                u'function_offset': u'0x5a1',
                u'line': 4752,
                u'module': u'libmozglue.dylib',
                u'module_offset': u'0x2141',
                u'offset': u'0x100009141',
                u'trust': u'cfi'
            },
            {
                u'frame': 2,
                u'function': u'malloc_zone_realloc',
                u'function_offset': u'0x5b',
                u'module': u'libSystem.B.dylib',
                u'module_offset': u'0x8b7a',
                u'offset': u'0x7fff82a27b7a',
            }
        ],
    },
    u'status': u'OK',
    u'system_info': {
        u'cpu_arch': u'amd64',
        u'cpu_count': 2,
        u'cpu_info': u'family 6 model 23 stepping 10',
        u'os': u'Mac OS X',
        u'os_ver': u'10.6.8 10K549'
    },
    u'thread_count': 48,
    # ...

}
cannonical_stackwalker_output_str = ujson.dumps(cannonical_stackwalker_output)


class MyBreakpadStackwalkerRule2015(BreakpadStackwalkerRule2015):
    @contextmanager
    def _temp_raw_crash_json_file(self, raw_crash, crash_id):
        yield "%s.json" % raw_crash.uuid


class TestCrashingThreadRule(TestCase):

    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        return config

    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []
        processor_meta.quit_check = lambda: False

        return processor_meta

    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processed_crash.json_dump = copy.copy(cannonical_stackwalker_output)
        processor_meta = self.get_basic_processor_meta()

        rule = CrashingThreadRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processed_crash.crashedThread == 0

    def test_stuff_missing(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processed_crash.json_dump = {}
        processor_meta = self.get_basic_processor_meta()

        rule = CrashingThreadRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processed_crash.crashedThread is None
        assert processor_meta.processor_notes == ['MDSW did not identify the crashing thread']


cannonical_external_output = {
    "key": "value"
}
cannonical_external_output_str = ujson.dumps(cannonical_external_output)


class TestExternalProcessRule(TestCase):

    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.dump_field = 'upload_file_minidump'
        config.command_line = (
            'timeout -s KILL 30 {command_pathname} '
            '{dump_file_pathname} '
            '{processor_symbols_pathname_list} 2>/dev/null'
        )
        config.command_pathname = 'bogus_command'
        config.processor_symbols_pathname_list = (
            '/mnt/socorro/symbols/symbols_ffx,'
            '/mnt/socorro/symbols/symbols_sea,'
            '/mnt/socorro/symbols/symbols_tbrd,'
            '/mnt/socorro/symbols/symbols_sbrd,'
            '/mnt/socorro/symbols/symbols_os'
        )
        config.symbol_cache_path = '/mnt/socorro/symbols'
        config.result_key = 'bogus_command_result'
        config.return_code_key = 'bogus_command_return_code'
        return config

    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []
        processor_meta.quit_check = lambda: False

        return processor_meta

    def test_dot_save(self):
        d = {}
        ExternalProcessRule.dot_save(d, 'x', 1)
        assert d['x'] == 1

        ExternalProcessRule.dot_save(d, 'z.y', 10)
        assert d['z']['y'] == 10

        d['a'] = {}
        d['a']['b'] = {}
        ExternalProcessRule.dot_save(d, 'a.b.c', 100)
        assert d['a']['b']['c'] == 100

        dd = CDotDict()
        ExternalProcessRule.dot_save(dd, 'a.b.c.d.e.f', 1000)
        assert dd.a.b.c.d.e.f == 1000

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_everything_we_hoped_for(self, mocked_subprocess_module):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            cannonical_external_output_str
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = ExternalProcessRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        mocked_subprocess_module.Popen.assert_called_with(
            'timeout -s KILL 30 bogus_command a_fake_dump.dump '
            '/mnt/socorro/symbols/symbols_ffx,/mnt/socorro/symbols/'
            'symbols_sea,/mnt/socorro/symbols/symbols_tbrd,/mnt/socorro/'
            'symbols/symbols_sbrd,/mnt/socorro/symbols/symbols_os'
            ' 2>/dev/null',
            shell=True,
            stdout=mocked_subprocess_module.PIPE
        )

        assert processed_crash.bogus_command_result == cannonical_external_output

        assert processed_crash.bogus_command_return_code == 0

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_external_fails(self, mocked_subprocess_module):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = \
            mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = '{}'
        mocked_subprocess_handle.wait.return_value = 124

        rule = ExternalProcessRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processed_crash.bogus_command_result == {}
        assert processed_crash.bogus_command_return_code == 124
        assert processor_meta.processor_notes == []

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_external_fails_2(self, mocked_subprocess_module):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = int
        mocked_subprocess_handle.wait.return_value = -1

        rule = ExternalProcessRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processed_crash.bogus_command_result == {}
        assert processed_crash.bogus_command_return_code == -1
        expected = [
            'bogus_command output failed in '
            'json: Expected String or Unicode',
        ]
        assert processor_meta.processor_notes == expected


class TestBreakpadTransformRule2015(TestCase):

    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.dump_field = 'upload_file_minidump'
        config.command_line = (
            BreakpadStackwalkerRule2015.required_config .command_line.default
        )
        config.kill_timeout = 5
        config.command_pathname = '/bin/stackwalker'
        config.symbols_urls = 'https://localhost'
        config.symbol_cache_path = '/mnt/socorro/symbols'
        config.symbol_tmp_path = '/mnt/socorro/symbols'
        config.temporary_file_system_storage_path = '/tmp'
        return config

    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []
        processor_meta.quit_check = lambda: False

        return processor_meta

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_everything_we_hoped_for(self, mocked_subprocess_module):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            cannonical_stackwalker_output_str
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = BreakpadStackwalkerRule2015(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processed_crash.json_dump == cannonical_stackwalker_output
        assert processed_crash.mdsw_return_code == 0
        assert processed_crash.mdsw_status_string == "OK"
        assert processed_crash.success

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_stackwalker_fails(self, mocked_subprocess_module):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = \
            mocked_subprocess_module.Popen.return_value
        mocked_subprocess_handle.stdout.read.return_value = '{}\n'
        mocked_subprocess_handle.wait.return_value = 124

        rule = BreakpadStackwalkerRule2015(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processed_crash.json_dump == {}
        assert processed_crash.mdsw_return_code == 124
        assert processed_crash.mdsw_status_string == "unknown error"
        assert not processed_crash.success
        assert processor_meta.processor_notes == ["MDSW terminated with SIGKILL due to timeout"]

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_stackwalker_fails_2(self, mocked_subprocess_module):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = int
        mocked_subprocess_handle.wait.return_value = -1

        rule = BreakpadStackwalkerRule2015(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processed_crash.json_dump == {}
        assert processed_crash.mdsw_return_code == -1
        assert processed_crash.mdsw_status_string == "unknown error"
        assert not processed_crash.success
        command_line = rule.expand_commandline(
            dump_file_pathname='a_fake_dump.dump',
            raw_crash_pathname=(
                '/tmp/00000000-0000-0000-0000-000002140504.MainThread.TEMPORARY.json'
            )
        )
        expected = [
            '%s output failed in json: Expected String or Unicode' % config.command_pathname,
            'MDSW failed on \'%s\': unknown error' % command_line
        ]
        assert processor_meta.processor_notes == expected

    @patch('socorro.processor.breakpad_transform_rules.os.unlink')
    def test_temp_file_context(self, mocked_unlink):
        config = self.get_basic_config()

        rule = BreakpadStackwalkerRule2015(config)
        with rule._temp_raw_crash_json_file('foo.json', example_uuid):
            pass
        mocked_unlink.assert_called_once_with('/tmp/%s.MainThread.TEMPORARY.json' % example_uuid)
        mocked_unlink.reset_mock()

        try:
            with rule._temp_raw_crash_json_file('foo.json', example_uuid):
                raise KeyError('oops')
        except KeyError:
            pass
        mocked_unlink.assert_called_once_with('/tmp/%s.MainThread.TEMPORARY.json' % example_uuid)
        mocked_unlink.reset_mock()


class TestJitCrashCategorizeRule(TestCase):

    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.dump_field = 'upload_file_minidump'
        config.command_line = (
            JitCrashCategorizeRule.required_config.command_line.default
        )
        config.result_key = 'classifications.jit.category'
        config.return_code_key = 'classifications.jit.category_return_code'
        config.command_pathname = \
            '/data/socorro/stackwalk/bin/jit-crash-categorize'
        config.temporary_file_system_storage_path = '/tmp'
        return config

    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []
        processor_meta.quit_check = lambda: False

        return processor_meta

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_everything_we_hoped_for(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = CDotDict()
        processed_crash.product = 'Firefox'
        processed_crash.os_name = 'Windows 386'
        processed_crash.cpu_name = 'x86'
        processed_crash.signature = 'EnterBaseline'
        processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'not_module': 'not-a-module'}),
            DotDict({'module': 'a-module'})
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            'EXTRA-SPECIAL'
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = JitCrashCategorizeRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processor_meta.processor_notes == []
        assert processed_crash.classifications.jit.category == 'EXTRA-SPECIAL'
        assert processed_crash.classifications.jit.category_return_code == 0

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_success_all_types_of_signatures(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        base_processed_crash = CDotDict()
        base_processed_crash.product = 'Firefox'
        base_processed_crash.os_name = 'Windows 386'
        base_processed_crash.cpu_name = 'x86'
        base_processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'not_module': 'not-a-module'}),
            DotDict({'module': 'a-module'})
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            'EXTRA-SPECIAL'
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = JitCrashCategorizeRule(config)

        signatures = [
            'EnterBaseline',
            'moz::something | EnterBaseline',
            'EnterIon',
            'js::jit::FastInvoke',
            'Foo::Bar__js::jit::IonCannon',
            'Small | js::irregexp::ExecuteCode<T>',
        ]
        for signature in signatures:
            processed_crash = CDotDict(base_processed_crash)
            processed_crash.signature = signature

            # the call to be tested
            rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

            assert processor_meta.processor_notes == []
            assert processed_crash.classifications.jit.category == 'EXTRA-SPECIAL'
            assert processed_crash.classifications.jit.category_return_code == 0

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_subprocess_fail(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = CDotDict()
        processed_crash.product = 'Firefox'
        processed_crash.os_name = 'Windows 386'
        processed_crash.cpu_name = 'x86'
        processed_crash.signature = 'EnterBaseline'
        processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'not_module': 'not-a-module'}),
            DotDict({'module': 'a-module'})
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            None
        )
        mocked_subprocess_handle.wait.return_value = -1

        rule = JitCrashCategorizeRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert processor_meta.processor_notes == []
        assert processed_crash.classifications.jit.category is None
        assert processed_crash.classifications.jit.category_return_code == -1

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_wrong_os(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processed_crash.product = 'Firefox'
        processed_crash.os_name = 'MS-DOS'
        processed_crash.cpu_name = 'x86'
        processed_crash.signature = 'EnterBaseline'
        processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'not_module': 'not-a-module'}),
            DotDict({'module': 'a-module'})
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            'EXTRA-SPECIAL'
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = JitCrashCategorizeRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert 'classifications.jit.category' not in processed_crash
        assert 'classifications.jit.category_return_code' not in processed_crash

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_wrong_product(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processed_crash.product = 'Firefrenzy'
        processed_crash.os_name = 'Windows NT'
        processed_crash.cpu_name = 'x86'
        processed_crash.signature = 'EnterBaseline'
        processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'not_module': 'not-a-module'}),
            DotDict({'module': 'a-module'})
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            'EXTRA-SPECIAL'
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = JitCrashCategorizeRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert 'classifications.jit.category' not in processed_crash
        assert 'classifications.jit.category_return_code' not in processed_crash

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_wrong_cpu(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processed_crash.product = 'Firefox'
        processed_crash.os_name = 'Windows NT'
        processed_crash.cpu_name = 'VAX 750'
        processed_crash.signature = 'EnterBaseline'
        processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'not_module': 'not-a-module'}),
            DotDict({'module': 'a-module'})
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            'EXTRA-SPECIAL'
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = JitCrashCategorizeRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert 'classifications.jit.category' not in processed_crash
        assert 'classifications.jit.category_return_code' not in processed_crash

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_wrong_signature(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processed_crash.product = 'Firefox'
        processed_crash.os_name = 'Windows NT'
        processed_crash.cpu_name = 'x86'
        processed_crash.signature = 'this-is-not-a-JIT-signature'
        processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'not_module': 'not-a-module'}),
            DotDict({'module': 'a-module'})
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            'EXTRA-SPECIAL'
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = JitCrashCategorizeRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert 'classifications.jit.category' not in processed_crash
        assert 'classifications.jit.category_return_code' not in processed_crash

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_module_on_stack_top(self, mocked_subprocess_module):
        config = self.get_basic_config()
        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {config.dump_field: 'a_fake_dump.dump'}
        processed_crash = DotDict()
        processed_crash.product = 'Firefox'
        processed_crash.os_name = 'Windows NT'
        processed_crash.cpu_name = 'x86'
        processed_crash.signature = 'EnterBaseline'
        processed_crash['json_dump.crashing_thread.frames'] = [
            DotDict({'module': 'a-module'}),
            DotDict({'not_module': 'not-a-module'}),
        ]
        processor_meta = self.get_basic_processor_meta()

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.stdout.read.return_value = (
            'EXTRA-SPECIAL'
        )
        mocked_subprocess_handle.wait.return_value = 0

        rule = JitCrashCategorizeRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        assert 'classifications.jit.category' not in processed_crash
        assert 'classifications.jit.category_return_code' not in processed_crash

    def test_predicate_no_json_dump(self):
        config = self.get_basic_config()
        processed_crash = DotDict({
            'product': 'Firefox',
            'os_name': 'Windows NT',
            'cpu_name': 'x86',
            'signature': 'EnterBaseline',
        })

        rule = JitCrashCategorizeRule(config)

        assert rule._predicate({}, {}, processed_crash, {}) is True

    def test_predicate_no_crashing_thread(self):
        config = self.get_basic_config()
        processed_crash = DotDict({
            'product': 'Firefox',
            'os_name': 'Windows NT',
            'cpu_name': 'x86',
            'signature': 'EnterBaseline',

            # No "crashing_thread" key
            'json_dump': {},
        })

        rule = JitCrashCategorizeRule(config)

        assert rule._predicate({}, {}, processed_crash, {}) is True

    def test_predicate_no_frames(self):
        config = self.get_basic_config()
        processed_crash = DotDict({
            'product': 'Firefox',
            'os_name': 'Windows NT',
            'cpu_name': 'x86',
            'signature': 'EnterBaseline',

            'json_dump': {
                # No "frames" key
                'crashing_thread': {}
            },
        })

        rule = JitCrashCategorizeRule(config)

        assert rule._predicate({}, {}, processed_crash, {}) is True

    def test_predicate_empty_frames(self):
        config = self.get_basic_config()
        processed_crash = DotDict({
            'product': 'Firefox',
            'os_name': 'Windows NT',
            'cpu_name': 'x86',
            'signature': 'EnterBaseline',

            'json_dump': {
                'crashing_thread': {
                    # There is a "frames" key, but nothing in the list
                    'frames': []
                }
            },
        })

        rule = JitCrashCategorizeRule(config)

        assert rule._predicate({}, {}, processed_crash, {}) is True

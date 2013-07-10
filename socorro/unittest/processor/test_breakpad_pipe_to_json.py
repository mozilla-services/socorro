# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

import socorro.processor.breakpad_pipe_to_json as bpj

from socorro.lib.util import DotDict

cannonical_json_dump = {
    #"status": ,
    "system_info": {
        'os': 'Windows NT',
        'os_ver': '5.1.2600 Service Pack 2',
        "cpu_arch": 'x86',
        "cpu_info": 'GenuineIntel family 6 model 22 stepping 1',
        "cpu_count": 4
    },
    "crash_info": {
        "type": 'EXCEPTION_ACCESS_VIOLATION_READ',
        "crash_address": '0x676c',
        "crashing_thread": 0
    },
    "main_module": 0,
    "modules": [
        {
            "filename": 'firefox.exe',
            "version": '24.0.0.4925',
            "debug_file": 'firefox.pdb',
            "debug_id": '9FFDDF56AADE45988C759EF5ABAE53862',
            "base_addr": '0x00400000',
            "end_addr": '0x004e0fff',
        },
        {
            "filename": 'nss3.dll',
            "version": '24.0.0.4925',
            "debug_file": 'nss3.pdb',
            "debug_id": '30EAD90FEEBD495398D46EFA41814E261',
            "base_addr": '0x00a00000',
            "end_addr": '0x00bb5fff',
        },
        {
            "filename": 'mozjs.dll',
            "debug_file": 'mozjs.pdb',
            "debug_id": 'CC7AA5DA1FB144C4B40C2DF1B08709232',
            "base_addr": '0x00bd0000',
            "end_addr": '0x00ef9fff',
        },
        {
            "filename": 'mozalloc.dll',
            "version": '24.0.0.4925',
            "debug_file": 'mozalloc.pdb',
            "debug_id": 'F4C1BFD2BA3A487CA37EBF3D7E543F7B1',
            "base_addr": '0x01000000',
            "end_addr": '0x01005fff',
        },
        {
            "filename": 'gkmedias.dll',
            "version": '24.0.0.4925',
            "debug_file": 'gkmedias.pdb',
            "debug_id": '02FE96BEFEAE4570AA12E766CF2C8A361',
            "base_addr": '0x01010000',
            "end_addr": '0x01337fff',
        },
    ],
    "thread_count": 2,
    "threads": [
        {
            "frame_count": 13,
            "frames": [
                {
                    "frame": 0,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_1",
                    "file": "jsinferinlines.h:17666746e8cc",
                    "line": 1321,
                },
                {
                    "frame": 1,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_2",
                    "file": "jsobj.cpp:17666746e8cc",
                    "line": 1552,
                },
                {
                    "frame": 2,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_3",
                    "file": "CodeGenerator.cpp:17666746e8cc",
                    "line": 3119,
                },
                {
                    "frame": 3,
                    "module": "mozjs.dll",
                    "module_offset": "0xcc9d0",
                },
                {
                    "frame": 4,
                    "offset": "0x80b6fe0",
                },
                {
                    "frame": 5,
                    "offset": "0x3cf5ee6",
                },
                {
                    "frame": 6,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_7",
                    "file": "BaselineJIT.cpp:17666746e8cc",
                    "line": 105,
                },
                {
                    "frame": 7,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_8",
                    "file": "BaselineCompiler-shared.cpp:17666746e8cc",
                    "line": 71,
                },
                {
                    "frame": 8,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_9",
                    "file": "Ion.cpp:17666746e8cc",
                    "line": 1708,
                },
                {
                    "frame": 9,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_10",
                    "file": "Interpreter.cpp:17666746e8cc",
                    "line": 2586,
                },
                {
                    "frame": 10,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_11",
                    "file": "Interpreter.cpp:17666746e8cc",
                    "line": 438,
                },
                {
                    "frame": 11,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_12",
                    "file": "Interpreter.cpp:17666746e8cc",
                    "line": 622,
                },
                {
                    "frame": 12,
                    "module": "mozjs.dll",
                    "function": "bogus_sig_13",
                    "file": "Interpreter.cpp:17666746e8cc",
                    "line": 659,
                },
            ]
        },
        {
            "frame_count": 2,
            "frames": [
                {
                    "frame": 0,
                    "module": "lars_crash.dll",
                    "function": "ha_ha",
                    "file": "no source",
                    "line": 0,
                },
                {
                    "frame": 1,
                    "module": "lars_crash.dll",
                    "function": "ha_ha2",
                    "file": "no source",
                    "line": 0,
                },
            ]
        }

    ],
    "crashing_thread": {
        "threads_index": 0,
        "total_frames": 13,
        "frames": [
            {
                "frame": 0,
                "module": "mozjs.dll",
                "function": "bogus_sig_1",
                "file": "jsinferinlines.h:17666746e8cc",
                "line": 1321,
            },
            {
                "frame": 1,
                "module": "mozjs.dll",
                "function": "bogus_sig_2",
                "file": "jsobj.cpp:17666746e8cc",
                "line": 1552,
            },
            {
                "frame": 2,
                "module": "mozjs.dll",
                "function": "bogus_sig_3",
                "file": "CodeGenerator.cpp:17666746e8cc",
                "line": 3119,
            },
            {
                "frame": 3,
                "module": "mozjs.dll",
                "module_offset": "0xcc9d0",
            },
            {
                "frame": 4,
                "offset": "0x80b6fe0",
            },
            {
                "frame": 5,
                "offset": "0x3cf5ee6",
            },
            {
                "frame": 6,
                "module": "mozjs.dll",
                "function": "bogus_sig_7",
                "file": "BaselineJIT.cpp:17666746e8cc",
                "line": 105,
            },
            {
                "frame": 7,
                "module": "mozjs.dll",
                "function": "bogus_sig_8",
                "file": "BaselineCompiler-shared.cpp:17666746e8cc",
                "line": 71,
            },
            {
                "frame": 8,
                "module": "mozjs.dll",
                "function": "bogus_sig_9",
                "file": "Ion.cpp:17666746e8cc",
                "line": 1708,
            },
            {
                "frame": 9,
                "module": "mozjs.dll",
                "function": "bogus_sig_10",
                "file": "Interpreter.cpp:17666746e8cc",
                "line": 2586,
            },
        ]
    }
}


class TestCase(unittest.TestCase):
    def test_get(self):
        a_list = ['a', 'b', 'c']
        self.assertEqual(bpj._get(a_list, 0, None), 'a')
        self.assertEqual(bpj._get(a_list, 1, None), 'b')
        self.assertEqual(bpj._get(a_list, 2, None), 'c')
        self.assertEqual(bpj._get(a_list, 3, None), None)

    def test_get_int(self):
        a_list = ['a', '1', 'c']
        self.assertEqual(bpj._get_int(a_list, 0, None), None)
        self.assertEqual(bpj._get_int(a_list, 1, None), 1)
        self.assertEqual(bpj._get_int(a_list, 2, None), None)
        self.assertEqual(bpj._get_int(a_list, 3, None), None)


    def test_extract_OS_info(self):
        info = ['OS', 'Windows NT', '5.1.2600 Service Pack 2']
        d = DotDict()
        bpj._extract_OS_info(info, d)
        self.assertTrue('system_info' in d)
        self.assertEqual(
            d.system_info,
            {
                'os': 'Windows NT',
                'os_ver': '5.1.2600 Service Pack 2'
            }
        )

    def test_extract_OS_info_fail(self):
        info = ['OS',]
        d = DotDict()
        bpj._extract_OS_info(info, d)
        self.assertTrue('system_info' in d)
        self.assertEqual(d.system_info, {})

    def test_extract_CPU_info(self):
        info = ['CPU', 'x86', 'GenuineIntel family 6 model 22 stepping 1', 1]
        d = DotDict()
        bpj._extract_CPU_info(info, d)
        self.assertTrue('system_info' in d)
        self.assertEqual(
            d.system_info,
            {
                "cpu_arch": 'x86',
                "cpu_info": 'GenuineIntel family 6 model 22 stepping 1',
                "cpu_count": 1
            }
        )

    def test_extract_OS_and_CPU_info(self):
        info = ['OS', 'Windows NT', '5.1.2600 Service Pack 2']
        d = DotDict()
        bpj._extract_OS_info(info, d)
        info = ['CPU', 'x86', 'GenuineIntel family 6 model 22 stepping 1', 1]
        bpj._extract_CPU_info(info, d)
        self.assertTrue('system_info' in d)
        self.assertEqual(
            d.system_info,
            {
                'os': 'Windows NT',
                'os_ver': '5.1.2600 Service Pack 2',
                "cpu_arch": 'x86',
                "cpu_info": 'GenuineIntel family 6 model 22 stepping 1',
                "cpu_count": 1
            }
        )

    def test_extract_crash_info(self):
        info = ['Crash', 'EXCEPTION_ACCESS_VIOLATION_READ', '0x676c', 1]
        d = DotDict()
        crashing_thread = bpj._extract_crash_info(info, d)
        self.assertTrue('crash_info' in d)
        self.assertEqual(
            d.crash_info,
            {
                "type": 'EXCEPTION_ACCESS_VIOLATION_READ',
                "crash_address": '0x676c',
                "crashing_thread": 1
            }
        )
        self.assertEqual(crashing_thread, 1)

    def test_extract_module_info(self):
        info = ['Module', 'firefox.exe', '24.0.0.4925', 'firefox.pdb',
                '9FFDDF56AADE45988C759EF5ABAE53862', '0x00400000',
                '0x004e0fff', '1']
        d = DotDict()
        bpj._extract_module_info(info, d, 17)
        self.assertTrue('modules' in d)
        self.assertTrue(len(d.modules), 1)
        self.assertEqual(d.main_module, 17)
        self.assertEqual(
            d.modules[0],
            {
                "filename": 'firefox.exe',
                "version": '24.0.0.4925',
                "debug_file": 'firefox.pdb',
                "debug_id": '9FFDDF56AADE45988C759EF5ABAE53862',
                "base_addr": '0x00400000',
                "end_addr": '0x004e0fff',
            }
        )

    def test_extract_module_info_not_main(self):
        info = ['Module', 'firefloosy.exe', '24.0.0.4925', 'firefox.pdb',
                '9FFDDF56AADE45988C759EF5ABAE53862', '0x00400000',
                '0x004e0fff', '0']
        d = DotDict()
        bpj._extract_module_info(info, d, 17)
        self.assertTrue('modules' in d)
        self.assertTrue(len(d.modules), 1)
        self.assertTrue('main_module' not in d)
        self.assertEqual(
            d.modules[0],
            {
                "filename": 'firefloosy.exe',
                "version": '24.0.0.4925',
                "debug_file": 'firefox.pdb',
                "debug_id": '9FFDDF56AADE45988C759EF5ABAE53862',
                "base_addr": '0x00400000',
                "end_addr": '0x004e0fff',
            }
        )


    def test_extract_frame_inf(self):
        info = ['0', '12', 'msvcr100.dll', '_callthreadstartex',
                'f:\\src\\threadex.c', '314', '0x6']
        d = DotDict()
        bpj._extract_frame_info(info, d)
        self.assertTrue('threads' in d)
        self.assertEqual(len(d.threads), 1)
        self.assertEqual(
            d.threads[0],
            {
                "frame_count": 1,
                "frames": [
                    {
                        "frame": 12,
                        "module": 'msvcr100.dll',
                        "function": '_callthreadstartex',
                        "file": 'f:\\src\\threadex.c',
                        "line": 314,
                    }
                ]
            }
        )

    def test_extract_frame_info_frames_missing(self):
        info = ['4', '12', 'msvcr100.dll', '_callthreadstartex',
                'f:\\src\\threadex.c', '314', '0x6']
        d = DotDict()
        bpj._extract_frame_info(info, d)
        self.assertTrue('threads' in d)
        self.assertEqual(len(d.threads), 5)
        self.assertEqual(
            d.threads[4],
            {
                "frame_count": 1,
                "frames": [
                    {
                        "frame": 12,
                        "module": 'msvcr100.dll',
                        "function": '_callthreadstartex',
                        "file": 'f:\\src\\threadex.c',
                        "line": 314,
                    }
                ]
            }
        )



    def test_pipe_dump_to_json_dump(self):
        pipe_dump = [
            "OS|Windows NT|5.1.2600 Service Pack 2",
            "CPU|x86|GenuineIntel family 6 model 22 stepping 1|4",
            "Crash|EXCEPTION_ACCESS_VIOLATION_READ|0x676c|0",
            "Module|firefox.exe|24.0.0.4925|firefox.pdb|9FFDDF56AADE45988C759EF5ABAE53862|0x00400000|0x004e0fff|1",
            "Module|nss3.dll|24.0.0.4925|nss3.pdb|30EAD90FEEBD495398D46EFA41814E261|0x00a00000|0x00bb5fff|0",
            "Module|mozjs.dll||mozjs.pdb|CC7AA5DA1FB144C4B40C2DF1B08709232|0x00bd0000|0x00ef9fff|0",
            "Module|mozalloc.dll|24.0.0.4925|mozalloc.pdb|F4C1BFD2BA3A487CA37EBF3D7E543F7B1|0x01000000|0x01005fff|0",
            "Module|gkmedias.dll|24.0.0.4925|gkmedias.pdb|02FE96BEFEAE4570AA12E766CF2C8A361|0x01010000|0x01337fff|0",
            "",
            "0|0|mozjs.dll|bogus_sig_1|jsinferinlines.h:17666746e8cc|1321|0x0",
            "0|1|mozjs.dll|bogus_sig_2|jsobj.cpp:17666746e8cc|1552|0x2d",
            "0|2|mozjs.dll|bogus_sig_3|CodeGenerator.cpp:17666746e8cc|3119|0x13",
            "0|3|mozjs.dll||||0xcc9d0",
            "0|4|||||0x80b6fe0",
            "0|5|||||0x3cf5ee6",
            "0|6|mozjs.dll|bogus_sig_7|BaselineJIT.cpp:17666746e8cc|105|0x20",
            "0|7|mozjs.dll|bogus_sig_8|BaselineCompiler-shared.cpp:17666746e8cc|71|0x3d",
            "0|8|mozjs.dll|bogus_sig_9|Ion.cpp:17666746e8cc|1708|0x1b",
            "0|9|mozjs.dll|bogus_sig_10|Interpreter.cpp:17666746e8cc|2586|0x26",
            "0|10|mozjs.dll|bogus_sig_11|Interpreter.cpp:17666746e8cc|438|0x9",
            "0|11|mozjs.dll|bogus_sig_12|Interpreter.cpp:17666746e8cc|622|0x37",
            "0|12|mozjs.dll|bogus_sig_13|Interpreter.cpp:17666746e8cc|659|0x1b",
            "1|0|lars_crash.dll|ha_ha|no source|0|0x3|0x2|0x1",
            "1|1|lars_crash.dll|ha_ha2|no source|0|0x5|0x1|0x3",
        ]
        json_dump = bpj.pipe_dump_to_json_dump(pipe_dump)
        self.assertEqual(json_dump, cannonical_json_dump)


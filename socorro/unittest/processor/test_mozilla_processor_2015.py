import ujson

from configman import ConfigurationManager
from configman.dotdict import DotDict

from mock import Mock, patch
from nose.tools import eq_, ok_

from socorro.processor.mozilla_processor_2015 import (
    MozillaProcessorAlgorithm2015
)
from socorro.unittest.testbase import TestCase


thread_over_255_chars = {
    "frames": [
        {
            "file": "nsTerminator.cpp:604367e1fa5e",
            "frame": 0,
            "function": ("mozilla::`anonymous namespace::"
                         "RunWatchdog(void *)" + "a" * 255),
            "function_offset": "0x0",
            "line": 151,
            "module": "xul.dll",
            "module_offset": "0x783f2b",
            "offset": "0x67903f2b",
            "registers": {
                "eax": "0x0000003f",
                "ebp": "0x163ff96c",
                "ebx": "0x0cf44450",
                "ecx": "0x691e3698",
                "edi": "0x76d3f551",
                "edx": "0x01dc1010",
                "efl": "0x00000246",
                "eip": "0x67903f2b",
                "esi": "0x0000003f",
                "esp": "0x163ff968"
            },
            "trust": "context"
        }
    ]
}
stackwalker_output_str = ujson.dumps({
    "crash_info": {
        "address": "0x0",
        "crashing_thread": 0,
        "type": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS"
    },
    "status": "OK",
    "crashing_thread": thread_over_255_chars,
    "threads": [thread_over_255_chars],
    "system_info": {
        "os": "Windows NT",
        "cpu_arch": "x86"
    },
    "sensitive": {
        "exploitability": "high"
    },
})


class TestMozillaProcessorAlgorithm2015(TestCase):

    @patch('socorro.processor.breakpad_transform_rules.subprocess')
    def test_process_over_255_chars(self, mocked_subprocess_module):
        cm = ConfigurationManager(
            definition_source=(
                MozillaProcessorAlgorithm2015.get_required_config(),
            ),
            values_source_list=[]
        )
        config = cm.get_config()
        config.logger = Mock()
        config.processor_name = 'dwight'

        mocked_subprocess_handle = (
            mocked_subprocess_module.Popen.return_value
        )
        mocked_subprocess_handle.wait.return_value = 0
        mocked_subprocess_handle.stdout.read.return_value = (
            stackwalker_output_str
        )
        p = MozillaProcessorAlgorithm2015(config)
        raw_crash = DotDict({
            "uuid": "00000000-0000-0000-0000-000002140504",
            "CrashTime": "1336519554",
            "SecondsSinceLastCrash": "86985",
            "PluginHang": "1",
            "ProductName": "Firefox",
            "Version": "19",
            "BuildID": "20121031"
        })
        raw_dumps = {"upload_file_minidump": "a_fake_dump.dump"}

        processed_crash = p.process_crash(
            raw_crash,
            raw_dumps,
            DotDict()
        )

        ok_(processed_crash.success)
        eq_(processed_crash.processor_notes,
            'dwight; MozillaProcessorAlgorithm2015; '
            'SignatureTool: signature truncated due to length; '
            'SignatureTool: signature truncated due to length')
        ok_(processed_crash.signature.startswith('shutdownhang'))
        eq_(len(processed_crash.signature), 255)

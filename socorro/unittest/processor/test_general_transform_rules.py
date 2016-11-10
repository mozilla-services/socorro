# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy

from nose.tools import eq_, ok_
from mock import Mock

from configman.dotdict import DotDict as CDotDict

from socorro.unittest.testbase import TestCase
from socorro.lib.util import DotDict
from socorro.processor.general_transform_rules import (
    IdentifierRule,
    CPUInfoRule,
    OSInfoRule,
)

canonical_standard_raw_crash = DotDict({
    "uuid": '00000000-0000-0000-0000-000002140504',
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

canonical_processed_crash = DotDict({
    "json_dump" : {
        "system_info" : {
            "os_ver" : "6.1.7601 Service Pack 1 ",
            "cpu_count" : 4,
            "cpu_info" : "GenuineIntel family 6 model 42 stepping 7",
            "cpu_arch" : "x86",
            "os" : "Windows NT"
        },
    }
})


#==============================================================================
class TestIdentifierRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = IdentifierRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.crash_id, "00000000-0000-0000-0000-000002140504")
        eq_(processed_crash.uuid, "00000000-0000-0000-0000-000002140504")

        # raw crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)

    #--------------------------------------------------------------------------
    def test_stuff_missing(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        del raw_crash.uuid
        expected_raw_crash = copy.copy(raw_crash)

        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = IdentifierRule(config)

        # the call to be tested
        result = rule.act(
            raw_crash,
            raw_dumps,
            processed_crash,
            processor_meta
        )

        eq_(result, (True, False))

        # raw crash should be unchanged
        eq_(raw_crash, expected_raw_crash)


#==============================================================================
class TestCPUInfoRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = copy.copy(canonical_processed_crash)
        processor_meta = self.get_basic_processor_meta()

        rule = CPUInfoRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.cpu_info,
            "GenuineIntel family 6 model 42 stepping 7 | 4"
        )
        eq_(processed_crash.cpu_name, 'x86')

        # raw crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)

    #--------------------------------------------------------------------------
    def test_stuff_missing(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)

        raw_dumps = {}
        system_info = copy.copy(
            canonical_processed_crash['json_dump']['system_info']
        )
        del system_info['cpu_count']
        processed_crash = DotDict()
        processed_crash.json_dump = {
            'system_info': system_info
        }

        processor_meta = self.get_basic_processor_meta()

        rule = CPUInfoRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.cpu_info,
            "GenuineIntel family 6 model 42 stepping 7"
        )
        eq_(processed_crash.cpu_name, 'x86')

        # raw crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)


#==============================================================================
class TestOSInfoRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = copy.copy(canonical_processed_crash)
        processor_meta = self.get_basic_processor_meta()

        rule = OSInfoRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.os_name, "Windows NT")
        eq_(processed_crash.os_version, "6.1.7601 Service Pack 1")

        # raw crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)

    #--------------------------------------------------------------------------
    def test_stuff_missing(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)

        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = OSInfoRule(config)

        # the call to be tested
        r = rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(r, (True, False))

        # processed crash should have empties
        expected = DotDict()
        expected.os_version = ''
        expected.os_name = ''
        eq_(processed_crash, expected)

        # raw crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)



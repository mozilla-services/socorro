# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import re
import json
from StringIO import StringIO

from mock import Mock, patch, call
from nose.tools import eq_, ok_

from configman.dotdict import DotDict as CDotDict

from socorro.unittest.testbase import TestCase
from socorrolib.lib.util import DotDict
from socorrolib.lib.datetimeutil import datetimeFromISOdateString
from socorro.processor.mozilla_transform_rules import (
    ProductRule,
    UserDataRule,
    EnvironmentRule,
    PluginRule,
    AddonsRule,
    DatesAndTimesRule,
    JavaProcessRule,
    OutOfMemoryBinaryRule,
    ProductRewrite,
    setup_product_id_map,
    ESRVersionRewrite,
    PluginContentURL,
    PluginUserComment,
    ExploitablityRule,
    FlashVersionRule,
    Winsock_LSPRule,
    TopMostFilesRule,
    MissingSymbolsRule,
    BetaVersionRule,
    OSPrettyVersionRule,
    ThemePrettyNameRule,
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

cannonical_processed_crash = DotDict({
    'json_dump': {
        'sensitive': {
            'exploitability': 'high'
        },
        'modules': [
            {
                "end_addr": "0x12e6000",
                "filename": "plugin-container.exe",
                "version": "26.0.0.5084",
                "debug_id": "8385BD80FD534F6E80CF65811735A7472",
                "debug_file": "plugin-container.pdb",
                "base_addr": "0x12e0000"
            },
            {
                "end_addr": "0x12e6000",
                "filename": "plugin-container.exe",
                "version": "26.0.0.5084",
                "debug_id": "8385BD80FD534F6E80CF65811735A7472",
                "debug_file": "plugin-container.pdb",
                "base_addr": "0x12e0000"
            },
            {
                "end_addr": "0x12e6000",
                "filename": "FlashPlayerPlugin9_1_3_08.exe",
                "debug_id": "8385BD80FD534F6E80CF65811735A7472",
                "debug_file": "plugin-container.pdb",
                "base_addr": "0x12e0000"
            },
            {
                "end_addr": "0x12e6000",
                "filename": "plugin-container.exe",
                "version": "26.0.0.5084",
                "debug_id": "8385BD80FD534F6E80CF65811735A7472",
                "debug_file": "plugin-container.pdb",
                "base_addr": "0x12e0000"
            },
        ]
    }
})


#==============================================================================
class TestProductRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        # does it even instantiate?
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ProductRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.product, "Firefox")
        eq_(processed_crash.version, "12.0")
        eq_(
            processed_crash.productid,
            "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}"
        )
        eq_(processed_crash.distributor, "Mozilla")
        eq_(processed_crash.distributor_version, "12.0")
        eq_(processed_crash.release_channel, "release")
        eq_(processed_crash.build, "20120420145725")

    #--------------------------------------------------------------------------
    def test_stuff_missing(self):
        # does it even instantiate?
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        del raw_crash.Version
        del raw_crash.Distributor
        del raw_crash.Distributor_version
        del raw_crash.ReleaseChannel

        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ProductRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.product, "Firefox")
        eq_(processed_crash.version, "")
        eq_(
            processed_crash.productid,
            "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}"
        )
        eq_(processed_crash.distributor, None)
        eq_(processed_crash.distributor_version, None)
        eq_(processed_crash.release_channel, "")
        eq_(processed_crash.build, "20120420145725")


#==============================================================================
class TestUserDataRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

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

        rule = UserDataRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.url, "http://www.mozilla.com")
        eq_(processed_crash.user_comments, "why did my browser crash?  #fail")
        eq_(processed_crash.email, "noreply@mozilla.com")
        eq_(processed_crash.user_id, "")

    #--------------------------------------------------------------------------
    def test_stuff_missing(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        del raw_crash.URL
        del raw_crash.Comments
        del raw_crash.Email

        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = UserDataRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.url, None)
        eq_(processed_crash.user_comments, None)
        eq_(processed_crash.email, None)


#==============================================================================
class TestEnvironmentRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

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

        rule = EnvironmentRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.app_notes, raw_crash.Notes)

    #--------------------------------------------------------------------------
    def test_stuff_missing(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        del raw_crash.Notes

        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = EnvironmentRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.app_notes, "")


#==============================================================================
class TestPluginRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_plugin_hang(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.PluginHang = 1
        raw_crash.Hang = 0
        raw_crash.ProcessType = 'plugin'
        raw_crash.PluginFilename = 'x.exe'
        raw_crash.PluginName = 'X'
        raw_crash.PluginVersion = '0.0'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = PluginRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.hangid,
            'fake-00000000-0000-0000-0000-000002140504'
        )
        eq_(processed_crash.hang_type, -1)
        eq_(processed_crash.process_type, 'plugin')
        eq_(processed_crash.PluginFilename, 'x.exe')
        eq_(processed_crash.PluginName, 'X')
        eq_(processed_crash.PluginVersion, '0.0')

    #--------------------------------------------------------------------------
    def test_browser_hang(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.Hang = 1
        raw_crash.ProcessType = 'browser'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = PluginRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.hangid, None)
        eq_(processed_crash.hang_type, 1)
        eq_(processed_crash.process_type, 'browser')
        ok_('PluginFilename' not in processed_crash)
        ok_('PluginName' not in processed_crash)
        ok_('PluginVersion' not in processed_crash)


#==============================================================================
class TestAddonsRule(TestCase):
    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.collect_addon = True
        config.chatty = False

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_addon_split_or_warn(self):
        config = self.get_basic_config()

        test_list = (
            "part1:part2",
            "part1-with-no-part2"
        )
        expected_output = (
            (('part1', 'part2'), []),
            (
                ('part1-with-no-part2', ''),
                ['add-on "part1-with-no-part2" is a bad name and/or version']
            )
        )
        an_addon_rule_instance = AddonsRule(config)
        for test_input, (expected_result, expected_notes) in zip(
            test_list, expected_output
        ):
            processor_notes = []
            result = an_addon_rule_instance._addon_split_or_warn(
                test_input,
                processor_notes
            )
            eq_(result, expected_result)
            eq_(processor_notes, expected_notes)

    #--------------------------------------------------------------------------
    def test_action_nothing_unexpected(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        addons_rule = AddonsRule(config)

        # the call to be tested
        addons_rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        # the raw crash & raw_dumps should not have changed
        eq_(raw_crash, canonical_standard_raw_crash)
        eq_(raw_dumps, {})

        expected_addon_list = [
            ('adblockpopups@jessehakanen.net', '0.3'),
            ('dmpluginff@westbyte.com', '1,4.8'),
            ('firebug@software.joehewitt.com', '1.9.1'),
            ('killjasmin@pierros14.com', '2.4'),
            ('support@surfanonymous-free.com', '1.0'),
            ('uploader@adblockfilters.mozdev.org', '2.1'),
            ('{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}', '20111107'),
            ('{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}', '2.0.3'),
            ('anttoolbar@ant.com', '2.4.6.4'),
            ('{972ce4c6-7e08-4474-a285-3208198ce6fd}', '12.0'),
            ('elemhidehelper@adblockplus.org', '1.2.1')
        ]
        eq_(processed_crash.addons, expected_addon_list)
        ok_(processed_crash.addons_checked)

    #--------------------------------------------------------------------------
    def test_action_colon_in_addon_version(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash['Add-ons'] = 'adblockpopups@jessehakanen.net:0:3:1'
        raw_crash['EMCheckCompatibility'] = 'Nope'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        addons_rule = AddonsRule(config)

        addons_rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        expected_addon_list = [
            ('adblockpopups@jessehakanen.net', '0:3:1'),
        ]
        eq_(processed_crash.addons, expected_addon_list)
        ok_(not processed_crash.addons_checked)

    #--------------------------------------------------------------------------
    def test_action_addon_is_nonsense(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash['Add-ons'] = 'naoenut813teq;mz;<[`19ntaotannn8999anxse `'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        addons_rule = AddonsRule(config)

        addons_rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        expected_addon_list = [
            ('naoenut813teq;mz;<[`19ntaotannn8999anxse `', ''),
        ]
        eq_(processed_crash.addons, expected_addon_list)
        ok_(processed_crash.addons_checked)


#==============================================================================
class TestDatesAndTimesRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_get_truncate_or_warn(self):
        raw_crash = copy.copy(canonical_standard_raw_crash)
        processor_notes = []
        eq_(
            DatesAndTimesRule._get_truncate_or_warn(
                raw_crash,
                'submitted_timestamp',
                processor_notes,
                '',
                50
            ),
            "2012-05-08T23:26:33.454482+00:00"
        )
        eq_(processor_notes, [])

        processor_notes = []
        eq_(
            DatesAndTimesRule._get_truncate_or_warn(
                raw_crash,
                'terrible_timestamp',
                processor_notes,
                "2012-05-08T23:26:33.454482+00:00",
                '50'
            ),
            "2012-05-08T23:26:33.454482+00:00"
        )
        eq_(processor_notes, ['WARNING: raw_crash missing terrible_timestamp'])

        raw_crash.submitted_timestamp = 17
        processor_notes = []
        eq_(
            DatesAndTimesRule._get_truncate_or_warn(
                raw_crash,
                'submitted_timestamp',
                processor_notes,
                "2012-05-08T23:26:33.454482+00:00",
                '50'
            ),
            "2012-05-08T23:26:33.454482+00:00"
        )
        # The warning message you get comes from a ValueError
        # which is phrased differently in python 2.6 compared to 2.7.
        # So we need to expect different things depend on python version.
        # print repr(processor_notes[0])
        try:
            42[:1]
        except TypeError as err:
            type_error_value = str(err)
        eq_(
            processor_notes,
            [
                "WARNING: raw_crash[submitted_timestamp] contains unexpected "
                "value: 17; %s" % type_error_value
            ]
        )

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 1336519554)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('2012-05-08 23:25:54+00:00')
        )
        eq_(processed_crash.install_age, 1079662)
        eq_(processed_crash.uptime, 20116)
        eq_(processed_crash.last_crash, 86985)

    #--------------------------------------------------------------------------
    def test_bad_timestamp(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.timestamp = 'hi there'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 1336519554)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('2012-05-08 23:25:54+00:00')
        )
        eq_(processed_crash.install_age, 1079662)
        eq_(processed_crash.uptime, 20116)
        eq_(processed_crash.last_crash, 86985)

        eq_(
            processor_meta.processor_notes,
            ['non-integer value of "timestamp"']
        )

    #--------------------------------------------------------------------------
    def test_bad_timestamp_and_no_crash_time(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.timestamp = 'hi there'
        del raw_crash.CrashTime
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 0)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('1970-01-01 00:00:00+00:00')
        )
        eq_(processed_crash.install_age, -1335439892)
        eq_(processed_crash.uptime, 0)
        eq_(processed_crash.last_crash, 86985)

        eq_(
            processor_meta.processor_notes,
            [
                'non-integer value of "timestamp"',
                'WARNING: raw_crash missing CrashTime'
            ]
        )

    #--------------------------------------------------------------------------
    def test_no_startup_time_bad_timestamp(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.timestamp = 'hi there'
        del raw_crash.StartupTime
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 1336519554)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('2012-05-08 23:25:54+00:00')
        )
        eq_(processed_crash.install_age, 1079662)
        eq_(processed_crash.uptime, 0)
        eq_(processed_crash.last_crash, 86985)

        eq_(
            processor_meta.processor_notes,
            [
                'non-integer value of "timestamp"',
            ]
        )

    #--------------------------------------------------------------------------
    def test_no_startup_time(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        del raw_crash.StartupTime
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 1336519554)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('2012-05-08 23:25:54+00:00')
        )
        eq_(processed_crash.install_age, 1079662)
        eq_(processed_crash.uptime, 0)
        eq_(processed_crash.last_crash, 86985)

        eq_(processor_meta.processor_notes, [])

    #--------------------------------------------------------------------------
    def test_bad_startup_time(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.StartupTime = 'feed the goats'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 1336519554)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('2012-05-08 23:25:54+00:00')
        )
        eq_(processed_crash.install_age, 1079662)
        eq_(processed_crash.uptime, 1336519554)
        eq_(processed_crash.last_crash, 86985)

        eq_(
            processor_meta.processor_notes,
            [
                'non-integer value of "StartupTime"',
            ]
        )

    #--------------------------------------------------------------------------
    def test_bad_install_time(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.InstallTime = 'feed the goats'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 1336519554)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('2012-05-08 23:25:54+00:00')
        )
        eq_(processed_crash.install_age, 1336519554)
        eq_(processed_crash.uptime, 20116)
        eq_(processed_crash.last_crash, 86985)

        eq_(
            processor_meta.processor_notes,
            [
                'non-integer value of "InstallTime"',
            ]
        )

    #--------------------------------------------------------------------------
    def test_bad_seconds_since_last_crash(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.SecondsSinceLastCrash = 'feed the goats'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = DatesAndTimesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(
            processed_crash.submitted_timestamp,
            datetimeFromISOdateString(raw_crash.submitted_timestamp)
        )
        eq_(
            processed_crash.date_processed,
            processed_crash.submitted_timestamp
        )
        eq_(processed_crash.crash_time, 1336519554)
        eq_(
            processed_crash.client_crash_date,
            datetimeFromISOdateString('2012-05-08 23:25:54+00:00')
        )
        eq_(processed_crash.install_age, 1079662)
        eq_(processed_crash.uptime, 20116)
        eq_(processed_crash.last_crash, None)

        eq_(
            processor_meta.processor_notes,
            [
                'non-integer value of "SecondsSinceLastCrash"',
            ]
        )


#==============================================================================
class TestJavaProcessRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

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
        raw_crash.JavaStackTrace = "this is a Java Stack trace"
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = JavaProcessRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.java_stack_trace, raw_crash.JavaStackTrace)

    #--------------------------------------------------------------------------
    def test_stuff_missing(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        del raw_crash.Notes

        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = JavaProcessRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.java_stack_trace, None)


#==============================================================================
class TestOutOfMemoryBinaryRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_extract_memory_info(self):
        config = CDotDict()
        config.max_size_uncompressed = 1024
        config.logger = Mock()

        processor_meta = self.get_basic_processor_meta()

        with patch(
            'socorro.processor.mozilla_transform_rules.gzip_open'
        ) as mocked_gzip_open:
            mocked_gzip_open.return_value = StringIO(
                json.dumps({'myserious': ['awesome', 'memory']})
            )
            rule = OutOfMemoryBinaryRule(config)
            memory = rule._extract_memory_info(
                'a_pathname',
                processor_meta.processor_notes
            )
            mocked_gzip_open.assert_called_with('a_pathname', 'rb')
            eq_(memory, {'myserious': ['awesome', 'memory']})

    #--------------------------------------------------------------------------
    def test_extract_memory_info_too_big(self):
        config = CDotDict()
        config.max_size_uncompressed = 5
        config.logger = Mock()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.JavaStackTrace = "this is a Java Stack trace"
        raw_dumps = {'memory_report': 'a_pathname'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        with patch(
            'socorro.processor.mozilla_transform_rules.gzip_open'
        ) as mocked_gzip_open:

            opened = Mock()
            opened.read.return_value = json.dumps({
                'some': 'notveryshortpieceofjson'
            })

            def gzip_open(filename, mode):
                assert mode == 'rb'
                return opened

            mocked_gzip_open.side_effect = gzip_open
            rule = OutOfMemoryBinaryRule(config)
            memory = rule._extract_memory_info(
                'a_pathname',
                processor_meta.processor_notes
            )
            expected_error_message = (
                "Uncompressed memory info too large %d (max: %s)" % (
                    35,
                    config.max_size_uncompressed,
                )
            )
            eq_(
                memory,
                {"ERROR": expected_error_message}
            )
            eq_(
                processor_meta.processor_notes,
                [expected_error_message]
            )
            opened.close.assert_called_with()

            rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
            ok_('memory_report' not in processed_crash)
            eq_(
                processed_crash.memory_report_error,
                expected_error_message
            )

    #--------------------------------------------------------------------------
    def test_extract_memory_info_with_trouble(self):
        config = CDotDict()
        config.max_size_uncompressed = 1024
        config.logger = Mock()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.JavaStackTrace = "this is a Java Stack trace"
        raw_dumps = {'memory_report': 'a_pathname'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        with patch(
            'socorro.processor.mozilla_transform_rules.gzip_open'
        ) as mocked_gzip_open:
            mocked_gzip_open.side_effect = IOError
            rule = OutOfMemoryBinaryRule(config)
            memory = rule._extract_memory_info(
                'a_pathname',
                processor_meta.processor_notes
            )

            eq_(
                memory,
                {"ERROR": "error in gzip for a_pathname: IOError()"}
            )
            eq_(
                processor_meta.processor_notes,
                ["error in gzip for a_pathname: IOError()"]
            )

            rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
            ok_('memory_report' not in processed_crash)
            eq_(
                processed_crash.memory_report_error,
                'error in gzip for a_pathname: IOError()'
            )

    #--------------------------------------------------------------------------
    def test_extract_memory_info_with_json_trouble(self):
        config = CDotDict()
        config.max_size_uncompressed = 1024
        config.logger = Mock()
        config.chatty = False

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.JavaStackTrace = "this is a Java Stack trace"
        raw_dumps = {'memory_report': 'a_pathname'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        with patch(
            'socorro.processor.mozilla_transform_rules.gzip_open'
        ) as mocked_gzip_open:
            with patch(
                'socorro.processor.mozilla_transform_rules.json_loads'
            ) as mocked_json_loads:
                mocked_json_loads.side_effect = ValueError

                rule = OutOfMemoryBinaryRule(config)
                memory = rule._extract_memory_info(
                    'a_pathname',
                    processor_meta.processor_notes
                )
                mocked_gzip_open.assert_called_with('a_pathname', 'rb')
                eq_(
                    memory,
                    {"ERROR": "error in json for a_pathname: ValueError()"}
                )
                eq_(
                    processor_meta.processor_notes,
                    ["error in json for a_pathname: ValueError()"]
                )
                mocked_gzip_open.return_value.close.assert_called_with()

                rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
                ok_('memory_report' not in processed_crash)
                eq_(
                    processed_crash.memory_report_error,
                    'error in json for a_pathname: ValueError()'
                )

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.JavaStackTrace = "this is a Java Stack trace"
        raw_dumps = {'memory_report': 'a_pathname'}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        class MyOutOfMemoryBinaryRule(OutOfMemoryBinaryRule):
            @staticmethod
            def _extract_memory_info(dump_pathname, processor_notes):
                eq_(dump_pathname, raw_dumps['memory_report'])
                eq_(processor_notes, [])
                return 'mysterious-awesome-memory'

        with patch(
            'socorro.processor.mozilla_transform_rules'
            '.temp_file_context'
        ):
            rule = MyOutOfMemoryBinaryRule(config)

            # the call to be tested
            rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

            eq_(processed_crash.memory_report, 'mysterious-awesome-memory')

    #--------------------------------------------------------------------------
    def test_this_is_not_the_crash_you_are_looking_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.JavaStackTrace = "this is a Java Stack trace"
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = OutOfMemoryBinaryRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        ok_('memory_report' not in processed_crash)


#==============================================================================
class TestProductRewrite(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.collect_addon = True
        config.chatty = False

        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_setup_product_id_map(self):
        # does it even instantiate?
        config = self.get_basic_config()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()
        config.transaction_executor_class.return_value.return_value = (
            ('FennecAndroid', '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}', True),
            ('Chrome', '{ec8030f7-c20a-464f-9b0e-13b3a9e97384}', True),
            ('Safari', '{ec8030f7-c20a-464f-9b0e-13c3a9e97384}', True),
        )

        product_id_map = setup_product_id_map(
            config,
            config,
            []
        )

        eq_(
            product_id_map,
            {
                '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}': {
                    'product_name': 'FennecAndroid',
                    'rewrite': True,
                },
                '{ec8030f7-c20a-464f-9b0e-13b3a9e97384}': {
                    'product_name': 'Chrome',
                    'rewrite': True,
                },
                '{ec8030f7-c20a-464f-9b0e-13c3a9e97384}': {
                    'product_name': 'Safari',
                    'rewrite': True,
                },
            }
        )

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()
        config.transaction_executor_class.return_value.return_value = (
            ('FennecAndroid', '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}', True),
            ('Chrome', '{ec8030f7-c20a-464f-9b0e-13b3a9e97384}', True),
            ('Safari', '{ec8030f7-c20a-464f-9b0e-13c3a9e97384}', True),
        )

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ProductRewrite(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.ProductName, 'FennecAndroid')

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())

    #--------------------------------------------------------------------------
    def test_this_is_not_the_crash_you_are_looking_for(self):
        config = self.get_basic_config()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()
        config.transaction_executor_class.return_value.return_value = (
            ('FennecAndroid', '{ec8030f7-c20a-464f-9b0e-13d3a9e97384}', True),
            ('Chrome', '{ec8030f7-c20a-464f-9b0e-13b3a9e97384}', True),
            ('Safari', '{ec8030f7-c20a-464f-9b0e-13c3a9e97384}', True),
        )

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ProductRewrite(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.ProductName, 'Firefox')

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())


#==============================================================================
class TestESRVersionRewrite(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

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
        raw_crash.ReleaseChannel = 'esr'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ESRVersionRewrite(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.Version, "12.0esr")

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())

    #--------------------------------------------------------------------------
    def test_this_is_not_the_crash_you_are_looking_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.ReleaseChannel = 'not_esr'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ESRVersionRewrite(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.Version, "12.0")

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())

    #--------------------------------------------------------------------------
    def test_this_is_really_broken(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.ReleaseChannel = 'esr'
        del raw_crash.Version
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ESRVersionRewrite(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        ok_("Version" not in raw_crash)
        eq_(
            processor_meta.processor_notes,
            ['"Version" missing from esr release raw_crash']
        )

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())


#==============================================================================
class TestPluginContentURL(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

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
        raw_crash.PluginContentURL = 'http://mozilla.com'
        raw_crash.URL = 'http://google.com'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = PluginContentURL(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.URL, "http://mozilla.com")

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())

    #--------------------------------------------------------------------------
    def test_this_is_not_the_crash_you_are_looking_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.URL = 'http://google.com'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = PluginContentURL(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.URL, "http://google.com")

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())


#==============================================================================
class TestPluginUserComment(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

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
        raw_crash.PluginUserComment = 'I hate it when this happens'
        raw_crash.Comments = 'I wrote something here, too'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = PluginUserComment(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.Comments, 'I hate it when this happens')

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())

    #--------------------------------------------------------------------------
    def test_this_is_not_the_crash_you_are_looking_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_crash.Comments = 'I wrote something here'
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = PluginUserComment(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(raw_crash.Comments, 'I wrote something here')

        # processed_crash should be unchanged
        eq_(processed_crash, DotDict())


#==============================================================================
class TestExploitablityRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False

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
        processed_crash = copy.copy(cannonical_processed_crash)
        processor_meta = self.get_basic_processor_meta()

        rule = ExploitablityRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.exploitability, 'high')

        # raw_crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)

    #--------------------------------------------------------------------------
    def test_this_is_not_the_crash_you_are_looking_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ExploitablityRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.exploitability, 'unknown')

        # raw_crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)


#==============================================================================
class TestFlashVersionRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False
        config.flash_re = re.compile(
            FlashVersionRule.required_config.flash_re.default
        )
        config.known_flash_identifiers = (
            FlashVersionRule.required_config.known_flash_identifiers.default
        )
        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_get_flash_version(self):
        config = self.get_basic_config()

        rule = FlashVersionRule(config)

        eq_(
            rule._get_flash_version(
                filename='NPSWF32_1_2_3.dll',
                version='1.2.3'),
            '1.2.3'
        )
        eq_(
            rule._get_flash_version(
                filename='NPSWF32_1_2_3.dll',
            ),
            '1.2.3'
        )

        eq_(
            rule._get_flash_version(
                filename='FlashPlayerPlugin_2_3_4.exe',
                version='2.3.4'),
            '2.3.4'
        )
        eq_(
            rule._get_flash_version(
                filename='FlashPlayerPlugin_2_3_4.exe',
            ),
            '2.3.4'
        )

        eq_(
            rule._get_flash_version(
                filename='libflashplayer3.4.5.so',
                version='3.4.5'),
            '3.4.5'
        )
        eq_(
            rule._get_flash_version(
                filename='libflashplayer3.4.5.so',
            ),
            '3.4.5'
        )

        eq_(
            rule._get_flash_version(
                filename='Flash Player-',
                version='4.5.6'),
            '4.5.6'
        )
        eq_(
            rule._get_flash_version(
                filename='Flash Player-.4.5.6',
            ),
            '.4.5.6'
        )

        eq_(
            rule._get_flash_version(
                filename='Flash Player-',
                version='.4.5.6',
                debug_id='83CF4DC03621B778E931FC713889E8F10'
            ),
            '.4.5.6'
        )
        eq_(
            rule._get_flash_version(
                filename='Flash Player-.4.5.6',
                debug_id='83CF4DC03621B778E931FC713889E8F10'
            ),
            '.4.5.6'
        )
        eq_(
            rule._get_flash_version(
                filename='Flash Player-',
                debug_id='83CF4DC03621B778E931FC713889E8F10'
            ),
            '9.0.16.0'
        )

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = copy.copy(cannonical_processed_crash)
        processor_meta = self.get_basic_processor_meta()

        rule = FlashVersionRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.flash_version, '9.1.3.08')

        # raw_crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)


#==============================================================================
class TestWinsock_LSPRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False
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
        raw_crash.Winsock_LSP = 'really long string'
        expected_raw_crash = copy.copy(raw_crash)
        raw_dumps = {}
        processed_crash = copy.copy(cannonical_processed_crash)
        processor_meta = self.get_basic_processor_meta()

        rule = Winsock_LSPRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.Winsock_LSP, 'really long string')

        # raw_crash should be unchanged
        eq_(raw_crash, expected_raw_crash)

    #--------------------------------------------------------------------------
    def test_missing_key(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        del raw_crash.Winsock_LSP
        expected_raw_crash = copy.copy(raw_crash)
        raw_dumps = {}
        processed_crash = copy.copy(cannonical_processed_crash)
        processor_meta = self.get_basic_processor_meta()

        rule = Winsock_LSPRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.Winsock_LSP, None)

        # raw_crash should be unchanged
        eq_(raw_crash, expected_raw_crash)


#==============================================================================
class TestTopMostFilesRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False
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
        processed_crash.json_dump = {
            'crash_info': {
                'crashing_thread': 0
            },
            'crashing_thread': {
                'frames': [
                    {
                        'source': 'not-the-right-file.dll'
                    },
                    {
                        'file': 'not-the-right-file.cpp'
                    },
                ]
            },
            'threads': [
                {
                    'frames': [
                        {
                            'source': 'dwight.dll'
                        },
                        {
                            'file': 'wilma.cpp'
                        },
                    ]
                },
            ]
        }

        processor_meta = self.get_basic_processor_meta()

        rule = TopMostFilesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.topmost_filenames, 'wilma.cpp')

        # raw_crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)

    #--------------------------------------------------------------------------
    def test_missing_key(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        expected_raw_crash = copy.copy(raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = TopMostFilesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.topmost_filenames, None)

        # raw_crash should be unchanged
        eq_(raw_crash, expected_raw_crash)

    #--------------------------------------------------------------------------
    def test_missing_key_2(self):
        config = self.get_basic_config()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processed_crash.json_dump = {
            'crashing_thread': {
                'frames': [
                    {
                        'filename': 'dwight.dll'
                    },
                    {
                        'filename': 'wilma.cpp'
                    }
                ]
            }
        }

        processor_meta = self.get_basic_processor_meta()

        rule = TopMostFilesRule(config)

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        eq_(processed_crash.topmost_filenames, None)

        # raw_crash should be unchanged
        eq_(raw_crash, canonical_standard_raw_crash)


#==============================================================================
class TestMissingSymbols(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False
        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processed_crash.date_processed = '2014-12-31'
        processed_crash.json_dump = {
            'modules': [
                {
                    "debug_id": "ABCDEFG",
                    "debug_file": "some-file.pdb",
                    "missing_symbols": True,
                    "code_id": "123",
                    "filename": "debug.py",
                },
                {
                    "debug_id": "BCDEFGH",
                    "debug_file": "other-file.pdb",
                    "missing_symbols": False,
                },
                {
                    "debug_id": "CDEFGHI",
                    "debug_file": "yet-another-file.pdb",
                    "missing_symbols": True,
                    "code_id": None,
                    # Note that this does not even have a key
                    # called 'code_file'.
                },
                {
                    "debug_id": "",
                    "debug_file": None,
                    "missing_symbols": True,
                },
            ]
        }

        processor_meta = self.get_basic_processor_meta()

        rule = MissingSymbolsRule(config)

        expected_sql = rule.sql % '20141229'

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        from socorro.external.postgresql.dbapi2_util import execute_no_results
        eq_(config.transaction_executor_class.return_value.call_count, 2)
        expected_execute_args = [
            call(execute_no_results, expected_sql,
                ('2014-12-31', 'some-file.pdb', 'ABCDEFG', 'debug.py', '123')),
            call(execute_no_results, expected_sql,
                ('2014-12-31', 'yet-another-file.pdb', 'CDEFGHI', None, None))
        ]
        config.transaction_executor_class.return_value.assert_has_calls(
                expected_execute_args
        )

        # make sure it works a second time
        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        eq_(config.transaction_executor_class.return_value.call_count, 4)
        expected_execute_args = [
            call(execute_no_results, expected_sql,
                ('2014-12-31', 'some-file.pdb', 'ABCDEFG', 'debug.py', '123')),
            call(execute_no_results, expected_sql,
                ('2014-12-31', 'yet-another-file.pdb', 'CDEFGHI', None, None)),
            call(execute_no_results, expected_sql,
                ('2014-12-31', 'some-file.pdb', 'ABCDEFG', 'debug.py', '123')),
            call(execute_no_results, expected_sql,
                ('2014-12-31', 'yet-another-file.pdb', 'CDEFGHI', None, None)),
        ]
        config.transaction_executor_class.return_value.assert_has_calls(
                expected_execute_args
        )


#==============================================================================
class TestBetaVersion(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False
        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}
        processed_crash = DotDict()
        processed_crash.date_processed = '2014-12-31'
        processed_crash.product = 'WaterWolf'

        processor_meta = self.get_basic_processor_meta()

        transaction = Mock()
        config.transaction_executor_class.return_value = transaction

        rule = BetaVersionRule(config)

        # A normal beta crash, with a know version.
        transaction.return_value = (('3.0b1',),)
        processed_crash.version = '3.0'
        processed_crash.release_channel = 'beta'
        processed_crash.build = 20001001101010

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        eq_(processed_crash['version'], '3.0b1')
        eq_(len(processor_meta.processor_notes), 0)

        # A release crash, version won't get changed.
        transaction.return_value = tuple()
        processed_crash.version = '2.0'
        processed_crash.release_channel = 'release'
        processed_crash.build = 20000801101010

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        eq_(processed_crash['version'], '2.0')
        eq_(len(processor_meta.processor_notes), 0)

        # An unkwown version.
        transaction.return_value = tuple()
        processed_crash.version = '5.0a1'
        processed_crash.release_channel = 'nightly'
        processed_crash.build = 20000105101010

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        eq_(processed_crash['version'], '5.0a1')
        eq_(len(processor_meta.processor_notes), 0)

        # An incorrect build id.
        transaction.return_value = tuple()
        processed_crash.version = '5.0'
        processed_crash.release_channel = 'beta'
        processed_crash.build = '",381,,"'

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        eq_(processed_crash['version'], '5.0b0')
        eq_(len(processor_meta.processor_notes), 1)

        # A beta crash with an unknown version, gets a special mark.
        transaction.return_value = tuple()
        processed_crash.version = '3.0'
        processed_crash.release_channel = 'beta'
        processed_crash.build = 20000101101011

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        eq_(processed_crash['version'], '3.0b0')
        eq_(len(processor_meta.processor_notes), 2)


#==============================================================================
class TestOsPrettyName(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False
        return config

    #--------------------------------------------------------------------------
    def get_basic_processor_meta(self):
        processor_meta = DotDict()
        processor_meta.processor_notes = []

        return processor_meta

    #--------------------------------------------------------------------------
    def test_everything_we_hoped_for(self):
        config = self.get_basic_config()
        config.database_class = Mock()
        config.transaction_executor_class = Mock()

        raw_crash = copy.copy(canonical_standard_raw_crash)
        raw_dumps = {}

        processor_meta = self.get_basic_processor_meta()

        transaction = Mock()
        config.transaction_executor_class.return_value = transaction
        transaction.return_value = (
            ('Windows XP', '5', '0'),
            ('Windows 8', '8', '11'),
            ('Windows 10', '10', '2'),
        )

        rule = OSPrettyVersionRule(config)

        # A known Windows version.
        processed_crash = DotDict()
        processed_crash.os_name = 'Windows NT'
        processed_crash.os_version = '10.2.11.7600'

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], 'Windows 10')

        # An unknown Windows version.
        processed_crash = DotDict()
        processed_crash.os_name = 'Windows NT'
        processed_crash.os_version = '15.2'

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], 'Windows Unknown')

        # A valid version of Mac OS X.
        processed_crash = DotDict()
        processed_crash.os_name = 'Mac OS X'
        processed_crash.os_version = '10.18.324'

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], 'OS X 10.18')

        # An invalid version of Mac OS X.
        processed_crash = DotDict()
        processed_crash.os_name = 'Mac OS X'
        processed_crash.os_version = '12.1'

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], 'OS X Unknown')

        # Any version of Linux.
        processed_crash = DotDict()
        processed_crash.os_name = 'Linux'
        processed_crash.os_version = '0.0.12.13'

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], 'Linux')

        # Now try some bogus processed_crashes.
        processed_crash = DotDict()
        processed_crash.os_name = 'Lunix'
        processed_crash.os_version = None

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], 'Lunix')

        processed_crash = DotDict()
        processed_crash.os_name = None
        processed_crash.os_version = None

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], None)

        processed_crash = DotDict()

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], None)

        processed_crash = DotDict()
        processed_crash.os_name = 'Windows NT'
        processed_crash.os_version = 'NaN'

        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)
        ok_('os_pretty_version' in processed_crash)
        eq_(processed_crash['os_pretty_version'], 'Windows NT')


#==============================================================================
class TestThemePrettyNameRule(TestCase):

    #--------------------------------------------------------------------------
    def get_basic_config(self):
        config = CDotDict()
        config.logger = Mock()
        config.chatty = False
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

        rule = ThemePrettyNameRule(config)

        processed_crash.addons = [
            ('adblockpopups@jessehakanen.net', '0.3'),
            ('dmpluginff@westbyte.com', '1,4.8'),
            ('firebug@software.joehewitt.com', '1.9.1'),
            ('killjasmin@pierros14.com', '2.4'),
            ('support@surfanonymous-free.com', '1.0'),
            ('uploader@adblockfilters.mozdev.org', '2.1'),
            ('{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}', '20111107'),
            ('{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}', '2.0.3'),
            ('anttoolbar@ant.com', '2.4.6.4'),
            ('{972ce4c6-7e08-4474-a285-3208198ce6fd}', '12.0'),
            ('elemhidehelper@adblockplus.org', '1.2.1')
        ]

        # the call to be tested
        rule.act(raw_crash, raw_dumps, processed_crash, processor_meta)

        # the raw crash & raw_dumps should not have changed
        eq_(raw_crash, canonical_standard_raw_crash)
        eq_(raw_dumps, {})

        expected_addon_list = [
            ('adblockpopups@jessehakanen.net', '0.3'),
            ('dmpluginff@westbyte.com', '1,4.8'),
            ('firebug@software.joehewitt.com', '1.9.1'),
            ('killjasmin@pierros14.com', '2.4'),
            ('support@surfanonymous-free.com', '1.0'),
            ('uploader@adblockfilters.mozdev.org', '2.1'),
            ('{a0d7ccb3-214d-498b-b4aa-0e8fda9a7bf7}', '20111107'),
            ('{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}', '2.0.3'),
            ('anttoolbar@ant.com', '2.4.6.4'),
            ('{972ce4c6-7e08-4474-a285-3208198ce6fd} (default theme)',
             '12.0'),
            ('elemhidehelper@adblockplus.org', '1.2.1')
        ]
        eq_(processed_crash.addons, expected_addon_list)

    #--------------------------------------------------------------------------
    def test_missing_key(self):
        config = self.get_basic_config()

        processed_crash = DotDict()
        processor_meta = self.get_basic_processor_meta()

        rule = ThemePrettyNameRule(config)

        # Test with missing key.
        res = rule._predicate({}, {}, processed_crash, processor_meta)
        ok_(not res)

        # Test with empty list.
        processed_crash.addons = []
        res = rule._predicate({}, {}, processed_crash, processor_meta)
        ok_(not res)

        # Test with key missing from list.
        processed_crash.addons = [
            ('adblockpopups@jessehakanen.net', '0.3'),
            ('dmpluginff@westbyte.com', '1,4.8'),
        ]
        res = rule._predicate({}, {}, processed_crash, processor_meta)
        ok_(not res)

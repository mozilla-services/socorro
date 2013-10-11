# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
import copy

from datetime import datetime

from configman.dotdict import DotDict

from socorro.processor.legacy_processor import (
  LegacyCrashProcessor,
  create_symbol_path_str
)
from socorro.lib.datetimeutil import datetimeFromISOdateString, UTC

def setup_config_with_mocks():
    config = DotDict()
    config.processor_name = 'testing_processor:2012'
    config.mock_quit_fn = mock.Mock()
    config.logger = mock.Mock()
    config.transaction = mock.MagicMock()
    config.transaction_executor_class = mock.Mock(
      return_value=config.transaction
    )
    config.database = mock.Mock()
    config.database_class = mock.Mock(return_value=config.database)
    config.dump_field = 'upload_file_minidump'
    config.with_old_monitor = True

    config.stackwalk_command_line = (
      '$minidump_stackwalk_pathname -m $dumpfilePathname '
      '$processor_symbols_pathname_list 2>/dev/null'
    )
    config.minidump_stackwalk_pathname = '/bin/mdsw'
    config.symbol_cache_path = '/symbol/cache'
    config.processor_symbols_pathname_list = '"/a/a" "/b/b" "/c/c"'

    config.c_signature = DotDict()
    config.c_signature.c_signature_tool_class = mock.Mock()
    config.java_signature = DotDict()
    config.java_signature.java_signature_tool_class = mock.Mock()

    config.statistics = DotDict()
    config.statistics.stats_class = mock.Mock()
    #config.save_mdsw_json = False

    return config

canonical_standard_raw_crash = DotDict({
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
    "ProductID": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}"
})

cannonical_basic_processed_crash = DotDict({
    'addons': None,
    'addons_checked': True,
    'address': None,
    'app_notes': 'AdapterVendorID: 0x1002, AdapterDeviceID: 0x7280, '
                 'AdapterSubsysID: 01821043, '
                 'AdapterDriverVersion: 8.593.100.0\nD3D10 Layers? '
                 'D3D10 Layers- D3D9 Layers? D3D9 Layers- ',
    'additional_minidumps': [],
    'build': '20120420145725',
    'client_crash_date': datetime(2012, 5, 8, 23, 25, 54, tzinfo=UTC),
    'completeddatetime': None,
    'cpu_info': None,
    'cpu_name': None,
    'crashedThread': None,
    'crash_time': 1336519554,
    'date_processed': datetime(2012, 5, 8, 23, 26, 33, 454482, tzinfo=UTC),
    'distributor': None,
    'distributor_version': None,
    'dump': '',
    'email': 'noreply@mozilla.com',
    'exploitability': None,
    'flash_version': None,
    'hangid': None,
    'hang_type': 0,
    'install_age': 1079662,
    'java_stack_trace': None,
    'last_crash': 86985,
    'process_type': None,
    'os_name': None,
    'os_version': None,
    'pluginFilename': None,
    'pluginName': None,
    'pluginVersion': None,
    'process_type': None,
    'processor_notes': '',
    'product': 'Firefox',
    'productid': '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}',
    'reason': None,
    'release_channel': 'release',
    'ReleaseChannel': 'release',
    'signature': 'EMPTY: crash failed to process',
    'startedDateTime': datetime(2012, 5, 4, 15, 10, tzinfo=UTC),
    'success': False, 'url': 'http://www.mozilla.com',
    'topmost_filenames': '',
    'truncated': None,
    'uptime': 20116,
    'url': 'http://www.mozilla.com',
    'user_comments': 'why did my browser crash?  #fail',
    'user_id': '',
    'uuid': '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
    'version': '12.0',
    'Winsock_LSP': None,
})

canonical_standard_raw_crash_corrupt = DotDict({
    "InstallTime": "1335787057",
    "AdapterVendorID": "0x10de",
    "Comments": "watching video in Safari Books Online, "
                "moved tab to second screen",
    "Theme": "classic/1.0",
    "Version": "12.0",
    "id": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
    "Vendor": "Mozilla",
    "EMCheckCompatibility": "true",
    "Throttleable": "1",
    "URL": "http://cisco.safaribooksonline.com/standaloneplayer?"
           "xmlid=9781926873985/0404&__playtm=162.106",
    "version": "12.0",
    "AdapterDeviceID": "0x a29",
    "ReleaseChannel": "release",
    "submitted_timestamp": "2012-05-09T23:06:02.586890+00:00",
    "buildid": "20120420145725",
    "timestamp": 1336604762.5870121,
    "Notes": "AdapterVendorID: 0x10de, AdapterDeviceID: 0x a29",
    "CrashTime": "1336604658",
    "FramePoisonBase": "00000000f0dea000",
    "FramePoisonSize": "4096",
    "StartupTime": "1336508037",
    "Add-ons": "eventbug@getfirebug.com:0.1b10,"
               "firebug@software.joehewitt.com:1.9.1,"
               "sroussey@illumination-for-developers.com:1.1.11,"
               "youtubeextension@mozilla.doslash.org:1.0,"
               "{4176DFF4-4698-11DE-BEEB-45DA55D89593}:0.8.32,"
               "{6AC85730-7D0F-4de0-B3FA-21142DD85326}:2.6.4,"
               "{c45c406e-ab73-11d8-be73-000a95be3b12}:1.1.9,"
               "{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}:2.0.3,"
               "{d40f5e7b-d2cf-4856-b441-cc613eeffbe3}:1.68,"
               "{e968fc70-8f95-4ab9-9e79-304de2a71ee1}:0.7.3,"
               "firefox@ghostery.com:2.7.2,"
               "foxyproxy-basic@eric.h.jung:2.6,"
               "{e3f6c2cc-d8db-498c-af6c-499fb211db97}:1.12.0.3,"
               "checkplaces@andyhalford.com:2.6.2,"
               "sortplaces@andyhalford.com:1.9.2,"
               "{5384767E-00D9-40E9-B72F-9CC39D655D6F}:1.4.2.1,"
               "https-everywhere@eff.org:2.0.3,"
               "{73a6fe31-595d-460b-a920-fcc0f8843232}:2.4,"
               "{972ce4c6-7e08-4474-a285-3208198ce6fd}:12.0,"
               "onepassword@agilebits.com:3.9.4",
    "BuildID": "20120420145725",
    "SecondsSinceLastCrash": "13912517",
    "ProductName": "Firefox",
    "legacy_processing": 0,
    "ProductID": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}"
})


class TestLegacyProcessor(unittest.TestCase):
    """
    """

    def test_create_symbol_path_str(self):
        s = '/a/a, /b/b, /c/c'
        r = create_symbol_path_str(s)
        e = '"/a/a" "/b/b" "/c/c"'
        self.assertEqual(r, e)

    def test_legacy_processor_basics(self):
        config = setup_config_with_mocks()
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform:
            leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)
            self.assertEqual(leg_proc.quit_check, config.mock_quit_fn)
            self.assertEqual(config.transaction, leg_proc.transaction)
            self.assertEqual(config.database,  leg_proc.database)
            self.assertEqual(
              leg_proc.mdsw_command_line,
              '/bin/mdsw -m DUMPFILEPATHNAME "/a/a" "/b/b" "/c/c" 2>/dev/null'
            )
            self.assertEqual(m_transform.call_count, 2)

    def test_convert_raw_crash_to_processed_crash_basic(self):
        config = setup_config_with_mocks()
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11,
                                                  tzinfo=UTC)

                raw_crash = DotDict()
                raw_crash.uuid = '3bc4bcaa-b61d-4d1f-85ae-30cb32120504'
                raw_crash.submitted_timestamp = '2012-05-04T15:33:33'
                raw_dump = {'upload_file_minidump':
                                '/some/path/%s.dump' % raw_crash.uuid,
                            'aux_dump_001':
                            '/some/path/aux_001.%s.dump' % raw_crash.uuid,
                            }
                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)

                started_timestamp = datetime(2012, 5, 4, 15, 10, tzinfo=UTC)
                leg_proc._log_job_start = mock.Mock(
                  return_value=started_timestamp
                )

                basic_processed_crash = DotDict()
                basic_processed_crash.uuid = raw_crash.uuid
                basic_processed_crash.hang_type = 0
                basic_processed_crash.java_stack_trace = None
                leg_proc._create_basic_processed_crash = mock.Mock(
                  return_value=basic_processed_crash)

                leg_proc._log_job_end = mock.Mock()

                processed_crash_update_dict = DotDict()
                processed_crash_update_dict.success = True
                leg_proc._do_breakpad_stack_dump_analysis = mock.Mock(
                  return_value=processed_crash_update_dict
                )

                leg_proc._cleanup_temp_file = mock.Mock()

                 # Here's the call being tested
                processed_crash = \
                    leg_proc.convert_raw_crash_to_processed_crash(
                      raw_crash,
                      raw_dump
                    )

                # test the result
                self.assertEqual(1, leg_proc._log_job_start.call_count)
                leg_proc._log_job_start.assert_called_with(raw_crash.uuid)

                self.assertEqual(1, m_transform.apply_all_rules.call_count)
                m_transform.apply_all_rules.has_calls(
                    mock.call(raw_crash, leg_proc),
                )
                self.assertEqual(
                    1,
                    m_transform.apply_until_action_succeeds.call_count
                )
                m_transform.apply_all_rules.has_calls(
                    mock.call(raw_crash, processed_crash, leg_proc)
                )

                self.assertEqual(
                  1,
                  leg_proc._create_basic_processed_crash.call_count
                )
                leg_proc._create_basic_processed_crash.assert_called_with(
                  raw_crash.uuid,
                  raw_crash,
                  datetime(2012, 5, 4, 15, 33, 33, tzinfo=UTC),
                  started_timestamp,
                  [
                      'testing_processor:2012',
                  ]
                )

                self.assertEqual(
                  2,
                  leg_proc._do_breakpad_stack_dump_analysis.call_count
                )
                first_call, second_call = \
                    leg_proc._do_breakpad_stack_dump_analysis.call_args_list
                self.assertEqual(
                  first_call,
                  ((raw_crash.uuid, '/some/path/%s.dump' % raw_crash.uuid,
                   0, None, datetime(2012, 5, 4, 15, 33, 33, tzinfo=UTC),
                   [
                      'testing_processor:2012',
                   ]),)
                )
                self.assertEqual(
                  second_call,
                  ((raw_crash.uuid,
                   '/some/path/aux_001.%s.dump' % raw_crash.uuid,
                   0, None, datetime(2012, 5, 4, 15, 33, 33, tzinfo=UTC),
                   [
                      'testing_processor:2012',
                   ]),)
                )

                self.assertEqual(1, leg_proc._log_job_end.call_count)
                leg_proc._log_job_end.assert_called_with(
                  datetime(2012, 5, 4, 15, 11, tzinfo=UTC),
                  True,
                  raw_crash.uuid
                )

                epc = DotDict()
                epc.uuid = raw_crash.uuid
                epc.topmost_filenames = ''
                epc.processor_notes = "testing_processor:2012"

                epc.success = True
                epc.completeddatetime = datetime(2012, 5, 4, 15, 11,
                                                 tzinfo=UTC)
                epc.hang_type = 0
                epc.java_stack_trace = None
                epc.Winsock_LSP = None
                epc.additional_minidumps = ['aux_dump_001']
                epc.aux_dump_001 = {'success': True}
                self.assertEqual(
                  dict(processed_crash),
                  dict(epc)
                )

                leg_proc._statistics.assert_has_calls(
                    [
                        mock.call.incr('jobs'),
                        mock.call.incr('restarts')
                    ],
                    any_order=True
                )

    def test_convert_raw_crash_to_processed_crash_unexpected_error(self):
        config = setup_config_with_mocks()
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11,
                                                  tzinfo=UTC)

                raw_crash = DotDict()
                raw_crash.uuid = '3bc4bcaa-b61d-4d1f-85ae-30cb32120504'
                raw_crash.submitted_timestamp = '2012-05-04T15:33:33'
                raw_dump = {'upload_file_minidump': 'abcdef'}

                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)

                started_timestamp = datetime(2012, 5, 4, 15, 10, tzinfo=UTC)
                leg_proc._log_job_start = mock.Mock(
                  return_value=started_timestamp
                )

                basic_processed_crash = DotDict()
                basic_processed_crash.uuid = raw_crash.uuid
                basic_processed_crash.success = False
                basic_processed_crash.hang_type = 0
                basic_processed_crash.java_stack_trace = None
                leg_proc._create_basic_processed_crash = mock.Mock(
                  return_value=basic_processed_crash)

                leg_proc._get_temp_dump_pathname = mock.Mock(
                  return_value='/tmp/x'
                )

                leg_proc._log_job_end = mock.Mock()

                processed_crash_update_dict = DotDict()
                processed_crash_update_dict.success = True
                leg_proc._do_breakpad_stack_dump_analysis = mock.Mock(
                  side_effect=Exception('nobody expects the spanish '
                                        'inquisition')
                )

                 # Here's the call being tested
                processed_crash = \
                    leg_proc.convert_raw_crash_to_processed_crash(
                      raw_crash,
                      raw_dump
                    )

                self.assertEqual(1, leg_proc._log_job_end.call_count)
                leg_proc._log_job_end.assert_called_with(
                  datetime(2012, 5, 4, 15, 11, tzinfo=UTC),
                  False,
                  raw_crash.uuid
                )

                e = {
                  'processor_notes':
                      'testing_processor:2012; unrecoverable processor error: '
                      'nobody expects the spanish inquisition',
                  'completeddatetime': datetime(2012, 5, 4, 15, 11,
                                                tzinfo=UTC),
                  'success': False,
                  'uuid': raw_crash.uuid,
                  'hang_type': 0,
                  'java_stack_trace': None,
                  'additional_minidumps': [],
                }
                self.assertEqual(e, processed_crash)
                leg_proc._statistics.assert_has_calls(
                    [
                        mock.call.incr('jobs'),
                        mock.call.incr('restarts'),
                        mock.call.incr('errors'),
                    ],
                    any_order=True
                )


    def test_create_basic_processed_crash_normal(self):
        config = setup_config_with_mocks()
        config.collect_addon = False
        config.collect_crash_process = False
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11,
                                                  tzinfo=UTC)

                started_timestamp = datetime(2012, 5, 4, 15, 10, tzinfo=UTC)

                raw_crash = canonical_standard_raw_crash
                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)
                processor_notes = []

                # test 01
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  raw_crash,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                assert 'exploitability' in processed_crash
                self.assertEqual(
                  processed_crash,
                  dict(cannonical_basic_processed_crash)
                )

                # test 02
                processor_notes = []
                raw_crash_missing_product = copy.deepcopy(raw_crash)
                del raw_crash_missing_product['ProductName']
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  raw_crash_missing_product,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                processed_crash_missing_product = \
                    copy.copy(cannonical_basic_processed_crash)
                processed_crash_missing_product.product = None
                self.assertEqual(
                  processed_crash,
                  processed_crash_missing_product
                )
                self.assertTrue('WARNING: raw_crash missing ProductName' in
                                processor_notes)
                self.assertEqual(len(processor_notes), 1)

                # test 03
                processor_notes = []
                raw_crash_missing_version = copy.deepcopy(raw_crash)
                del raw_crash_missing_version['Version']
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  raw_crash_missing_version,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                processed_crash_missing_version = \
                    copy.copy(cannonical_basic_processed_crash)
                processed_crash_missing_version.version = None
                self.assertEqual(
                  processed_crash,
                  processed_crash_missing_version
                )
                self.assertTrue('WARNING: raw_crash missing Version' in
                                processor_notes)
                self.assertEqual(len(processor_notes), 1)

                # test 04
                processor_notes = []
                raw_crash_with_hangid = copy.deepcopy(raw_crash)
                raw_crash_with_hangid.HangID = \
                    '30cb3212-b61d-4d1f-85ae-3bc4bcaa0504'
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  raw_crash_with_hangid,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                processed_crash_with_hangid = \
                    copy.copy(cannonical_basic_processed_crash)
                processed_crash_with_hangid.hangid = \
                    raw_crash_with_hangid.HangID
                processed_crash_with_hangid.hang_type = -1
                self.assertEqual(
                  processed_crash,
                  processed_crash_with_hangid
                )
                self.assertEqual(len(processor_notes), 0)

                # test 05
                processor_notes = []
                raw_crash_with_pluginhang = copy.deepcopy(raw_crash)
                raw_crash_with_pluginhang.PluginHang = '1'
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  raw_crash_with_pluginhang,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                processed_crash_with_pluginhang = \
                    copy.copy(cannonical_basic_processed_crash)
                processed_crash_with_pluginhang.hangid = \
                    'fake-3bc4bcaa-b61d-4d1f-85ae-30cb32120504'
                processed_crash_with_pluginhang.hang_type = -1
                self.assertEqual(
                  processed_crash,
                  processed_crash_with_pluginhang
                )
                self.assertEqual(len(processor_notes), 0)

                # test 06
                processor_notes = []
                raw_crash_with_hang_only = copy.deepcopy(raw_crash)
                raw_crash_with_hang_only.Hang = 16
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  raw_crash_with_hang_only,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                processed_crash_with_hang_only = \
                    copy.copy(cannonical_basic_processed_crash)
                processed_crash_with_hang_only.hang_type = 1
                self.assertEqual(
                  processed_crash,
                  processed_crash_with_hang_only
                )
                self.assertEqual(len(processor_notes), 0)
                leg_proc._statistics.assert_has_calls(
                    [
                        mock.call.incr('restarts'),
                    ],
                    any_order=True
                )

                # test 07
                processor_notes = []
                raw_crash_with_hang_only = copy.deepcopy(raw_crash)
                raw_crash_with_hang_only.Hang = 'bad value'
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  raw_crash_with_hang_only,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                processed_crash_with_hang_only = \
                    copy.copy(cannonical_basic_processed_crash)
                processed_crash_with_hang_only.hang_type = 0
                self.assertEqual(
                  processed_crash,
                  processed_crash_with_hang_only
                )
                self.assertEqual(len(processor_notes), 0)
                leg_proc._statistics.assert_has_calls(
                    [
                        mock.call.incr('restarts'),
                    ],
                    any_order=True
                )

                # test 08
                processor_notes = []
                bad_raw_crash = copy.deepcopy(raw_crash)
                bad_raw_crash['SecondsSinceLastCrash'] = 'badness'
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  bad_raw_crash,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                self.assertEqual(processed_crash.last_crash, None)
                self.assertTrue(
                    'non-integer value of "SecondsSinceLastCrash"' in
                    processor_notes
                )

                # test 09
                processor_notes = []
                bad_raw_crash = copy.deepcopy(raw_crash)
                bad_raw_crash['CrashTime'] = 'badness'
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  bad_raw_crash,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                self.assertEqual(processed_crash.crash_time, 0)
                self.assertTrue(
                    'non-integer value of "CrashTime"' in processor_notes
                )

                # test 10
                processor_notes = []
                bad_raw_crash = copy.deepcopy(raw_crash)
                bad_raw_crash['StartupTime'] = 'badness'
                bad_raw_crash['InstallTime'] = 'more badness'
                bad_raw_crash['CrashTime'] = 'even more badness'
                processed_crash = leg_proc._create_basic_processed_crash(
                  '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                  bad_raw_crash,
                  datetimeFromISOdateString(raw_crash.submitted_timestamp),
                  started_timestamp,
                  processor_notes,
                )
                self.assertEqual(processed_crash.install_age, 0)
                self.assertTrue(
                    'non-integer value of "StartupTime"' in processor_notes
                )
                self.assertTrue(
                    'non-integer value of "InstallTime"' in processor_notes
                )
                self.assertTrue(
                    'non-integer value of "CrashTime"' in processor_notes
                )

    def test_process_list_of_addons(self):
        config = setup_config_with_mocks()
        config.collect_addon = False
        config.collect_crash_process = False
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11,
                                                  tzinfo=UTC)
                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)

                # test successful case
                raw_crash = canonical_standard_raw_crash
                processor_notes = []
                addon_list = leg_proc._process_list_of_addons(
                  raw_crash,
                  processor_notes
                )
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
                self.assertEqual(addon_list, expected_addon_list)

                # test colon in version case
                raw_crash = copy.copy(canonical_standard_raw_crash)
                raw_crash['Add-ons'] = 'adblockpopups@jessehakanen.net:0:3:1'
                processor_notes = []
                addon_list = leg_proc._process_list_of_addons(
                  raw_crash,
                  processor_notes
                )
                expected_addon_list = [
                  ('adblockpopups@jessehakanen.net', '0:3:1'),
                ]
                self.assertEqual(addon_list, expected_addon_list)
                leg_proc._statistics.assert_has_calls(
                    [
                        mock.call.incr('restarts'),
                    ],
                    any_order=True
                )

    def test_add_process_type_to_processed_crash(self):
        config = setup_config_with_mocks()
        config.collect_addon = False
        config.collect_crash_process = True
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11,
                                                  tzinfo=UTC)
                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)

                # test null case
                raw_crash = canonical_standard_raw_crash
                processor_notes = []
                pc_update = leg_proc._add_process_type_to_processed_crash(
                  raw_crash
                )
                self.assertEqual(pc_update, {})
                self.assertEqual(processor_notes, [])

                # test unknown case
                raw_crash = copy.copy(canonical_standard_raw_crash)
                raw_crash.ProcessType = 'unknown'
                processor_notes = []
                pc_update = leg_proc._add_process_type_to_processed_crash(
                  raw_crash
                )
                self.assertEqual(
                  pc_update,
                  {
                    'process_type': 'unknown',
                  }
                )
                self.assertEqual(processor_notes, [])

                #test plugin null case
                raw_crash = copy.copy(canonical_standard_raw_crash)
                raw_crash.ProcessType = 'plugin'
                processor_notes = []
                pc_update = leg_proc._add_process_type_to_processed_crash(
                  raw_crash
                )
                self.assertEqual(
                  pc_update,
                  {
                    'process_type': 'plugin',
                    'PluginFilename': '',
                    'PluginName': '',
                    'PluginVersion': '',
                  }
                )
                self.assertEqual(processor_notes, [])

                #test plugin case
                raw_crash = copy.copy(canonical_standard_raw_crash)
                raw_crash.ProcessType = 'plugin'
                raw_crash.PluginFilename = 'myfile.dll'
                raw_crash.PluginName = 'myplugin'
                raw_crash.PluginVersion = '6.6.6'
                processor_notes = []
                pc_update = leg_proc._add_process_type_to_processed_crash(
                  raw_crash
                )
                self.assertEqual(
                  pc_update,
                  {
                    'process_type': 'plugin',
                    'PluginFilename': 'myfile.dll',
                    'PluginName': 'myplugin',
                    'PluginVersion': '6.6.6',
                  }
                )
                self.assertEqual(processor_notes, [])

    def basic_jDump_stack_dump_analysis(self, mdsw_sequence,
                                        signature='signature'):

        m_iter = mock.MagicMock()
        m_iter.return_value = m_iter
        m_iter.__iter__.return_value = iter(mdsw_sequence)
        m_iter.cache = [str(x) for x in mdsw_sequence[:3]]
        m_iter.theIterator = mock.Mock()

        m_subprocess = mock.MagicMock()
        m_subprocess.wait = mock.MagicMock(return_value=0)

        class MyProcessor(LegacyCrashProcessor):

            def _invoke_minidump_stackwalk(self, dump_pathname):
                return m_iter, mock.Mock()

            def _analyze_header(self, ooid, dump_analysis_line_iterator,
                                submitted_timestamp, processor_notes):
                for x in zip(xrange(5), dump_analysis_line_iterator):
                    pass
                dump_analysis_line_iterator.next()
                processed_crash_update = DotDict()
                processed_crash_update.crashedThread = 17
                processed_crash_update.os_name = 'Windows NT'
                return processed_crash_update

            def _analyze_frames(self, hang_type, java_stack_trace,
                                make_modules_lower_case,
                                dump_analysis_line_iterator,
                                submitted_timestamp,
                                crashed_thread,
                                processor_notes):
                for x in zip(xrange(5), dump_analysis_line_iterator):
                    pass
                return DotDict({
                  "signature": signature,
                  "truncated": False,
                  "topmost_filenames": 'topmost_sourcefiles',
                })

        config = setup_config_with_mocks()
        config.crashing_thread_tail_frame_threshold = 5
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11,
                                                  tzinfo=UTC)
                leg_proc = MyProcessor(config, config.mock_quit_fn)

                processor_notes = []
                processed_crash_update = \
                    leg_proc._do_breakpad_stack_dump_analysis(
                      '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
                      'some_path',
                      0,
                      None,
                      datetime(2012, 5, 4, 15, 11, tzinfo=UTC),
                      processor_notes
                    )
                return processed_crash_update

    def test_do_breakpad_stack_dump_analysis_with_jDump_success(self):
        mdsw_sequence = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             '{"a": 23, "b": 16, "status": 0, ',
             '"c": "c"}']
        processed_crash_update = (
            self.basic_jDump_stack_dump_analysis(mdsw_sequence)
        )
        e_pcu = {
          'os_name': 'Windows NT',
          'success': False,
          'dump': '0\n1\n2',
          'truncated': False,
          'crashedThread': 17,
          'signature': 'signature',
          'topmost_filenames': 'topmost_sourcefiles',
          'exploitability': 'unknown',
          'json_dump': {
              u'a': 23,
              u'b': 16,
              u'c': u'c',
              u'status': 0
              },
        }
        self.assertEqual(dict(e_pcu), dict(processed_crash_update))

    def test_do_breakpad_stack_dump_analysis_with_jDump_bad_mdsw_1(self):
        mdsw_sequence = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             '{"a": 23, "b": 16, "status": 3, ',
             '"c": "c"}']
        processed_crash_update = (
            self.basic_jDump_stack_dump_analysis(
                mdsw_sequence,
                signature='EMPTY: bad deal'
            )
        )
        e_pcu = {
          'os_name': 'Windows NT',
          'success': False,
          'dump': '0\n1\n2',
          'truncated': False,
          'crashedThread': 17,
          'signature': 'EMPTY: bad deal; MDSW_ERROR_NO_THREAD_LIST',
          'topmost_filenames': 'topmost_sourcefiles',
          'exploitability': 'unknown',
          'json_dump': {
              u'a': 23,
              u'b': 16,
              u'c': u'c',
              u'status': 3
              },
        }
        self.assertEqual(dict(e_pcu), dict(processed_crash_update))

    def test_do_breakpad_stack_dump_analysis_with_jDump_bad_mdsw_2(self):
        mdsw_sequence = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             '{"a": 23, "b": 16, "status": 8, ',
             '"c": "c"}']
        processed_crash_update = (
            self.basic_jDump_stack_dump_analysis(
                mdsw_sequence,
                signature='EMPTY: bad deal'
            )
        )
        e_pcu = {
          'os_name': 'Windows NT',
          'success': False,
          'dump': '0\n1\n2',
          'truncated': False,
          'crashedThread': 17,
          'signature': 'EMPTY: bad deal; MDSW_UNKNOWN_ERROR',
          'topmost_filenames': 'topmost_sourcefiles',
          'exploitability': 'unknown',
          'json_dump': {
              u'a': 23,
              u'b': 16,
              u'c': u'c',
              u'status': 8
              },
        }
        self.assertEqual(dict(e_pcu), dict(processed_crash_update))

    def test_do_breakpad_stack_dump_analysis_with_jDump_bad_mdsw_3(self):
        mdsw_sequence = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             '{"a": 23, "b": 16, "status": 0, ',
             '"sensitive": {"exploitability": "extreme"}, ',
             '"c": "c"}']
        processed_crash_update = (
            self.basic_jDump_stack_dump_analysis(
                mdsw_sequence,
            )
        )
        e_pcu = {
          'os_name': 'Windows NT',
          'success': False,
          'dump': '0\n1\n2',
          'truncated': False,
          'crashedThread': 17,
          'signature': 'signature',
          'topmost_filenames': 'topmost_sourcefiles',
          'exploitability': u'extreme',
          'json_dump': {
              u'a': 23,
              u'b': 16,
              u'c': u'c',
              u'status': 0,
              u'sensitive': {
                u'exploitability': u'extreme'
              },
            },
        }
        self.assertEqual(dict(e_pcu), dict(processed_crash_update))

    def test_analyze_header(self):  # verify fix for Bug 881623 in test one
        """test some of the possibilities in reading the first three lines
        from MDSW.  This does not provide comprehensive coverage."""
        config = setup_config_with_mocks()
        config.collect_addon = False
        config.collect_crash_process = True
        config.crashing_thread_frame_threshold = 100000
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11,
                                                  tzinfo=UTC)
                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)

                # test one - all ok
                def dump_iter():
                    lines = [
                        'OS|Windows NT|6.1.7601 Service Pack 1 ',
                        'CPU|x86|GenuineIntel family 6 model 42 stepping 7|8',
                        'Crash|EXCEPTION_ACCESS_VIOLATION_READ|0xffffffffdadadada|0'
                    ]
                    for a_line in lines:
                        yield a_line

                processor_notes = []

                result = leg_proc._analyze_header(
                    '1fcdec5e-face-404a-8622-babda2130605',
                    dump_iter(),
                    m_utc_now(),
                    processor_notes
                )

                self.assertTrue(result.success)
                self.assertEqual(result.os_name, 'Windows NT')
                self.assertEqual(result.os_version, '6.1.7601 Service Pack 1')
                self.assertEqual(result.cpu_name, 'x86')
                self.assertEqual(result.cpu_info, 'GenuineIntel family 6 model 42 stepping 7 | 8')
                self.assertEqual(result.reason, 'EXCEPTION_ACCESS_VIOLATION_READ')
                self.assertEqual(result.address, '0xffffffffdadadada')
                self.assertEqual(result.crashedThread, 0)

                # test two - crashed thread missing
                def dump_iter():
                    lines = [
                        'OS|Windows NT|6.1.7601 Service Pack 1 ',
                        'CPU|x86|GenuineIntel family 6 model 42 stepping 7|8',
                        'Crash|EXCEPTION_ACCESS_VIOLATION_READ|0xffffffffdadadada|'
                    ]
                    for a_line in lines:
                        yield a_line

                processor_notes = []

                result = leg_proc._analyze_header(
                    '1fcdec5e-face-404a-8622-babda2130605',
                    dump_iter(),
                    m_utc_now(),
                    processor_notes
                )

                self.assertTrue(result.success)
                self.assertEqual(result.os_name, 'Windows NT')
                self.assertEqual(result.os_version, '6.1.7601 Service Pack 1')
                self.assertEqual(result.cpu_name, 'x86')
                self.assertEqual(result.cpu_info, 'GenuineIntel family 6 model 42 stepping 7 | 8')
                self.assertEqual(result.reason, 'EXCEPTION_ACCESS_VIOLATION_READ')
                self.assertEqual(result.address, '0xffffffffdadadada')
                self.assertEqual(result.crashedThread, None)
                self.assertTrue(
                    'MDSW did not identify the crashing thread' in
                    processor_notes
                )

                # test three - no lines
                def dump_iter():
                    for a_line in []:
                        yield a_line

                processor_notes = []

                result = leg_proc._analyze_header(
                    '1fcdec5e-face-404a-8622-babda2130605',
                    dump_iter(),
                    m_utc_now(),
                    processor_notes
                )

                self.assertTrue(result.success)
                self.assertEqual(result.os_name, None)
                self.assertEqual(result.os_version, None)
                self.assertEqual(result.cpu_name, None)
                self.assertEqual(result.cpu_info, None)
                self.assertEqual(result.reason, None)
                self.assertEqual(result.address, None)
                self.assertEqual(result.crashedThread, None)
                self.assertTrue(
                    'MDSW did not identify the crashing thread' in
                    processor_notes
                )
                self.assertTrue(
                    'MDSW emitted no header lines' in
                    processor_notes
                )

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
    config.mock_quit_fn = mock.Mock()
    config.logger = mock.Mock()
    config.transaction = mock.Mock()
    config.transaction_executor_class = mock.Mock(return_value=
                                                  config.transaction)
    config.database = mock.Mock()
    config.database_class = mock.Mock(return_value=config.database)
    config.stackwalkCommandLine = (
      '$minidump_stackwalkPathname -m $dumpfilePathname '
      '$processorSymbolsPathnameList 2>/dev/null'
    )
    config.minidump_stackwalkPathname = '/bin/mdsw'
    config.symbolCachePath = '/symbol/cache'
    config.processorSymbolsPathnameList = '"/a/a" "/b/b" "/c/c"'

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
    'client_crash_date': datetime(2012, 5, 8, 23, 25, 54, tzinfo=UTC),
    'app_notes': 'AdapterVendorID: 0x1002, AdapterDeviceID: 0x7280, '
                 'AdapterSubsysID: 01821043, '
                 'AdapterDriverVersion: 8.593.100.0\nD3D10 Layers? '
                 'D3D10 Layers- D3D9 Layers? D3D9 Layers- ',
    'date_processed': datetime(2012, 5, 8, 23, 26, 33, 454482, tzinfo=UTC),
    'install_age': 1079662,
    'dump': '',
    'startedDateTime': datetime(2012, 5, 4, 15, 10),
    'last_crash': 86985,
    'java_stack_trace': None,
    'product': 'Firefox',
    'crash_time': 1336519554,
    'hang_type': 0,
    'distributor': None,
    'user_id': '',
    'user_comments': 'why did my browser crash?  #fail',
    'uptime': 20116,
    'release_channel': 'release',
    'uuid': '3bc4bcaa-b61d-4d1f-85ae-30cb32120504',
    'success': False, 'url': 'http://www.mozilla.com',
    'distributor_version': None,
    'process_type': None,
    'hangid': None,
    'version': '12.0',
    'build': '20120420145725',
    'ReleaseChannel': 'release',
    'email': 'noreply@mozilla.com',
    'addons_checked': True,
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
              leg_proc.command_line,
              '/bin/mdsw -m DUMPFILEPATHNAME "/a/a" "/b/b" "/c/c" 2>/dev/null'
            )
            self.assertEqual(m_transform.call_count, 1)

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
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11)

                raw_crash = DotDict()
                raw_crash.uuid = '3bc4bcaa-b61d-4d1f-85ae-30cb32120504'
                raw_crash.submitted_timestamp = '2012-05-04T15:33:33'
                raw_dump = 'abcdef'
                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)

                started_timestamp = datetime(2012, 5, 4, 15, 10)
                leg_proc._log_job_start = mock.Mock(
                  return_value=started_timestamp
                )

                basic_processed_crash = DotDict()
                basic_processed_crash.uuid = raw_crash.uuid
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
                m_transform.apply_all_rules.assert_called_with(
                  raw_crash,
                  leg_proc
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
                  []
                )

                self.assertEqual(
                  1,
                  leg_proc._get_temp_dump_pathname.call_count
                )
                leg_proc._get_temp_dump_pathname.assert_called_with(
                  raw_crash.uuid,
                  raw_dump
                )

                self.assertEqual(
                  1,
                  leg_proc._do_breakpad_stack_dump_analysis.call_count
                )
                leg_proc._do_breakpad_stack_dump_analysis.assert_called_with(
                  raw_crash.uuid,
                  '/tmp/x',
                  0,
                  None,
                  datetime(2012, 5, 4, 15, 33, 33, tzinfo=UTC),
                  []
                )

                self.assertEqual(
                  1,
                  leg_proc._cleanup_temp_file.call_count
                )
                leg_proc._cleanup_temp_file.assert_called_with('/tmp/x')

                self.assertEqual(1, leg_proc._log_job_end.call_count)
                leg_proc._log_job_end.assert_called_with(
                  datetime(2012, 5, 4, 15, 11),
                  True,
                  raw_crash.uuid
                )

                epc = DotDict()
                epc.uuid = raw_crash.uuid
                epc.topmost_filenames = ''
                epc.processor_notes = ''
                epc.success = True
                epc.completeddatetime = datetime(2012, 5, 4, 15, 11)
                epc.hang_type = 0
                epc.java_stack_trace = None

                self.assertEqual(
                  processed_crash,
                  epc
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
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11)

                raw_crash = DotDict()
                raw_crash.uuid = '3bc4bcaa-b61d-4d1f-85ae-30cb32120504'
                raw_crash.submitted_timestamp = '2012-05-04T15:33:33'
                raw_dump = 'abcdef'

                leg_proc = LegacyCrashProcessor(config, config.mock_quit_fn)

                started_timestamp = datetime(2012, 5, 4, 15, 10)
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

                leg_proc._cleanup_temp_file = mock.Mock()

                 # Here's the call being tested
                processed_crash = \
                    leg_proc.convert_raw_crash_to_processed_crash(
                      raw_crash,
                      raw_dump
                    )

                self.assertEqual(
                  1,
                  leg_proc._cleanup_temp_file.call_count
                )
                leg_proc._cleanup_temp_file.assert_called_with('/tmp/x')

                self.assertEqual(1, leg_proc._log_job_end.call_count)
                leg_proc._log_job_end.assert_called_with(
                  datetime(2012, 5, 4, 15, 11),
                  False,
                  raw_crash.uuid
                )

                e = {
                  'processor_notes': 'nobody expects the spanish inquisition',
                  'completeddatetime': datetime(2012, 5, 4, 15, 11),
                  'success': False,
                  'uuid': raw_crash.uuid,
                  'hang_type': 0,
                  'java_stack_trace': None,
                }
                self.assertEqual(e, processed_crash)

    def test_create_basic_processed_crash_normal(self):
        config = setup_config_with_mocks()
        config.collectAddon = False
        config.collectCrashProcess = False
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11)

                started_timestamp = datetime(2012, 5, 4, 15, 10)

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
                self.assertEqual(
                  processed_crash,
                  cannonical_basic_processed_crash
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


    def test_process_list_of_addons(self):
        config = setup_config_with_mocks()
        config.collectAddon = False
        config.collectCrashProcess = False
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11)
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


    def test_add_process_type_to_processed_crash(self):
        config = setup_config_with_mocks()
        config.collectAddon = False
        config.collectCrashProcess = True
        mocked_transform_rules_str = \
            'socorro.processor.legacy_processor.TransformRuleSystem'
        with mock.patch(mocked_transform_rules_str) as m_transform_class:
            m_transform = mock.Mock()
            m_transform_class.return_value = m_transform
            m_transform.attach_mock(mock.Mock(), 'apply_all_rules')
            utc_now_str = 'socorro.processor.legacy_processor.utc_now'
            with mock.patch(utc_now_str) as m_utc_now:
                m_utc_now.return_value = datetime(2012, 5, 4, 15, 11)
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




import unittest
import mock

from datetime import datetime

from configman.dotdict import DotDict

from socorro.processor.legacy_processor import (
  LegacyCrashProcessor,
  create_symbol_path_str
)
from socorro.lib.datetimeutil import UTC

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

                processed_crash = \
                    leg_proc.convert_raw_crash_to_processed_crash(
                      raw_crash,
                      raw_dump
                    )

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

                self.assertEqual(
                  processed_crash,
                  epc
                )


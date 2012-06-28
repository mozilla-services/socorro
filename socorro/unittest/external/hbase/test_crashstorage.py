import os
import time
import json
import unittest
import mock

from configman import ConfigurationManager

from socorro.external.hbase import hbase_client

from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.external.hbase.crashstorage import HBaseCrashStorage
from socorro.lib.util import DotDict
from socorro.unittest.config import commonconfig
from socorro.database.transaction_executor import (
  TransactionExecutorWithLimitedBackoff
)

_run_integration_tests = os.environ.get('RUN_HBASE_INTEGRATION_TESTS', False)
if _run_integration_tests in ('false', 'False', 'no', '0'):
    _run_integration_tests = False


if not _run_integration_tests:
    import logging
    logging.warning("Skipping HBase integration tests")

else:

    class TestIntegrationHBaseCrashStorage(unittest.TestCase):
        """
        If you ever get this::
            Traceback (most recent call last):
            ...
            socorro.storage.hbaseClient.FatalException: the connection is not
            viable.  retries fail:

        Then try the following:

            /etc/init.d/hadoop-hbase-master restart
            /etc/init.d/hadoop-hbase-thrift restart

        Also, you can look in /var/log/hbase for clues.
        Still not working, try:

            hbase shell
            > describe 'crash_reports'

        and keep an eye on the logs.
        """

        def tearDown(self):
            self._truncate_hbase_table()

        def _truncate_hbase_table(self):
            connection = hbase_client.HBaseConnectionForCrashReports(
                commonconfig.hbaseHost.default,
                commonconfig.hbasePort.default,
                100
            )
            for row in connection.merge_scan_with_prefix(
              'crash_reports', '', ['ids:ooid']):
                index_row_key = row['_rowkey']
                connection.client.deleteAllRow(
                  'crash_reports', index_row_key)
            # because of HBase's async nature, deleting can take time
            list(connection.iterator_for_all_legacy_to_be_processed())

        def test_basic_hbase_crashstorage(self):
            mock_logging = mock.Mock()
            required_config = HBaseCrashStorage.required_config
            required_config.add_option('logger', default=mock_logging)

            config_manager = ConfigurationManager(
              [required_config],
              app_name='testapp',
              app_version='1.0',
              app_description='app description',
              values_source_list=[{
                'logger': mock_logging,
                'hbase_timeout': 100,
                'hbase_host': commonconfig.hbaseHost.default,
                'hbase_port': commonconfig.hbasePort.default,
              }]
            )
            with config_manager.context() as config:
                crashstorage = HBaseCrashStorage(config)
                self.assertEqual(list(crashstorage.new_crashes()), [])

                # data doesn't contain an 'ooid' key
                #raw = '{"name": "Peter"}'
                #self.assertRaises(
                  #CrashIDNotFound,
                  #crashstorage.save_raw_crash,
                  #json.loads(raw),
                  #raw
                #)

                #raw = '{"name":"Peter","ooid":"abc123"}'
                #self.assertRaises(
                  #ValueError,  # missing the 'submitted_timestamp' key
                  #crashstorage.save_raw_crash,
                  #json.loads(raw),
                  #raw
                #)

                raw = ('{"name":"Peter", '
                       '"submitted_timestamp":"%d"}' % time.time())
                crashstorage.save_raw_crash(json.loads(raw), raw, "abc123")

                assert config.logger.info.called
                assert config.logger.info.call_count > 1
                msg_tmpl, msg_arg = config.logger.info.call_args_list[1][0]
                # ie logging.info(<template>, <arg>)
                msg = msg_tmpl % msg_arg
                self.assertTrue('saved' in msg)
                self.assertTrue('abc123' in msg)

                meta = crashstorage.get_raw_crash('abc123')
                assert isinstance(meta, dict)
                self.assertEqual(meta['name'], 'Peter')

                dump = crashstorage.get_raw_dump('abc123')
                assert isinstance(dump, basestring)
                self.assertTrue('"name":"Peter"' in dump)

                # hasn't been processed yet
                self.assertRaises(CrashIDNotFound,
                                  crashstorage.get_processed_crash,
                                  'abc123')

                pro = ('{"name":"Peter","uuid":"abc123", '
                       '"submitted_timestamp":"%d", '
                       '"completeddatetime": "%d"}' %
                       (time.time(), time.time()))

                crashstorage.save_processed(json.loads(pro))
                data = crashstorage.get_processed_crash('abc123')
                self.assertEqual(data['name'], u'Peter')
                assert crashstorage.hbaseConnection.transport.isOpen()
                crashstorage.close()
                transport = crashstorage.hbaseConnection.transport
                self.assertTrue(not transport.isOpen())


class TestHBaseCrashStorage(unittest.TestCase):
    def test_hbase_crashstorage_basic_error(self):
        mock_logging = mock.Mock()
        required_config = HBaseCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'hbase_timeout': 100,
            'hbase_host': commonconfig.hbaseHost.default,
            'hbase_port': commonconfig.hbasePort.default,
          }]
        )

        with config_manager.context() as config:

            hbaseclient_ = 'socorro.external.hbase.crashstorage.hbase_client'
            with mock.patch(hbaseclient_) as hclient:

                class SomeThriftError(Exception):
                    pass

                klass = hclient.HBaseConnectionForCrashReports

                def retry_raiser(*args, **kwargs):
                    raise SomeThriftError('try again')

                klass.put_json_dump.side_effect = ValueError('crap!')
                crashstorage = HBaseCrashStorage(config)
                raw = ('{"name":"Peter", '
                       '"submitted_timestamp":"%d"}' % time.time())

                # Note, we're not expect it to raise an error
                self.assertRaises(ValueError,
                  crashstorage.save_raw_crash,
                  json.loads(raw),
                  raw,
                  "abc123"
                )
                #self.assertEqual(instance.put_json_dump.call_count, 3)

    def test_hbase_crashstorage_error_after_retries(self):
        mock_logging = mock.Mock()
        required_config = HBaseCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'hbase_timeout': 100,
            'hbase_host': commonconfig.hbaseHost.default,
            'hbase_port': commonconfig.hbasePort.default,
            'transaction_executor_class':
                TransactionExecutorWithLimitedBackoff,
            'backoff_delays': [0, 0, 0]
          }]
        )

        with config_manager.context() as config:

            hbaseclient_ = 'socorro.external.hbase.crashstorage.hbase_client'
            with mock.patch(hbaseclient_) as hclient:

                class SomeThriftError(Exception):
                    pass

                klass = hclient.HBaseConnectionForCrashReports
                klass.return_value = klass
                klass.operational_exceptions = (SomeThriftError,)

                def retry_raiser_iterator(*args, **kwargs):
                    return SomeThriftError('try again')

                klass.put_json_dump.side_effect = retry_raiser_iterator()
                crashstorage = HBaseCrashStorage(config)
                raw = ('{"name":"Peter", '
                       '"submitted_timestamp":"%d"}' % time.time())

                self.assertRaises(SomeThriftError,
                  crashstorage.save_raw_crash,
                  json.loads(raw),
                  raw,
                  "abc123"
                )
                self.assertEqual(klass.put_json_dump.call_count, 3)

    def test_hbase_crashstorage_success_after_retries(self):
        mock_logging = mock.Mock()
        required_config = HBaseCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'hbase_timeout': 100,
            'hbase_host': commonconfig.hbaseHost.default,
            'hbase_port': commonconfig.hbasePort.default,
            'transaction_executor_class':
                TransactionExecutorWithLimitedBackoff,
            'backoff_delays': [0, 0, 0]
          }]
        )

        with config_manager.context() as config:

            hbaseclient_ = 'socorro.external.hbase.crashstorage.hbase_client'
            with mock.patch(hbaseclient_) as hclient:

                class SomeThriftError(Exception):
                    pass

                klass = hclient.HBaseConnectionForCrashReports
                klass.return_value = klass
                klass.operational_exceptions = (SomeThriftError,)

                _attempts = [SomeThriftError, SomeThriftError]

                def retry_raiser_iterator(*args, **kwargs):
                    try:
                        raise _attempts.pop(0)
                    except IndexError:
                        return klass

                klass.put_json_dump.side_effect = retry_raiser_iterator
                crashstorage = HBaseCrashStorage(config)
                raw = ('{"name":"Peter", '
                       '"submitted_timestamp":"%d"}' % time.time())

                crashstorage.save_raw_crash(json.loads(raw), raw, "abc123")
                self.assertEqual(klass.put_json_dump.call_count, 3)

    def test_hbase_crashstorage_puts_and_gets(self):
        mock_logging = mock.Mock()
        required_config = HBaseCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'hbase_timeout': 100,
            'hbase_host': commonconfig.hbaseHost.default,
            'hbase_port': commonconfig.hbasePort.default,
            'transaction_executor_class':
                TransactionExecutorWithLimitedBackoff,
            'backoff_delays': [0, 0, 0]
          }]
        )

        with config_manager.context() as config:

            hbaseclient_ = 'socorro.external.hbase.crashstorage.hbase_client'
            with mock.patch(hbaseclient_) as hclient:

                # test save_raw_crash
                raw_crash = {
                  "name": "Peter",
                  "email": "bogus@nowhere.org",
                  "url": "http://embarassing.xxx",
                  "submitted_timestamp": "2012-05-04T15:10:00",
                  "user_id": "000-00-0000",
                }
                fake_binary_dump = "this a bogus binary dump"

                expected_raw_crash = raw_crash
                expected_dump = fake_binary_dump

                # saves us from loooong lines
                klass = hclient.HBaseConnectionForCrashReports

                crashstorage = HBaseCrashStorage(config)
                crashstorage.save_raw_crash(raw_crash, fake_binary_dump, "abc123")
                self.assertEqual(
                  klass.put_json_dump.call_count,
                  1
                )
                a = klass.put_json_dump.call_args
                self.assertEqual(len(a[0]), 4)
                #self.assertEqual(a[0][1], "abc123")
                self.assertEqual(a[0][2], expected_raw_crash)
                self.assertEqual(a[0][3], expected_dump)
                self.assertEqual(a[1], {'number_of_retries': 0})

                # test save_processed
                processed_crash = {
                  "name": "Peter",
                  "uuid": "abc123",
                  "email": "bogus@nowhere.org",
                  "url": "http://embarassing.xxx",
                  "user_id": "000-00-0000",
                }
                expected_processed_crash = {
                  "name": "Peter",
                  "uuid": "abc123",
                }
                crashstorage = HBaseCrashStorage(config)
                crashstorage.save_processed(processed_crash)
                self.assertEqual(klass.put_processed_json.call_count, 1)
                a = klass.put_processed_json.call_args
                self.assertEqual(len(a[0]), 3)
                self.assertEqual(a[0][1], "abc123")
                self.assertEqual(a[0][2], expected_processed_crash)
                self.assertEqual(a[1], {'number_of_retries': 0})

                # test get_raw_crash
                m = mock.Mock(return_value=raw_crash)
                klass.get_json = m
                r = crashstorage.get_raw_crash("abc123")
                self.assertTrue(isinstance(r, DotDict))
                a = klass.get_json.call_args
                self.assertEqual(len(a[0]), 2)
                self.assertEqual(a[0][1], "abc123")
                self.assertEqual(klass.get_json.call_count, 1)
                self.assertEqual(r, expected_raw_crash)

                # test get_raw_dump
                m = mock.Mock(return_value=fake_binary_dump)
                klass.get_dump = m
                r = crashstorage.get_raw_dump("abc123")
                a = klass.get_dump.call_args
                self.assertEqual(len(a[0]), 2)
                self.assertEqual(a[0][1], "abc123")
                self.assertEqual(klass.get_dump.call_count, 1)
                self.assertEqual(r, expected_dump)

                # test get_processed_crash
                m = mock.Mock(return_value=expected_processed_crash)
                klass.get_processed_json = m
                r = crashstorage.get_processed_crash("abc123")
                self.assertTrue(isinstance(r, DotDict))
                a = klass.get_processed_json.call_args
                self.assertEqual(len(a[0]), 2)
                self.assertEqual(a[0][1], "abc123")
                self.assertEqual(klass.get_processed_json.call_count, 1)
                self.assertEqual(r, expected_processed_crash)

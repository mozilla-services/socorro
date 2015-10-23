# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import time
import json
from contextlib import nested

import mock
from nose.tools import eq_, ok_, assert_raises
from configman import ConfigurationManager

from socorro.external.hbase import hbase_client

from socorro.external.crashstorage_base import (
    CrashIDNotFound,
    Redactor,
    MemoryDumpsMapping
)
from socorro.external.hbase.crashstorage import HBaseCrashStorage
from socorro.external.hbase.connection_context import \
     HBaseConnectionContextPooled
from socorro.lib.util import DotDict
from socorro.unittest.config import commonconfig
from socorro.database.transaction_executor import (
  TransactionExecutorWithLimitedBackoff
)
from socorro.unittest.testbase import TestCase


class SomeThriftError(Exception):
    pass

_run_integration_tests = os.environ.get('RUN_HBASE_INTEGRATION_TESTS', False)
if _run_integration_tests in ('false', 'False', 'no', '0'):
    _run_integration_tests = False


if not _run_integration_tests:
    import logging
    logging.warning("Skipping HBase integration tests")

else:

    class TestIntegrationHBaseCrashStorage(TestCase):
        """
        If you ever get this::
            Traceback (most recent call last):
            ...
            socorro.external.hbase.hbase_client.FatalException: the connection
            is not viable.  retries fail:

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
            super(TestIntegrationHBaseCrashStorage, self).tearDown()
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
              }],
              argv_source=[]
            )
            with config_manager.context() as config:
                crashstorage = HBaseCrashStorage(config)
                eq_(list(crashstorage.new_crashes()), [])

                crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'

                raw = ('{"name":"Peter", '
                       '"submitted_timestamp":"%d"}' % time.time())
                fake_raw_dump_1 = 'peter is a swede'
                fake_raw_dump_2 = 'lars is a norseman'
                fake_raw_dump_3 = 'adrian is a frenchman'
                fake_dumps = MemoryDumpsMapping({
                    'upload_file_minidump': fake_raw_dump_1,
                     'lars': fake_raw_dump_2,
                     'adrian': fake_raw_dump_3
                })
                crashstorage.save_raw_crash(json.loads(raw),
                                            fake_dumps,
                                            crash_id)

                assert config.logger.info.called
                assert config.logger.info.call_count > 1
                msg_tmpl, msg_arg = config.logger.info.call_args_list[1][0]
                # ie logging.info(<template>, <arg>)
                msg = msg_tmpl % msg_arg
                ok_('saved' in msg)
                ok_(crash_id in msg)

                raw_crash = crashstorage.get_raw_crash(crash_id)
                assert isinstance(raw_crash, dict)
                eq_(raw_crash['name'], 'Peter')

                dump = crashstorage.get_raw_dump(crash_id)
                assert isinstance(dump, basestring)
                ok_('peter is a swede' in dump)

                dumps = crashstorage.get_raw_dumps(crash_id)
                assert isinstance(dumps, dict)
                ok_('upload_file_minidump' in dumps)
                ok_('lars' in dumps)
                ok_('adrian' in dumps)
                eq_(dumps['upload_file_minidump'],
                                 fake_dumps['upload_file_minidump'])
                eq_(dumps['lars'],
                                 fake_dumps['lars'])
                eq_(dumps['adrian'],
                                 fake_dumps['adrian'])

                # hasn't been processed yet
                assert_raises(CrashIDNotFound,
                                  crashstorage.get_processed,
                                  crash_id)

                pro = ('{"name":"Peter",'
                       '"uuid":"86b58ff2-9708-487d-bfc4-9dac32121214", '
                       '"submitted_timestamp":"%d", '
                       '"completeddatetime": "%d"}' %
                       (time.time(), time.time()))

                crashstorage.save_processed(json.loads(pro))
                data = crashstorage.get_processed(crash_id)
                eq_(data['name'], u'Peter')

                hb_connection = crashstorage.hbaseConnectionPool.connection()
                ok_(hb_connection.transport.isOpen())
                crashstorage.close()
                ok_(not hb_connection.transport.isOpen())


class TestHBaseCrashStorage(TestCase):
    def test_hbase_crashstorage_basic_error(self):
        mock_logging = mock.Mock()
        required_config = HBaseCrashStorage.get_required_config()
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
          }],
          argv_source=[]
        )

        with config_manager.context() as config:
            config.executor_identity = lambda: 'dwight'  # bogus thread id

            hbaseclient_ = 'socorro.external.hbase.crashstorage.hbase_client'
            with mock.patch(hbaseclient_) as hclient:

                klass = hclient.HBaseConnectionForCrashReports

                def retry_raiser(*args, **kwargs):
                    raise SomeThriftError('try again')

                klass.put_json_dump.side_effect = ValueError('crap!')
                crashstorage = HBaseCrashStorage(config)
                raw = ('{"name":"Peter", '
                       '"submitted_timestamp":"%d"}' % time.time())

                # Note, we're not expect it to raise an error
                assert_raises(ValueError,
                  crashstorage.save_raw_crash,
                  json.loads(raw),
                  raw,
                  "abc123"
                )
                #eq_(instance.put_json_dump.call_count, 3)

    def test_hbase_crashstorage_error_after_retries(self):
        cshbaseclient_ = 'socorro.external.hbase.crashstorage.hbase_client'
        cchbaseclient_ = \
            'socorro.external.hbase.connection_context.hbase_client'
        with nested(mock.patch(cshbaseclient_),
                    mock.patch(cchbaseclient_)) as (cshclient, cchclient):

            fake_hbase_client_connection = mock.MagicMock()
            cshclient.HBaseConnectionForCrashReports.return_value = \
                fake_hbase_client_connection
            fake_put_json_method = mock.MagicMock()
            cshclient.HBaseConnectionForCrashReports.put_json_dump = \
                fake_put_json_method
            cchclient.HBaseConnectionForCrashReports.return_value = \
                fake_hbase_client_connection
            fake_hbase_client_connection.hbaseThriftExceptions = \
                (SomeThriftError,)
            fake_put_json_method.side_effect = SomeThriftError('try again')

            config = DotDict({
              'logger': mock.MagicMock(),
              'hbase_timeout': 0,
              'hbase_host': 'somehost',
              'hbase_port': 9090,
              'number_of_retries': 2,
              'hbase_connection_pool_class':
                  HBaseConnectionContextPooled,
              'transaction_executor_class':
                  TransactionExecutorWithLimitedBackoff,
              'backoff_delays': [0, 0, 0],
              'redactor_class': Redactor,
              'forbidden_keys':
                  Redactor.required_config.forbidden_keys.default,
               'executor_identity': lambda: 'dwight'  # bogus thread id
            })
            crashstorage = HBaseCrashStorage(config)
            raw = ('{"name":"Peter", '
                   '"submitted_timestamp":"%d"}' % time.time())
            assert_raises(SomeThriftError,
              crashstorage.save_raw_crash,
              json.loads(raw),
              raw,
              {}
            )
            eq_(fake_put_json_method.call_count, 3)

    def test_hbase_crashstorage_success_after_retries(self):
        cshbaseclient_ = 'socorro.external.hbase.crashstorage.hbase_client'
        cchbaseclient_ = \
            'socorro.external.hbase.connection_context.hbase_client'
        with nested(mock.patch(cshbaseclient_),
                    mock.patch(cchbaseclient_)) as (cshclient, cchclient):

            fake_hbase_client_connection = mock.MagicMock()
            cshclient.HBaseConnectionForCrashReports.return_value = \
                fake_hbase_client_connection
            fake_put_json_method = mock.MagicMock()
            cshclient.HBaseConnectionForCrashReports.put_json_dump = \
                fake_put_json_method
            cchclient.HBaseConnectionForCrashReports.return_value = \
                fake_hbase_client_connection
            fake_hbase_client_connection.hbaseThriftExceptions = \
                (SomeThriftError,)
            _attempts = [SomeThriftError, SomeThriftError]
            def retry_raiser_iterator(*args, **kwargs):
                try:
                    raise _attempts.pop(0)
                except IndexError:
                    return None
            fake_put_json_method.side_effect = retry_raiser_iterator

            config = DotDict({
              'logger': mock.MagicMock(),
              'hbase_timeout': 0,
              'hbase_host': 'somehost',
              'hbase_port': 9090,
              'number_of_retries': 2,
              'hbase_connection_pool_class':
                  HBaseConnectionContextPooled,
              'transaction_executor_class':
                  TransactionExecutorWithLimitedBackoff,
              'backoff_delays': [0, 0, 0],
              'redactor_class': Redactor,
              'forbidden_keys':
                  Redactor.required_config.forbidden_keys.default,
              'executor_identity': lambda: 'dwight'  # bogus thread id
            })
            crashstorage = HBaseCrashStorage(config)
            raw = ('{"name":"Peter", '
                   '"submitted_timestamp":"%d"}' % time.time())
            crashstorage.save_raw_crash(json.loads(raw), raw, "abc123")
            eq_(fake_put_json_method.call_count, 3)

    def test_hbase_crashstorage_puts_and_gets(self):
        mock_logging = mock.Mock()
        required_config = HBaseCrashStorage.get_required_config()
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
            'backoff_delays': [0, 0, 0],
          }],
          argv_source=[]
        )

        with config_manager.context() as config:
            config.executor_identity = lambda: 'dwight'  # bogus thread id

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
                expected_dump_2 = fake_binary_dump + " number 2"

                # saves us from loooong lines
                klass = hclient.HBaseConnectionForCrashReports

                crashstorage = HBaseCrashStorage(config)
                crashstorage.save_raw_crash(raw_crash, fake_binary_dump,
                                            "abc123")
                eq_(
                  klass.put_json_dump.call_count,
                  1
                )
                a = klass.put_json_dump.call_args
                eq_(len(a[0]), 4)
                #eq_(a[0][1], "abc123")
                eq_(a[0][2], expected_raw_crash)
                eq_(a[0][3], expected_dump)
                eq_(a[1], {'number_of_retries': 0})

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
                expected_unredacted_processed_crash = {
                    "name": "Peter",
                    "uuid": "abc123",
                    "email": "bogus@nowhere.org",
                    "url": "http://embarassing.xxx",
                    "user_id": "000-00-0000",
                }
                crashstorage = HBaseCrashStorage(config)
                crashstorage.save_processed(processed_crash)
                eq_(klass.put_processed_json.call_count, 1)
                a = klass.put_processed_json.call_args
                eq_(len(a[0]), 3)
                eq_(a[0][1], "abc123")
                eq_(a[0][2], expected_unredacted_processed_crash)
                eq_(a[1], {'number_of_retries': 0})

                # test get_raw_crash
                m = mock.Mock(return_value=raw_crash)
                klass.get_json = m
                r = crashstorage.get_raw_crash("abc123")
                ok_(isinstance(r, DotDict))
                a = klass.get_json.call_args
                eq_(len(a[0]), 2)
                eq_(a[0][1], "abc123")
                eq_(klass.get_json.call_count, 1)
                eq_(r, expected_raw_crash)

                # test get_raw_dump
                m = mock.Mock(return_value=fake_binary_dump)
                klass.get_dump = m
                r = crashstorage.get_raw_dump("abc123")
                a = klass.get_dump.call_args
                eq_(len(a[0]), 3)
                eq_(a[0][1], "abc123")
                eq_(klass.get_dump.call_count, 1)
                eq_(r, expected_dump)

                # test get_raw_dumps
                m = mock.Mock(return_value={'upload_file_minidump':
                                                fake_binary_dump})
                klass.get_dumps = m
                r = crashstorage.get_raw_dumps("abc123")
                a = klass.get_dumps.call_args
                eq_(len(a[0]), 2)
                eq_(a[0][1], "abc123")
                eq_(klass.get_dumps.call_count, 1)
                eq_(r, {'upload_file_minidump': expected_dump})

                # test get_raw_dumps 2
                m = mock.Mock(return_value={'upload_file_minidump':
                                                fake_binary_dump,
                                            'aux_1':
                                                expected_dump_2})
                klass.get_dumps = m
                r = crashstorage.get_raw_dumps("abc123")
                a = klass.get_dumps.call_args
                eq_(len(a[0]), 2)
                eq_(a[0][1], "abc123")
                eq_(klass.get_dumps.call_count, 1)
                eq_(r, {'upload_file_minidump':
                                         fake_binary_dump,
                                     'aux_1':
                                         expected_dump_2})

                # test get_processed
                m = mock.Mock(return_value=expected_processed_crash)
                klass.get_processed_json = m
                r = crashstorage.get_processed("abc123")
                ok_(isinstance(r, DotDict))
                a = klass.get_processed_json.call_args
                eq_(len(a[0]), 2)
                eq_(a[0][1], "abc123")
                eq_(klass.get_processed_json.call_count, 1)
                eq_(r, expected_processed_crash)

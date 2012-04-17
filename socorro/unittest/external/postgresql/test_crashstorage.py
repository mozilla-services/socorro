import time
import json
import inspect
import unittest
import mock

from psycopg2 import OperationalError

from configman import ConfigurationManager

from socorro.database.transaction_executor import (
  TransactionExecutorWithLimitedBackoff
)
from socorro.external.crashstorage_base import (
  CrashStorageBase, OOIDNotFoundException)
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.unittest.config import commonconfig
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)


DSN = {
  "database_host": databaseHost.default,
  "database_name": databaseName.default,
  "database_user": databaseUserName.default,
  "database_password": databasePassword.default
}

a_processed_crash = {
    "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]],
    "addons_checked": None,
    "address": "0x1c",
    "app_notes": "...",
    "build": "20120309050057",
    "client_crash_date": "2012-04-08 10:52:42.0",
    "completeddatetime": "2012-04-08 10:56:50.902884",
    "cpu_info": "None | 0",
    "cpu_name": "arm",
    "crashedThread": 8,
    "date_processed": "2012-04-08 10:56:41.558922",
    "distributor": None,
    "distributor_version": None,
    "dump": "...",
    "email": "bogus@bogus.com",
    "flash_version": "[blank]",
    "hangid": None,
    "id": 361399767,
    "install_age": 22385,
    "last_crash": None,
    "os_name": "Linux",
    "os_version": "0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ",
    "processor_notes": "SignatureTool: signature truncated due to length",
    "process_type": "plugin",
    "product": "FennecAndroid",
    "PluginFilename": "dwight.txt",
    "PluginName": "wilma",
    "PluginVersion": "69",
    "reason": "SIGSEGV",
    "release_channel": "default",
    "ReleaseChannel": "default",
    "signature": "libxul.so@0x117441c",
    "startedDateTime": "2012-04-08 10:56:50.440752",
    "success": True,
    "topmost_filenames": [],
    "truncated": False,
    "uptime": 170,
    "url": "http://embarasing.porn.com",
    "user_comments": None,
    "user_id": None,
    "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
    "version": "13.0a1",
}



#class TestIntegrationPostgresSQLCrashStorage(unittest.TestCase):
    #"""

    #"""

    #def tearDown(self):
        #self._truncate_reports_table()

    #def _truncate_reports_table(self):
        #print "WORK HARDER!"

    #def test_basic_hbase_crashstorage(self):
        #mock_logging = mock.Mock()
        #required_config = PostgreSQLCrashStorage.required_config
        #required_config.add_option('logger', default=mock_logging)

        #config_manager = ConfigurationManager(
          #[required_config],
          #app_name='testapp',
          #app_version='1.0',
          #app_description='app description',
          #values_source_list=[{
            #'logger': mock_logging,
            #}, DSN]
        #)
        #with config_manager.context() as config:
            #crashstorage = PostgreSQLCrashStorage(config)
            ## data doesn't contain an 'ooid' key
            #raw = '{"name": "Peter"}'
            #processed = '{"name_length": 5,'\
                        #' "date_processed": "2012-03-19T12:12:12"}'
            #print json.loads(processed)
            #self.assertRaises(
              #OOIDNotFoundException,
              #crashstorage.save_raw_and_processed,
              #json.loads(raw),
              #raw,
              #json.loads(processed)
            #)

            #raw = '{"name":"Peter","ooid":"abc123"}'
            #self.assertRaises(
              #ValueError,  # missing the 'submitted_timestamp' key
              #crashstorage.save_raw_and_processed,
              #json.loads(raw),
              #raw,
              #json.loads(processed)
            #)

            #raw = ('{"name":"Peter","ooid":"abc123",'
                   #'"submitted_timestamp":"%d"}' % time.time())
            #result = crashstorage.save_raw(json.loads(raw), raw)
            #self.assertEqual(result, CrashStorageBase.OK)

            #assert config.logger.info.called
            #assert config.logger.info.call_count > 1
            #msg_tmpl, msg_arg = config.logger.info.call_args_list[1][0]
            ## ie logging.info(<template>, <arg>)
            #msg = msg_tmpl % msg_arg
            #self.assertTrue('saved' in msg)
            #self.assertTrue('abc123' in msg)

            #meta = crashstorage.get_raw_json('abc123')
            #assert isinstance(meta, dict)
            #self.assertEqual(meta['name'], 'Peter')

            #dump = crashstorage.get_raw_dump('abc123')
            #assert isinstance(dump, basestring)
            #self.assertTrue('"name":"Peter"' in dump)

            #self.assertTrue(crashstorage.has_ooid('abc123'))
            ## call it again, just to be sure
            #self.assertTrue(crashstorage.has_ooid('abc123'))
            #self.assertTrue(not crashstorage.has_ooid('xyz789'))

            #return


            ## hasn't been processed yet
            #self.assertRaises(hbaseClient.OoidNotFoundException,
                              #crashstorage.get_processed_json,
                              #'abc123')

            #raw = ('{"name":"Peter","ooid":"abc123", '
                   #'"submitted_timestamp":"%d", '
                   #'"completeddatetime": "%d"}' %
                   #(time.time(), time.time()))

            #crashstorage.save_processed('abc123', json.loads(raw))
            #data = crashstorage.get_processed_json('abc123')
            #self.assertEqual(data['name'], u'Peter')
            #assert crashstorage.hbaseConnection.transport.isOpen()
            #crashstorage.close()
            #transport = crashstorage.hbaseConnection.transport
            #self.assertTrue(not transport.isOpen())


class TestPostgresCrashStorage(unittest.TestCase):
    """
    Tests where the actual PostgreSQL part is mocked.
    """

    def test_basic_key_error_on_save_processed(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = PostgreSQLCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database': mock_postgres
          }]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            self.assertTrue(isinstance(database, mock.Mock))

            broken_processed_crash = {
                "product": "Peter",
                "version": "1.0B3",
                "ooid": "abc123",
                "submitted_timestamp": time.time(),
                "unknown_field": 'whatever'
            }
            self.assertRaises(KeyError,
                              crashstorage.save_processed,
                              broken_processed_crash)


    def test_basic_postgres_save_processed_success(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = PostgreSQLCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database': mock_postgres
          }]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            self.assertTrue(isinstance(database, mock.Mock))

            crashstorage.save_processed(a_processed_crash)

            fetch_all_returns = [((666,),), ((23,),), ]
            def fetch_all_func(*args):
                result = fetch_all_returns.pop(0)
                return result

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            m.cursor.return_value.fetchall.side_effect=fetch_all_func
            crashstorage.save_processed(a_processed_crash)
            self.assertEqual(m.cursor.call_count, 4)
            self.assertEqual(m.cursor().fetchall.call_count, 2)
            self.assertEqual(m.cursor().execute.call_count, 4)

            expected_execute_args = (
                (('insert into reports20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarasing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugin_reports20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                     (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('insert into extensions20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                     (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),))

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                self.assertEqual(expected, actual)

    def test_basic_postgres_save_processed_success2(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = PostgreSQLCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database': mock_postgres
          }]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            self.assertTrue(isinstance(database, mock.Mock))

            fetch_all_returns = [((666,),), None, ((23,),), ]
            def fetch_all_func(*args):
                result = fetch_all_returns.pop(0)
                return result

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            m.cursor.return_value.fetchall.side_effect=fetch_all_func
            crashstorage.save_processed(a_processed_crash)
            self.assertEqual(m.cursor.call_count, 5)
            self.assertEqual(m.cursor().fetchall.call_count, 3)
            self.assertEqual(m.cursor().execute.call_count, 5)

            expected_execute_args = (
                (('insert into reports20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarasing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugin_reports20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                     (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('insert into extensions20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                     (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),))

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                self.assertEqual(expected, actual)

    def test_basic_postgres_save_processed_operational_error(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()

        required_config = PostgreSQLCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database': mock_postgres,
            'transaction_executor_class':
                TransactionExecutorWithLimitedBackoff,
            'backoff_delays': [0, 0, 0],
          }]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            crashstorage.database.operational_exceptions = (OperationalError,)

            database = crashstorage.database.return_value = mock.MagicMock()
            self.assertTrue(isinstance(database, mock.Mock))

            fetch_all_returns = [((666,),), None, ((23,),), ]
            def fetch_all_func(*args):
                result = fetch_all_returns.pop(0)
                return result

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            m.cursor.side_effect = OperationalError('bad')
            self.assertRaises(OperationalError,
                              crashstorage.save_processed,
                              a_processed_crash)
            self.assertEqual(m.cursor.call_count, 3)


    def test_basic_postgres_save_processed_succeed_after_failures(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()

        required_config = PostgreSQLCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database': mock_postgres,
            'transaction_executor_class':
                TransactionExecutorWithLimitedBackoff,
            'backoff_delays': [0, 0, 0],
          }]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            crashstorage.database.operational_exceptions = (OperationalError,)

            database = crashstorage.database.return_value = mock.MagicMock()
            self.assertTrue(isinstance(database, mock.Mock))

            fetch_all_returns = [((666,),), None, ((23,),), ]
            def fetch_all_func(*args):
                result = fetch_all_returns.pop(0)
                return result
            fetch_mock = mock.Mock()
            fetch_mock.fetchall.side_effect = fetch_all_func

            connection_trouble = [OperationalError('bad'),
                                  OperationalError('worse'),
                                  ]
            def broken_connection(*args):
                try:
                    result = connection_trouble.pop(0)
                    raise result
                except IndexError:
                    return fetch_mock

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            m.cursor.side_effect = broken_connection
            crashstorage.save_processed(a_processed_crash)
            self.assertEqual(m.cursor.call_count, 7)
            self.assertEqual(m.cursor().fetchall.call_count, 3)
            self.assertEqual(m.cursor().execute.call_count, 5)

            expected_execute_args = (
                (('insert into reports20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarasing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugin_reports20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                     (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('insert into extensions20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                     (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),))

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                self.assertEqual(expected, actual)



# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time
import datetime
import unittest
import mock
import json
from nose.plugins.attrib import attr

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extensions import TRANSACTION_STATUS_IDLE

from configman import ConfigurationManager

from socorro.database.transaction_executor import (
    TransactionExecutorWithLimitedBackoff
)
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.external.crashstorage_base import Redactor
from socorro.lib.datetimeutil import utc_now

from unittestbase import PostgreSQLTestCase

empty_tuple = ()

a_raw_crash = {
    "submitted_timestamp": "2012-04-08 10:52:42.0",
    "ProductName": "Fennicky",
    "Version": "6.02E23",
}

a_bad_raw_crash = {
 'submitted_timestamp': '2013-10-26T17:09:12.818834+00:00',
 'badstuff': u'\udc02',
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
    "exploitability": "high",
    #"flash_process_dump": "flash dump",  # future
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
    "productid": "FA-888888",
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
    "url": "http://embarrassing.porn.com",
    "user_comments": None,
    "user_id": None,
    "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
    "version": "13.0a1",
}

f = open("testcrash/d436f7d7-4053-46d9-bc20-273e42131026.json", "rb")
a_raw_crash_from_disk = f.read(-1)
f.close()

def convert(input):
    if isinstance(input, dict):
        return dict([(convert(key), convert(value)) for key, value in input.iteritems()])
    elif isinstance(input, list):
        return [convert(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

@attr(integration='postgres')
class TestIntegrationPostgresSQLCrashStorage(PostgreSQLTestCase):

    def setUp(self):
        super(TestIntegrationPostgresSQLCrashStorage, self).setUp()

        mock_logging = mock.Mock()
        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        self.config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            # Set these values to what we have in the test class
            # otherwise they grab info from the environment
            'database_hostname': self.config.database_hostname,
            'database_name': self.config.database_name,
            'database_port': self.config.database_port,
            'database_username': self.config.database_username,
            'database_password': self.config.database_password,
           }]
        )

    def tearDown(self):
        pass


    def test_save_raw_crash(self):
        with self.config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            for key,value in config.items():
                print key, value
            cursor = self.connection.cursor()
            try:
                # Our crash comes from October 2013
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS raw_crashes_20131021 (LIKE raw_crashes) INHERITS (raw_crashes)
                """)
                cursor.execute("""
                    TRUNCATE raw_crashes CASCADE
                """)
                self.connection.commit()
            except:
                raise

            crashstorage.save_raw_crash(a_bad_raw_crash, None, 'd436f7d7-4053-46d9-bc20-273e42131026')
            cursor.execute('select count(*) from raw_crashes')
            count, = cursor.fetchone()
            self.assertEqual(count, 1L)

            # Test: pull out JSON data without error
            try:
                cursor.execute("""
                    SELECT 1
                        FROM raw_crashes
                    WHERE
                        json_object_field_text(raw_crash, 'AvailableVirtualMemory')
                            IS NOT NULL
                """)
            except:
                raise
            count, = cursor.fetchone()
            self.assertEqual(count, 1L)

    def test_save_processed(self):
        pass


class TestPostgresCrashStorage(unittest.TestCase):
    """
    Tests where the actual PostgreSQL part is mocked.
    """

    def test_basic_postgres_save_raw_crash(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
          }]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            self.assertTrue(isinstance(database, mock.Mock))

            self.assertTrue('submitted_timestamp' in a_raw_crash)

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            crashstorage.save_raw_crash(
                a_raw_crash,
                '',
                "936ce666-ff3b-4c7a-9674-367fe2120408"
            )
            self.assertEqual(m.cursor.call_count, 3)
            self.assertEqual(m.cursor().execute.call_count, 3)

            expected_execute_args = (
                (('savepoint MainThread', None),),
                (('insert into raw_crashes_20120402 (uuid, raw_crash, date_processed) values (%s, %s, %s)',
                     (
                         '936ce666-ff3b-4c7a-9674-367fe2120408',
                         '{"submitted_timestamp": "2012-04-08 10:52:42.0", "Version": "6.02E23", "ProductName": "Fennicky"}',
                         "2012-04-08 10:52:42.0"
                    )),),
                (('release savepoint MainThread', None),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                expeceted_sql, expected_params = expected[0]
                expeceted_sql = expeceted_sql.replace('\n', '')
                expeceted_sql = expeceted_sql.replace(' ', '')
                actual_sql, actual_params = actual[0]
                actual_sql = actual_sql.replace('\n', '')
                actual_sql = actual_sql.replace(' ', '')
                self.assertEqual(expeceted_sql, actual_sql)
                self.assertEqual(expected_params, actual_params)

    def test_basic_key_error_on_save_processed(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
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
        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
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
            self.assertEqual(m.cursor.call_count, 6)
            self.assertEqual(m.cursor().fetchall.call_count, 2)
            self.assertEqual(m.cursor().execute.call_count, 6)

            expected_execute_args = (
                (('savepoint MainThread', None),),
                (('insert into reports_20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, exploitability, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, productid, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('release savepoint MainThread', None),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                     (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('insert into extensions_20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                     (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),),
                (('release savepoint MainThread', None),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                self.assertEqual(expected, actual)

    def test_basic_postgres_save_processed_success2(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres
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
            self.assertEqual(m.cursor.call_count, 7)
            self.assertEqual(m.cursor().fetchall.call_count, 3)
            self.assertEqual(m.cursor().execute.call_count, 7)

            expected_execute_args = (
                (('savepoint MainThread', None),),
                (('insert into reports_20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, exploitability, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, productid, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('release savepoint MainThread', None),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                     (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('insert into extensions_20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                     (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                self.assertEqual(expected, actual)

    def test_basic_postgres_save_processed_operational_error(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()

        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres,
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

        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'database_class': mock_postgres,
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
            self.assertEqual(m.cursor.call_count, 9)
            self.assertEqual(m.cursor().fetchall.call_count, 3)
            self.assertEqual(m.cursor().execute.call_count, 7)

            expected_execute_args = (
                (('savepoint MainThread', None),),
                (('insert into reports_20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, exploitability, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, productid, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('release savepoint MainThread', None),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                     (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('insert into extensions_20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                     (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                self.assertEqual(expected, actual)

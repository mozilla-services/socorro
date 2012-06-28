import time
import json
import inspect
import unittest
import mock

import psycopg2
from psycopg2 import OperationalError
from psycopg2.extensions import TRANSACTION_STATUS_IDLE

from configman import ConfigurationManager

from socorro.database.transaction_executor import (
  TransactionExecutorWithLimitedBackoff
)
from socorro.external.crashstorage_base import (
  CrashStorageBase, CrashIDNotFound)
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.unittest.config import commonconfig
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)

empty_tuple = ()

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
class DontTestIntegrationPostgresSQLCrashStorage(object):
    """

    """

    def setUp(self):
        assert 'test' in databaseName.default, databaseName.default
        dsn = ('host=%(database_host)s dbname=%(database_name)s '
               'user=%(database_user)s password=%(database_password)s' % DSN)
        self.conn = psycopg2.connect(dsn)
        cursor = self.conn.cursor()
        date_suffix = PostgreSQLCrashStorage._table_suffix_for_crash_id(a_processed_crash['uuid'])
        self.reports_table_name = 'reports%s' % date_suffix
        cursor.execute("""
        DROP TABLE IF EXISTS %(table_name)s;
        CREATE TABLE %(table_name)s (
            id integer NOT NULL,
            client_crash_date timestamp with time zone,
            date_processed timestamp with time zone,
            uuid character varying(50) NOT NULL,
            product character varying(30),
            version character varying(16),
            build character varying(30),
            signature character varying(255),
            url character varying(255),
            install_age integer,
            last_crash integer,
            uptime integer,
            cpu_name character varying(100),
            cpu_info character varying(100),
            reason character varying(255),
            address character varying(20),
            os_name character varying(100),
            os_version character varying(100),
            email character varying(100),
            user_id character varying(50),
            started_datetime timestamp with time zone,
            completed_datetime timestamp with time zone,
            success boolean,
            truncated boolean,
            processor_notes text,
            user_comments character varying(1024),
            app_notes character varying(1024),
            distributor character varying(20),
            distributor_version character varying(20),
            topmost_filenames text,
            addons_checked boolean,
            flash_version text,
            hangid text,
            process_type text,
            release_channel text,
            productid text
        );
        DROP SEQUENCE reports_id_seq;
        CREATE SEQUENCE reports_id_seq
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;

        ALTER TABLE ONLY %(table_name)s ALTER COLUMN id
          SET DEFAULT nextval('reports_id_seq'::regclass);

        DROP TABLE IF EXISTS plugins;
        CREATE TABLE plugins (
            id serial NOT NULL,
            filename text NOT NULL,
            name text NOT NULL
        );

        DROP TABLE IF EXISTS plugins_reports;
        CREATE TABLE plugins_reports (
            report_id integer NOT NULL,
            plugin_id integer NOT NULL,
            date_processed timestamp with time zone,
            version text NOT NULL
        );

        DROP TABLE IF EXISTS plugin_%(table_name)s;
        CREATE TABLE plugin_%(table_name)s (
            report_id integer NOT NULL,
            plugin_id integer NOT NULL,
            date_processed timestamp with time zone,
            version text NOT NULL
        );

        DROP TABLE IF EXISTS extensions;
        CREATE TABLE extensions (
            report_id serial NOT NULL,
            date_processed timestamp with time zone,
            extension_key integer NOT NULL,
            extension_id text NOT NULL,
            extension_version text
        );

        DROP TABLE IF EXISTS extensions%(date_suffix)s;
        CREATE TABLE extensions%(date_suffix)s (
            report_id serial NOT NULL,
            date_processed timestamp with time zone,
            extension_key integer NOT NULL,
            extension_id text NOT NULL,
            extension_version text
        );

        """ % dict(table_name=self.reports_table_name,
                   date_suffix=date_suffix))
        self.conn.commit()
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE

    def test_save_processed(self):
        mock_logging = mock.Mock()
        required_config = PostgreSQLCrashStorage.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            }, DSN]
        )
        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            # data doesn't contain an 'ooid' key
            raw = '{"name": "Peter"}'
            processed = '{"name_length": 5,'\
                        ' "date_processed": "2012-03-19T12:12:12"}'
            crashstorage.save_processed(a_processed_crash)

            cursor = self.conn.cursor()
            cursor.execute('select uuid from %s' % self.reports_table_name)
            report, = cursor.fetchall()
            uuid, = report
            self.assertEqual(uuid, a_processed_crash['uuid'])


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
        required_config = PostgreSQLCrashStorage.required_config
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
                (('insert into reports_20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarasing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('release savepoint MainThread', None),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugin_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
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
        required_config = PostgreSQLCrashStorage.required_config
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
                (('insert into reports_20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarasing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('release savepoint MainThread', None),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugin_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
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

        required_config = PostgreSQLCrashStorage.required_config
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

        required_config = PostgreSQLCrashStorage.required_config
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
                (('insert into reports_20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id',
                     [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarasing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1']),),
                (('release savepoint MainThread', None),),
                (('select id from plugins where filename = %s and name = %s',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                     ('dwight.txt', 'wilma')),),
                (('insert into plugin_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                     (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('insert into extensions_20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                     (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                self.assertEqual(expected, actual)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time

import mock
from nose.tools import eq_, ok_, assert_raises
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extensions import TRANSACTION_STATUS_IDLE

from configman import ConfigurationManager

from socorro.database.transaction_executor import (
    TransactionExecutorWithLimitedBackoff
)
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.unittest.testbase import TestCase

empty_tuple = ()

a_raw_crash = {
    "submitted_timestamp": "2012-04-08 10:52:42.0",
    "ProductName": "Fennicky",
    "Version": "6.02E23",
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
    # "flash_process_dump": "flash dump",  # future
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

a_processed_crash_with_everything_too_long = {
    "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]],
    "addons_checked": None,
    "address": "*" * 25,
    "app_notes": "*" * 1200,
    "build": "*" * 35,
    "client_crash_date": "2012-04-08 10:52:42.0",
    "completeddatetime": "2012-04-08 10:56:50.902884",
    "cpu_info": "*" * 105,
    "cpu_name": "*" * 107,
    "crashedThread": 8,
    "date_processed": "2012-04-08 10:56:41.558922",
    "distributor": '*' * 24,
    "distributor_version": '*' * 25,
    "dump": "...",
    "email": "*" * 101,
    "exploitability": "high",
    # "flash_process_dump": "flash dump",  # future
    "flash_version": "[blank]",
    "hangid": None,
    "id": 361399767,
    "install_age": 22385,
    "last_crash": None,
    "os_name": "*" * 111,
    "os_version": "*" * 102,
    "processor_notes": "SignatureTool: signature truncated due to length",
    "process_type": "plugin",
    "product": "*" * 34,
    "productid": "FA-888888",
    "PluginFilename": "dwight.txt",
    "PluginName": "wilma",
    "PluginVersion": "69",
    "reason": "*" * 257,
    "release_channel": "default",
    "ReleaseChannel": "default",
    "signature": "*" * 300,
    "startedDateTime": "2012-04-08 10:56:50.440752",
    "success": True,
    "topmost_filenames": [],
    "truncated": False,
    "uptime": 170,
    "url": "*" * 288,
    "user_comments": "*" * 1111,
    "user_id": '*' * 80,
    "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
    "version": "*" * 18,
}

a_processed_report_with_everything_truncated = [
    None,
    ("*" * 25)[:20],
    ("*" * 1200)[:1024],
    ("*" * 35)[:30],
    "2012-04-08 10:52:42.0",
    "2012-04-08 10:56:50.902884",
    ("*" * 105)[:100],
    ("*" * 107)[:100],
    "2012-04-08 10:56:41.558922",
    ('*' * 24)[:20],
    ('*' * 25)[:20],
    ("*" * 101)[:100],
    "high",
    "[blank]",
    None,
    22385,
    None,
    ("*" * 111)[:100],
    ("*" * 102)[:100],
    "SignatureTool: signature truncated due to length",
    "plugin",
    ("*" * 34)[:30],
    "FA-888888",
    ("*" * 257)[:255],
    "default",
    ("*" * 300)[:255],
    "2012-04-08 10:56:50.440752",
    True,
    [],
    False,
    170,
    ("*" * 1111)[:1024],
    ('*' * 80)[:50],
    ("*" * 288)[:255],
    "936ce666-ff3b-4c7a-9674-367fe2120408",
    ("*" * 18)[:16],
    "936ce666-ff3b-4c7a-9674-367fe2120408",
]




def remove_whitespace(string):
    return string.replace('\n', '').replace(' ', '')


# class TestIntegrationPostgresSQLCrashStorage(TestCase):
class DontTestIntegrationPostgresSQLCrashStorage(object):

    def _setup_config_manager(self, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}

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
            }, extra_value_source],
            argv_source=[]
        )

        return config_manager

    def setUp(self):

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            DSN = {
                "database_hostname": config.database_hostnamename,
                "database_name": config.database_name,
                "database_username": config.database_username,
                "database_password": config.database_password
            }

        dsn = ('host=%(database_hostname)s dbname=%(database_name)s '
               'user=%(database_username)s password=%(database_password)s'
               % DSN)
        self.conn = psycopg2.connect(dsn)
        cursor = self.conn.cursor()
        date_suffix = PostgreSQLCrashStorage.\
            _table_suffix_for_crash_id(a_processed_crash['uuid'])
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
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            # data doesn't contain an 'ooid' key
            crashstorage.save_processed(a_processed_crash)

            cursor = self.conn.cursor()
            cursor.execute('select uuid from %s' % self.reports_table_name)
            report, = cursor.fetchall()
            uuid, = report
            eq_(uuid, a_processed_crash['uuid'])


class TestPostgresCrashStorage(TestCase):
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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            ok_(isinstance(database, mock.Mock))

            ok_('submitted_timestamp' in a_raw_crash)

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            crashstorage.save_raw_crash(
                a_raw_crash,
                '',
                "936ce666-ff3b-4c7a-9674-367fe2120408"
            )
            eq_(m.cursor.call_count, 1)
            eq_(m.cursor().execute.call_count, 1)

            expected_execute_args = ((("""
                WITH update_raw_crash AS (
                    UPDATE raw_crashes_20120402 SET
                        raw_crash = %(raw_crash)s,
                        date_processed = %(date_processed)s
                    WHERE uuid = %(crash_id)s
                    RETURNING 1
                ),
                insert_raw_crash AS (
                    INSERT into raw_crashes_20120402
                    (uuid, raw_crash, date_processed)
                    ( SELECT
                        %(crash_id)s as uuid,
                        %(raw_crash)s as raw_crash,
                        %(date_processed)s as date_processed
                        WHERE NOT EXISTS (
                            SELECT uuid from raw_crashes_20120402
                            WHERE
                                uuid = %(crash_id)s
                            LIMIT 1
                        )
                    )
                    RETURNING 2
                )
                SELECT * from update_raw_crash
                UNION ALL
                SELECT * from insert_raw_crash
            """, {
                'crash_id': '936ce666-ff3b-4c7a-9674-367fe2120408',
                'raw_crash': '{"submitted_timestamp": "2012-04-08 10:52:42.0", "Version": "6.02E23", "ProductName": "Fennicky"}',
                'date_processed': "2012-04-08 10:52:42.0"
            }),),)

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                expeceted_sql, expected_params = expected[0]
                expeceted_sql = remove_whitespace(expeceted_sql)
                actual_sql, actual_params = actual[0]
                actual_sql = remove_whitespace(actual_sql)
                eq_(expeceted_sql, actual_sql)
                eq_(expected_params, actual_params)

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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            ok_(isinstance(database, mock.Mock))

            broken_processed_crash = {
                "product": "Peter",
                "version": "1.0B3",
                "ooid": "abc123",
                "submitted_timestamp": time.time(),
                "unknown_field": 'whatever'
            }
            assert_raises(KeyError,
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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            ok_(isinstance(database, mock.Mock))

            crashstorage.save_processed(a_processed_crash)

            fetch_all_returns = [((666,),), ((23,),), ]

            def fetch_all_func(*args):
                result = fetch_all_returns.pop(0)
                return result

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            m.cursor.return_value.fetchall.side_effect = fetch_all_func
            crashstorage.save_processed(a_processed_crash)
            eq_(m.cursor.call_count, 7)
            eq_(m.cursor().fetchall.call_count, 2)
            eq_(m.cursor().execute.call_count, 7)

            expected_execute_args = (
                (('WITH update_report AS (UPDATE reports_20120402 SET addons_checked=%s, address=%s, app_notes=%s, build=%s, client_crash_date=%s, completed_datetime=%s, cpu_info=%s, cpu_name=%s, date_processed=%s, distributor=%s, distributor_version=%s, email=%s, exploitability=%s, flash_version=%s, hangid=%s, install_age=%s, last_crash=%s, os_name=%s, os_version=%s, processor_notes=%s, process_type=%s, product=%s, productid=%s, reason=%s, release_channel=%s, signature=%s, started_datetime=%s, success=%s, topmost_filenames=%s, truncated=%s, uptime=%s, user_comments=%s, user_id=%s, url=%s, uuid=%s, version=%s WHERE uuid=%s RETURNING id), insert_report AS (INSERT INTO reports_20120402(addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, exploitability, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, productid, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version)(SELECT%s as addons_checked, %s as address, %s as app_notes, %s as build, %s as client_crash_date, %s as completed_datetime, %s as cpu_info, %s as cpu_name, %s as date_processed, %s as distributor, %s as distributor_version, %s as email, %s as exploitability, %s as flash_version, %s as hangid, %s as install_age, %s as last_crash, %s as os_name, %s as os_version, %s as processor_notes, %s as process_type, %s as product, %s as productid, %s as reason, %s as release_channel, %s as signature, %s as started_datetime, %s as success, %s as topmost_filenames, %s as truncated, %s as uptime, %s as user_comments, %s as user_id, %s as url, %s as uuid, %s as version WHERE NOT EXISTS(SELECT uuid from reports_20120402 WHERE uuid=%s LIMIT 1)) RETURNING id) SELECT * from update_report UNION ALL SELECT * from insert_report',
                    [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1', '936ce666-ff3b-4c7a-9674-367fe2120408',
                    None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1', '936ce666-ff3b-4c7a-9674-367fe2120408']),),
                (('select id from plugins where filename = %s and name = %s',
                    ('dwight.txt', 'wilma')),),
                (('delete from  plugins_reports_20120402 where report_id = %s',
                    (666, )),),
                (('insert into plugins_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                    (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('delete from  extensions_20120402 where report_id = %s',
                    (666, )),),
                (('insert into extensions_20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                    (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),),
                (("""WITH update_processed_crash AS ( UPDATE processed_crashes_20120402 SET processed_crash = %(processed_json)s, date_processed = %(date_processed)s WHERE uuid = %(uuid)s RETURNING 1), insert_processed_crash AS ( INSERT INTO processed_crashes_20120402 (uuid, processed_crash, date_processed) ( SELECT %(uuid)s as uuid, %(processed_json)s as processed_crash, %(date_processed)s as date_processed WHERE NOT EXISTS ( SELECT uuid from processed_crashes_20120402 WHERE uuid = %(uuid)s LIMIT 1)) RETURNING 2) SELECT * from update_processed_crash UNION ALL SELECT * from insert_processed_crash """,
                    {'uuid': '936ce666-ff3b-4c7a-9674-367fe2120408', 'processed_json': '{"startedDateTime": "2012-04-08 10:56:50.440752", "crashedThread": 8, "cpu_info": "None | 0", "PluginName": "wilma", "install_age": 22385, "topmost_filenames": [], "user_comments": null, "user_id": null, "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408", "flash_version": "[blank]", "os_version": "0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ", "PluginVersion": "69", "addons_checked": null, "completeddatetime": "2012-04-08 10:56:50.902884", "productid": "FA-888888", "success": true, "exploitability": "high", "client_crash_date": "2012-04-08 10:52:42.0", "PluginFilename": "dwight.txt", "dump": "...", "truncated": false, "product": "FennecAndroid", "distributor": null, "processor_notes": "SignatureTool: signature truncated due to length", "uptime": 170, "release_channel": "default", "distributor_version": null, "process_type": "plugin", "id": 361399767, "hangid": null, "version": "13.0a1", "build": "20120309050057", "ReleaseChannel": "default", "email": "bogus@bogus.com", "app_notes": "...", "os_name": "Linux", "last_crash": null, "date_processed": "2012-04-08 10:56:41.558922", "cpu_name": "arm", "reason": "SIGSEGV", "address": "0x1c", "url": "http://embarrassing.porn.com", "signature": "libxul.so@0x117441c", "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]]}', 'date_processed': '2012-04-08 10:56:41.558922'}),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                expected_sql, expected_params = expected[0]
                expected_sql = remove_whitespace(expected_sql)
                actual_sql, actual_params = actual[0]
                actual_sql = remove_whitespace(actual_sql)
                eq_(expected_sql, actual_sql)
                eq_(expected_params, actual_params)

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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            database = crashstorage.database.return_value = mock.MagicMock()
            ok_(isinstance(database, mock.Mock))

            fetch_all_returns = [((666,),), None, ((23,),), ]

            def fetch_all_func(*args):
                result = fetch_all_returns.pop(0)
                return result

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            m.cursor.return_value.fetchall.side_effect = fetch_all_func
            crashstorage.save_processed(a_processed_crash)
            eq_(m.cursor.call_count, 8)
            eq_(m.cursor().fetchall.call_count, 3)
            eq_(m.cursor().execute.call_count, 8)

            expected_execute_args = (
                (('WITH update_report AS (UPDATE reports_20120402 SET addons_checked=%s, address=%s, app_notes=%s, build=%s, client_crash_date=%s, completed_datetime=%s, cpu_info=%s, cpu_name=%s, date_processed=%s, distributor=%s, distributor_version=%s, email=%s, exploitability=%s, flash_version=%s, hangid=%s, install_age=%s, last_crash=%s, os_name=%s, os_version=%s, processor_notes=%s, process_type=%s, product=%s, productid=%s, reason=%s, release_channel=%s, signature=%s, started_datetime=%s, success=%s, topmost_filenames=%s, truncated=%s, uptime=%s, user_comments=%s, user_id=%s, url=%s, uuid=%s, version=%s WHERE uuid=%s RETURNING id), insert_report AS (INSERT INTO reports_20120402(addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, exploitability, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, productid, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version)(SELECT%s as addons_checked, %s as address, %s as app_notes, %s as build, %s as client_crash_date, %s as completed_datetime, %s as cpu_info, %s as cpu_name, %s as date_processed, %s as distributor, %s as distributor_version, %s as email, %s as exploitability, %s as flash_version, %s as hangid, %s as install_age, %s as last_crash, %s as os_name, %s as os_version, %s as processor_notes, %s as process_type, %s as product, %s as productid, %s as reason, %s as release_channel, %s as signature, %s as started_datetime, %s as success, %s as topmost_filenames, %s as truncated, %s as uptime, %s as user_comments, %s as user_id, %s as url, %s as uuid, %s as version WHERE NOT EXISTS(SELECT uuid from reports_20120402 WHERE uuid=%s LIMIT 1)) RETURNING id) SELECT * from update_report UNION ALL SELECT * from insert_report',
                    [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1', '936ce666-ff3b-4c7a-9674-367fe2120408',
                    None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1', '936ce666-ff3b-4c7a-9674-367fe2120408']),),
                (('select id from plugins where filename = %s and name = %s',
                    ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                    ('dwight.txt', 'wilma')),),
                (('delete from  plugins_reports_20120402 where report_id = %s',
                    (666, )),),
                (('insert into plugins_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                    (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('delete from  extensions_20120402 where report_id = %s',
                    (666, )),),
                (('insert into extensions_20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                    (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),),
                (("""WITH update_processed_crash AS ( UPDATE processed_crashes_20120402 SET processed_crash = %(processed_json)s, date_processed = %(date_processed)s WHERE uuid = %(uuid)s RETURNING 1), insert_processed_crash AS ( INSERT INTO processed_crashes_20120402 (uuid, processed_crash, date_processed) ( SELECT %(uuid)s as uuid, %(processed_json)s as processed_crash, %(date_processed)s as date_processed WHERE NOT EXISTS ( SELECT uuid from processed_crashes_20120402 WHERE uuid = %(uuid)s LIMIT 1)) RETURNING 2) SELECT * from update_processed_crash UNION ALL SELECT * from insert_processed_crash """,
                    {'uuid': '936ce666-ff3b-4c7a-9674-367fe2120408', 'processed_json': '{"startedDateTime": "2012-04-08 10:56:50.440752", "crashedThread": 8, "cpu_info": "None | 0", "PluginName": "wilma", "install_age": 22385, "topmost_filenames": [], "user_comments": null, "user_id": null, "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408", "flash_version": "[blank]", "os_version": "0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ", "PluginVersion": "69", "addons_checked": null, "completeddatetime": "2012-04-08 10:56:50.902884", "productid": "FA-888888", "success": true, "exploitability": "high", "client_crash_date": "2012-04-08 10:52:42.0", "PluginFilename": "dwight.txt", "dump": "...", "truncated": false, "product": "FennecAndroid", "distributor": null, "processor_notes": "SignatureTool: signature truncated due to length", "uptime": 170, "release_channel": "default", "distributor_version": null, "process_type": "plugin", "id": 361399767, "hangid": null, "version": "13.0a1", "build": "20120309050057", "ReleaseChannel": "default", "email": "bogus@bogus.com", "app_notes": "...", "os_name": "Linux", "last_crash": null, "date_processed": "2012-04-08 10:56:41.558922", "cpu_name": "arm", "reason": "SIGSEGV", "address": "0x1c", "url": "http://embarrassing.porn.com", "signature": "libxul.so@0x117441c", "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]]}', 'date_processed': '2012-04-08 10:56:41.558922'}),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                expected_sql, expected_params = expected[0]
                expected_sql = remove_whitespace(expected_sql)
                actual_sql, actual_params = actual[0]
                actual_sql = remove_whitespace(actual_sql)
                eq_(expected_sql, actual_sql)
                eq_(expected_params, actual_params)

    def test_basic_postgres_save_processed_success_3_truncations(self):

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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            with mock.patch(
                'socorro.external.postgresql.crashstorage.single_value_sql'
            ) as mocked_sql_execute:
                fake_connection = mock.Mock(),
                crashstorage._save_processed_report(
                    fake_connection,
                    a_processed_crash_with_everything_too_long
                )
                mocked_sql_execute.assert_called_with(
                    fake_connection,
                    "\n        WITH\n        update_report AS (\n            UPDATE reports_20120402 SET\n                addons_checked = %s, address = %s, app_notes = %s, build = %s, client_crash_date = %s, completed_datetime = %s, cpu_info = %s, cpu_name = %s, date_processed = %s, distributor = %s, distributor_version = %s, email = %s, exploitability = %s, flash_version = %s, hangid = %s, install_age = %s, last_crash = %s, os_name = %s, os_version = %s, processor_notes = %s, process_type = %s, product = %s, productid = %s, reason = %s, release_channel = %s, signature = %s, started_datetime = %s, success = %s, topmost_filenames = %s, truncated = %s, uptime = %s, user_comments = %s, user_id = %s, url = %s, uuid = %s, version = %s\n            WHERE uuid = %s\n            RETURNING id\n        ),\n        insert_report AS (\n            INSERT INTO reports_20120402 (addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, exploitability, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, productid, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version)\n            ( SELECT\n                %s as addons_checked, %s as address, %s as app_notes, %s as build, %s as client_crash_date, %s as completed_datetime, %s as cpu_info, %s as cpu_name, %s as date_processed, %s as distributor, %s as distributor_version, %s as email, %s as exploitability, %s as flash_version, %s as hangid, %s as install_age, %s as last_crash, %s as os_name, %s as os_version, %s as processor_notes, %s as process_type, %s as product, %s as productid, %s as reason, %s as release_channel, %s as signature, %s as started_datetime, %s as success, %s as topmost_filenames, %s as truncated, %s as uptime, %s as user_comments, %s as user_id, %s as url, %s as uuid, %s as version\n                WHERE NOT EXISTS (\n                    SELECT uuid from reports_20120402\n                    WHERE\n                        uuid = %s\n                    LIMIT 1\n                )\n            )\n            RETURNING id\n        )\n        SELECT * from update_report\n        UNION ALL\n        SELECT * from insert_report\n        ",
                    a_processed_report_with_everything_truncated * 2
                )

    def test_basic_postgres_save_processed_operational_error(self):

        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()

        required_config = PostgreSQLCrashStorage.get_required_config()
        required_config.add_option(
            'logger',
            default=mock_logging)

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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            crashstorage.database.operational_exceptions = (OperationalError,)

            database = crashstorage.database.return_value = mock.MagicMock()
            ok_(isinstance(database, mock.Mock))

            m = mock.MagicMock()
            m.__enter__.return_value = m
            database = crashstorage.database.return_value = m
            m.cursor.side_effect = OperationalError('bad')
            assert_raises(OperationalError,
                          crashstorage.save_processed,
                          a_processed_crash)
            eq_(m.cursor.call_count, 3)

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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            crashstorage = PostgreSQLCrashStorage(config)
            crashstorage.database.operational_exceptions = (OperationalError,)

            database = crashstorage.database.return_value = mock.MagicMock()
            ok_(isinstance(database, mock.Mock))

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
            eq_(m.cursor.call_count, 10)
            eq_(m.cursor().fetchall.call_count, 3)
            eq_(m.cursor().execute.call_count, 8)

            expected_execute_args = (
                (('WITH update_report AS (UPDATE reports_20120402 SET addons_checked=%s, address=%s, app_notes=%s, build=%s, client_crash_date=%s, completed_datetime=%s, cpu_info=%s, cpu_name=%s, date_processed=%s, distributor=%s, distributor_version=%s, email=%s, exploitability=%s, flash_version=%s, hangid=%s, install_age=%s, last_crash=%s, os_name=%s, os_version=%s, processor_notes=%s, process_type=%s, product=%s, productid=%s, reason=%s, release_channel=%s, signature=%s, started_datetime=%s, success=%s, topmost_filenames=%s, truncated=%s, uptime=%s, user_comments=%s, user_id=%s, url=%s, uuid=%s, version=%s WHERE uuid=%s RETURNING id), insert_report AS (INSERT INTO reports_20120402(addons_checked, address, app_notes, build, client_crash_date, completed_datetime, cpu_info, cpu_name, date_processed, distributor, distributor_version, email, exploitability, flash_version, hangid, install_age, last_crash, os_name, os_version, processor_notes, process_type, product, productid, reason, release_channel, signature, started_datetime, success, topmost_filenames, truncated, uptime, user_comments, user_id, url, uuid, version)(SELECT%s as addons_checked, %s as address, %s as app_notes, %s as build, %s as client_crash_date, %s as completed_datetime, %s as cpu_info, %s as cpu_name, %s as date_processed, %s as distributor, %s as distributor_version, %s as email, %s as exploitability, %s as flash_version, %s as hangid, %s as install_age, %s as last_crash, %s as os_name, %s as os_version, %s as processor_notes, %s as process_type, %s as product, %s as productid, %s as reason, %s as release_channel, %s as signature, %s as started_datetime, %s as success, %s as topmost_filenames, %s as truncated, %s as uptime, %s as user_comments, %s as user_id, %s as url, %s as uuid, %s as version WHERE NOT EXISTS(SELECT uuid from reports_20120402 WHERE uuid=%s LIMIT 1)) RETURNING id) SELECT * from update_report UNION ALL SELECT * from insert_report',
                    [None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1', '936ce666-ff3b-4c7a-9674-367fe2120408',
                    None, '0x1c', '...', '20120309050057', '2012-04-08 10:52:42.0', '2012-04-08 10:56:50.902884', 'None | 0', 'arm', '2012-04-08 10:56:41.558922', None, None, 'bogus@bogus.com', 'high', '[blank]', None, 22385, None, 'Linux', '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ', 'SignatureTool: signature truncated due to length', 'plugin', 'FennecAndroid', 'FA-888888', 'SIGSEGV', 'default', 'libxul.so@0x117441c', '2012-04-08 10:56:50.440752', True, [], False, 170, None, None, 'http://embarrassing.porn.com', '936ce666-ff3b-4c7a-9674-367fe2120408', '13.0a1', '936ce666-ff3b-4c7a-9674-367fe2120408']),),
                (('select id from plugins where filename = %s and name = %s',
                    ('dwight.txt', 'wilma')),),
                (('insert into plugins (filename, name) values (%s, %s) returning id',
                    ('dwight.txt', 'wilma')),),
                (('delete from  plugins_reports_20120402 where report_id = %s',
                    (666, )),),
                (('insert into plugins_reports_20120402     (report_id, plugin_id, date_processed, version) values     (%s, %s, %s, %s)',
                    (666, 23, '2012-04-08 10:56:41.558922', '69')),),
                (('delete from extensions_20120402 where report_id = %s',
                    (666, )),),
                (('insert into extensions_20120402     (report_id, date_processed, extension_key, extension_id,      extension_version)values (%s, %s, %s, %s, %s)',
                    (666, '2012-04-08 10:56:41.558922', 0, '{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1')),),
                (("""WITH update_processed_crash AS ( UPDATE processed_crashes_20120402 SET processed_crash = %(processed_json)s, date_processed = %(date_processed)s WHERE uuid = %(uuid)s RETURNING 1), insert_processed_crash AS ( INSERT INTO processed_crashes_20120402 (uuid, processed_crash, date_processed) ( SELECT %(uuid)s as uuid, %(processed_json)s as processed_crash, %(date_processed)s as date_processed WHERE NOT EXISTS ( SELECT uuid from processed_crashes_20120402 WHERE uuid = %(uuid)s LIMIT 1)) RETURNING 2) SELECT * from update_processed_crash UNION ALL SELECT * from insert_processed_crash """,
                    {'uuid': '936ce666-ff3b-4c7a-9674-367fe2120408', 'processed_json': '{"startedDateTime": "2012-04-08 10:56:50.440752", "crashedThread": 8, "cpu_info": "None | 0", "PluginName": "wilma", "install_age": 22385, "topmost_filenames": [], "user_comments": null, "user_id": null, "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408", "flash_version": "[blank]", "os_version": "0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ", "PluginVersion": "69", "addons_checked": null, "completeddatetime": "2012-04-08 10:56:50.902884", "productid": "FA-888888", "success": true, "exploitability": "high", "client_crash_date": "2012-04-08 10:52:42.0", "PluginFilename": "dwight.txt", "dump": "...", "truncated": false, "product": "FennecAndroid", "distributor": null, "processor_notes": "SignatureTool: signature truncated due to length", "uptime": 170, "release_channel": "default", "distributor_version": null, "process_type": "plugin", "id": 361399767, "hangid": null, "version": "13.0a1", "build": "20120309050057", "ReleaseChannel": "default", "email": "bogus@bogus.com", "app_notes": "...", "os_name": "Linux", "last_crash": null, "date_processed": "2012-04-08 10:56:41.558922", "cpu_name": "arm", "reason": "SIGSEGV", "address": "0x1c", "url": "http://embarrassing.porn.com", "signature": "libxul.so@0x117441c", "addons": [["{1a5dabbd-0e74-41da-b532-a364bb552cab}", "1.0.4.1"]]}', 'date_processed': '2012-04-08 10:56:41.558922'}),),
            )

            actual_execute_args = m.cursor().execute.call_args_list
            for expected, actual in zip(expected_execute_args,
                                        actual_execute_args):
                expected_sql, expected_params = expected[0]
                expected_sql = remove_whitespace(expected_sql)
                actual_sql, actual_params = actual[0]
                actual_sql = remove_whitespace(actual_sql)
                eq_(expected_sql, actual_sql)
                eq_(expected_params, actual_params)

    def test_get_raw_crash(self):
        mock_logging = mock.Mock()
        mock_postgres = mock.Mock()
        mock_postgres.return_value = mock.MagicMock()

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
            }],
            argv_source=[]
        )

        with config_manager.context() as config:
            a_crash_id = "936ce666-ff3b-4c7a-9674-367fe2120408"
            crashstorage = PostgreSQLCrashStorage(config)
            connection = crashstorage.database.return_value.__enter__.return_value
            connection.cursor.return_value.fetchall.return_value = [[
                {
                    'uuid': a_crash_id,
                }
            ]]

            a_crash = crashstorage.get_raw_crash(a_crash_id)

            ok_(a_crash['uuid'] == a_crash_id)
            connection.cursor.return_value.execute. \
                assert_called_with(
                    'select raw_crash from raw_crash_20120402 where uuid = %s',
                    ('936ce666-ff3b-4c7a-9674-367fe2120408',)
                )

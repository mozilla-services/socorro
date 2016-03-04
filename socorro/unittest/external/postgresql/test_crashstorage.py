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
from configman.dotdict import DotDict

from socorro.database.transaction_executor import (
    TransactionExecutorWithLimitedBackoff,
    TransactionExecutorWithInfiniteBackoff
)
from socorro.external.postgresql.crashstorage import (
    PostgreSQLBasicCrashStorage,
    PostgreSQLCrashStorage,
)
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


class TestPostgresBasicCrashStorage(TestCase):
    """
    Tests where the actual PostgreSQL part is mocked.
    """

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
            crashstorage = PostgreSQLBasicCrashStorage(config)
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
        config =  DotDict()
        config.database_class = mock.MagicMock()
        config.transaction_executor_class = TransactionExecutorWithInfiniteBackoff
        config.redactor_class = mock.Mock()
        config.backoff_delays = [1]
        config.wait_log_interval = 10
        config.logger = mock.Mock()

        mocked_database_connection_source = config.database_class.return_value
        mocked_connection = (
            mocked_database_connection_source.return_value
            .__enter__.return_value
        )
        mocked_cursor = mocked_connection.cursor.return_value.__enter__.return_value

        # the call to be tested
        crashstorage = PostgreSQLCrashStorage(config)
        crashstorage.save_processed(a_processed_crash)

        eq_(mocked_database_connection_source.call_count, 1)
        eq_(mocked_cursor.execute.call_count, 5)
        # check correct fragments
        sql_fragments = [
            "UPDATE reports_20120402",
            'select id from plugins',
            'delete from plugins_reports_20120402',
            'insert into plugins_reports_20120402',
        ]
        for a_call, a_fragment in zip(mocked_cursor.execute.call_args_list, sql_fragments):
            ok_(a_fragment in a_call[0][0])

    def test_basic_postgres_save_processed_success_2(self):
        config =  DotDict()
        config.database_class = mock.MagicMock()
        config.transaction_executor_class = TransactionExecutorWithInfiniteBackoff
        config.redactor_class = mock.Mock()
        config.backoff_delays = [1]
        config.wait_log_interval = 10
        config.logger = mock.Mock()

        mocked_database_connection_source = config.database_class.return_value
        mocked_connection = (
            mocked_database_connection_source.return_value
            .__enter__.return_value
        )
        mocked_cursor = mocked_connection.cursor.return_value.__enter__.return_value
        fetch_all_returns = [((666,),), None, ((23,),), ]
        def fetch_all_func(*args):
            result = fetch_all_returns.pop(0)
            return result
        mocked_cursor.fetchall =  fetch_all_func

        # the call to be tested
        crashstorage = PostgreSQLCrashStorage(config)
        crashstorage.save_processed(a_processed_crash)

        eq_(mocked_database_connection_source.call_count, 1)
        eq_(mocked_cursor.execute.call_count, 6)
        # check correct fragments
        sql_fragments = [
            "UPDATE reports_20120402",
            'select id from plugins',
            'insert into plugins',
            'delete from plugins_reports_20120402',
            'insert into plugins_reports_20120402',
        ]
        for a_call, a_fragment in zip(mocked_cursor.execute.call_args_list, sql_fragments):
            ok_(a_fragment in a_call[0][0])

    def test_basic_postgres_save_processed_success_3_truncations(self):
        config =  DotDict()
        config.database_class = mock.MagicMock()
        config.transaction_executor_class = TransactionExecutorWithInfiniteBackoff
        config.redactor_class = mock.Mock()
        config.backoff_delays = [1]
        config.wait_log_interval = 10
        config.logger = mock.Mock()

        mocked_database_connection_source = config.database_class.return_value
        mocked_connection = (
            mocked_database_connection_source.return_value
            .__enter__.return_value
        )
        mocked_cursor = mocked_connection.cursor.return_value.__enter__.return_value

        # the call to be tested
        crashstorage = PostgreSQLCrashStorage(config)
        crashstorage.save_processed(a_processed_crash_with_everything_too_long)

        eq_(mocked_database_connection_source.call_count, 1)
        eq_(mocked_cursor.execute.call_count, 5)
        # check correct fragments

        first_call = mocked_cursor.execute.call_args_list[0]
        eq_(
            first_call[0][1],
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
            eq_(m.cursor.return_value.__enter__.return_value.execute.call_count, 1)

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
        config =  DotDict()
        config.database_class = mock.MagicMock()
        config.transaction_executor_class = TransactionExecutorWithInfiniteBackoff
        config.redactor_class = mock.Mock()
        config.backoff_delays = [1]
        config.wait_log_interval = 10
        config.logger = mock.Mock()

        mocked_database_connection_source = config.database_class.return_value
        mocked_connection = (
            mocked_database_connection_source.return_value
            .__enter__.return_value
        )
        mocked_cursor = mocked_connection.cursor.return_value.__enter__.return_value

        # the call to be tested
        crashstorage = PostgreSQLCrashStorage(config)
        crashstorage.save_processed(a_processed_crash)

        eq_(mocked_database_connection_source.call_count, 1)
        eq_(mocked_cursor.execute.call_count, 5)
        # check correct fragments
        sql_fragments = [
            "UPDATE reports_20120402",
            'select id from plugins',
            'delete from plugins_reports_20120402',
            'insert into plugins_reports_20120402',
            'UPDATE processed_crashes_20120402'
        ]
        for a_call, a_fragment in zip(mocked_cursor.execute.call_args_list, sql_fragments):
            ok_(a_fragment in a_call[0][0])

    def test_basic_postgres_save_processed_success_2(self):
        config =  DotDict()
        config.database_class = mock.MagicMock()
        config.transaction_executor_class = TransactionExecutorWithInfiniteBackoff
        config.redactor_class = mock.Mock()
        config.backoff_delays = [1]
        config.wait_log_interval = 10
        config.logger = mock.Mock()

        mocked_database_connection_source = config.database_class.return_value
        mocked_connection = (
            mocked_database_connection_source.return_value
            .__enter__.return_value
        )
        mocked_cursor = mocked_connection.cursor.return_value.__enter__.return_value
        fetch_all_returns = [((666,),), None, ((23,),), ]
        def fetch_all_func(*args):
            result = fetch_all_returns.pop(0)
            return result
        mocked_cursor.fetchall =  fetch_all_func

        # the call to be tested
        crashstorage = PostgreSQLCrashStorage(config)
        crashstorage.save_processed(a_processed_crash)

        eq_(mocked_database_connection_source.call_count, 1)
        eq_(mocked_cursor.execute.call_count, 6)
        # check correct fragments
        sql_fragments = [
            "UPDATE reports_20120402",
            'select id from plugins',
            'insert into plugins',
            'delete from plugins_reports_20120402',
            'insert into plugins_reports_20120402',
            'UPDATE processed_crashes_20120402'
        ]
        for a_call, a_fragment in zip(mocked_cursor.execute.call_args_list, sql_fragments):
            ok_(a_fragment in a_call[0][0])

    def test_basic_postgres_save_processed_success_3_truncations(self):
        config =  DotDict()
        config.database_class = mock.MagicMock()
        config.transaction_executor_class = TransactionExecutorWithInfiniteBackoff
        config.redactor_class = mock.Mock()
        config.backoff_delays = [1]
        config.wait_log_interval = 10
        config.logger = mock.Mock()

        mocked_database_connection_source = config.database_class.return_value
        mocked_connection = (
            mocked_database_connection_source.return_value
            .__enter__.return_value
        )
        mocked_cursor = mocked_connection.cursor.return_value.__enter__.return_value

        # the call to be tested
        crashstorage = PostgreSQLCrashStorage(config)
        crashstorage.save_processed(a_processed_crash_with_everything_too_long)

        eq_(mocked_database_connection_source.call_count, 1)
        eq_(mocked_cursor.execute.call_count, 5)
        # check correct fragments

        first_call = mocked_cursor.execute.call_args_list[0]
        eq_(
            first_call[0][1],
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
            connection.cursor.return_value.__enter__.return_value.fetchall.return_value = [[
                {
                    'uuid': a_crash_id,
                }
            ]]

            a_crash = crashstorage.get_raw_crash(a_crash_id)

            ok_(a_crash['uuid'] == a_crash_id)
            connection.cursor.return_value.__enter__.return_value.execute. \
                assert_called_with(
                    'select raw_crash from raw_crashes_20120402 where uuid = %s',
                    ('936ce666-ff3b-4c7a-9674-367fe2120408',)
                )

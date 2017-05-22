# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from nose.tools import eq_, ok_, assert_raises
from configman import ConfigurationManager, Namespace
from mock import Mock

from socorro.lib import (
    MissingArgumentError,
    ResourceNotFound,
    ResourceUnavailable
)
from socorro.external.postgresql import crash_data, crashstorage
from socorro.unittest.testbase import TestCase
from socorro.unittest.external.postgresql.test_crashstorage import (
    a_processed_crash
)


class TestIntegrationPostgresCrashData(TestCase):

    def setUp(self):
        super(TestIntegrationPostgresCrashData, self).setUp()
        self.config_manager = self._common_config_setup()
        self._truncate()
        with self.config_manager.context() as config:
            store = crashstorage.PostgreSQLCrashStorage(config.database)

        # First we need to create the partitioned tables.
        connection = store.database.connection()
        cursor = connection.cursor()
        table_data = (['reports', '1', '{id,uuid}',
             '{date_processed,hangid,"product,version",reason,signature,url}',
             '{}', 'date_processed', 'TIMESTAMPTZ'],
            ['plugins_reports', '2', '{"report_id,plugin_id"}',
             '{"report_id,date_processed"}',
             '{}', 'date_processed', 'TIMESTAMPTZ'],
            ['raw_crashes', '4', '{uuid}', '{}', '{}', 'date_processed',
                'TIMESTAMPTZ'],
            ['processed_crashes', '6', '{uuid}', '{}', '{}', 'date_processed',
                'TIMESTAMPTZ'])
        query = """
            INSERT INTO report_partition_info
            (table_name, build_order, keys, indexes, fkeys, partition_column,
             timetype)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        cursor.executemany(query, table_data)
        connection.commit()

        cursor.execute("SELECT weekly_report_partitions(2, '2012-03-14');")
        cursor.execute("SELECT weekly_report_partitions(2, '2012-08-20');")
        connection.commit()

        # A complete crash report (raw, dump and processed)
        fake_raw_dump_1 = 'peter is a swede'
        fake_raw_dump_2 = 'lars is a norseman'
        fake_raw_dump_3 = 'adrian is a frenchman'
        fake_dumps = {'upload_file_minidump': fake_raw_dump_1,
                      'lars': fake_raw_dump_2,
                      'adrian': fake_raw_dump_3}
        fake_raw = {
            'name': 'Peter',
            'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314',
            'legacy_processing': 0,
            'submitted_timestamp': '2012-03-15T00:00:00',
        }
        fake_processed = a_processed_crash.copy()
        fake_processed.update({
            'name': 'Peter',
            'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314',
            'completeddatetime': '2012-03-15T00:00:00',
            'date_processed': '2012-03-15T00:00:00',
            'email': 'peter@fake.org',
        })

        store.save_raw_crash(
            fake_raw,
            fake_dumps,
            '114559a5-d8e6-428c-8b88-1c1f22120314'
        )
        store.save_processed(fake_processed)

        # A non-processed crash report
        fake_raw = {
            'name': 'Adrian',
            'uuid': '58727744-12f5-454a-bcf5-f688a2120821',
            'legacy_processing': 0,
            'submitted_timestamp': '2012-08-24'
        }

        store.save_raw_crash(
            fake_raw,
            fake_dumps,
            '58727744-12f5-454a-bcf5-f688a2120821'
        )

    def tearDown(self):
        self._truncate()
        super(TestIntegrationPostgresCrashData, self).tearDown()

    def _truncate(self):
        with self.config_manager.context() as config:
            store = crashstorage.PostgreSQLCrashStorage(config.database)

            connection = store.database.connection()
            cursor = connection.cursor()
            cursor.execute("""
                TRUNCATE
                    report_partition_info,
                    plugins
                CASCADE
            """)
            connection.commit()

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = Namespace()
        required_config.namespace('database')
        required_config.database.crashstorage_class = \
            crashstorage.PostgreSQLCrashStorage
        required_config.database.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
            [required_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[{'database': {
                'logger': mock_logging,
                'database_name': 'socorro_integration_test',
                'database_hostname': os.environ['database_hostname'],
                'database_username': os.environ['database_username'],
                'database_password': os.environ['database_password'],
            }}]
        )
        return config_manager

    def test_get(self):
        with self.config_manager.context() as config:

            service = crash_data.CrashData(config=config)
            params = {
                'datatype': 'raw',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'
            }

            # get a raw crash
            params['datatype'] = 'meta'
            res_expected = {
                'name': 'Peter',
                'legacy_processing': 0,
                'submitted_timestamp': '2012-03-15T00:00:00',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'
            }
            res = service.get(**params)
            eq_(res, res_expected)

            # get a processed crash
            params['datatype'] = 'processed'
            res_expected = a_processed_crash.copy()
            res_expected.update({
                'name': 'Peter',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314',
                'completeddatetime': '2012-01-01T00:00:00'
            })
            res = service.get(**params)

            eq_(res['name'], 'Peter')
            ok_('url' not in res)
            ok_('email' not in res)
            ok_('user_id' not in res)
            ok_('exploitability' not in res)

            # get a unredacted processed crash
            params['datatype'] = 'unredacted'
            res = service.get(**params)

            eq_(res['name'], 'Peter')
            ok_('url' in res)
            ok_('email' in res)
            ok_('user_id' in res)
            ok_('exploitability' in res)

            eq_(res['email'], 'peter@fake.org')

            # missing parameters
            assert_raises(
                MissingArgumentError,
                service.get
            )
            assert_raises(
                MissingArgumentError,
                service.get,
                **{'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'}
            )

            # crash cannot be found
            assert_raises(
                ResourceNotFound,
                service.get,
                **{
                    'uuid': 'c44245f4-c93b-49b8-86a2-c15dc2130504',
                    'datatype': 'processed'
                }
            )
            # crash cannot be found
            assert_raises(
                ResourceNotFound,
                service.get,
                **{
                    'uuid': 'c44245f4-c93b-49b8-86a2-c15dc2130504',
                    'datatype': 'unredacted'
                }
            )

            # not yet available crash
            assert_raises(
                ResourceUnavailable,
                service.get,
                **{
                    'uuid': '58727744-12f5-454a-bcf5-f688a2120821',
                    'datatype': 'processed'
                }
            )

            # not yet available crash
            assert_raises(
                ResourceUnavailable,
                service.get,
                **{
                    'uuid': '58727744-12f5-454a-bcf5-f688a2120821',
                    'datatype': 'unredacted'
                }
            )

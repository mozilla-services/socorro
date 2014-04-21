# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock, MagicMock
from nose.plugins.attrib import attr
from nose.tools import eq_

from crontabber.app import CronTabber

from crontabber.tests.base import IntegrationTestCaseBase


#==============================================================================
@attr(integration='postgres')
class IntegrationTestServerStatus(IntegrationTestCaseBase):

    def _clear_tables(self):
        self.conn.cursor().execute("""
            TRUNCATE
                processors,
                server_status,
                report_partition_info,
                server_status,
                release_channels,
                reports
            CASCADE
        """)

    def setUp(self):
        super(IntegrationTestServerStatus, self).setUp()
        self._clear_tables()

    def tearDown(self):
        """
        The reason why this is all necessary, including the commit, is that
        we're testing a multi-process tool, crontabber.
        The changes made to the database happen in a transaction
        that crontabber doesn't have visibility into.

        TODO drop reports partitions, not just the data

        """
        self._clear_tables()
        self.conn.commit()
        super(IntegrationTestServerStatus, self).tearDown()

    def _setup_config_manager(self):
        _super = super(IntegrationTestServerStatus, self)._setup_config_manager

        queue_mock = Mock()
        queue_mock.return_value.return_value = MagicMock()
        queue_mock.return_value.return_value.queue_status_standard \
            .method.message_count = 1

        return _super(
            'socorro.cron.jobs.serverstatus.ServerStatusCronApp|5m',
            extra_value_source={
                'crontabber.class-ServerStatusCronApp.queuing.queuing_class':
                queue_mock
            }
        )

    def test_server_status(self):
        """ Simple test of status monitor """
        config_manager = self._setup_config_manager()

        cursor = self.conn.cursor()

        # Create partitions to support the status query
        # Load report_partition_info data
        cursor.execute("""
            INSERT into report_partition_info
              (table_name, build_order, keys, indexes,
              fkeys, partition_column, timetype)
            VALUES
             ('reports', '1', '{id,uuid}',
             '{date_processed,hangid,"product,version",reason,signature,url}',
             '{}', 'date_processed', 'TIMESTAMPTZ')
        """)
        cursor.execute('SELECT weekly_report_partitions()')

        # We have to do this here to accommodate separate crontabber processes
        self.conn.commit()

        # Load sample data
        cursor.execute("""
            INSERT INTO processors
            (id, lastseendatetime, name, startdatetime)
            VALUES
            (1, now(), 'test', now())
        """)
        cursor.execute("""
            INSERT INTO reports
            (uuid, signature, completed_datetime,
            started_datetime, date_processed)
            VALUES
            ('123', 'legitimate(sig)', now(), now()-'1 minute'::interval,
            now()),
            ('456', 'MWSBAR.DLL@0x2589f', now(), now()-'2 minutes'::interval,
            now());
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()
        cursor.execute('select count(*) from server_status')

        res_expected = 1
        res, = cursor.fetchone()
        eq_(res, res_expected)

        cursor.execute("""select
                date_recently_completed
                , date_oldest_job_queued -- is NULL until we upgrade Rabbit
                , avg_process_sec
                , waiting_job_count -- should be 1
                , processors_count -- should be 1
                -- , date_created -- leaving timestamp verification out
            from server_status
        """)

        res_expected = (None, None, 0.0, 1, 1)
        res = cursor.fetchone()
        eq_(res, res_expected)

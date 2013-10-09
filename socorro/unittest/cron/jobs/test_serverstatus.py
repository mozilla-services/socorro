# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os
import json
from mock import Mock
from nose.plugins.attrib import attr
from socorro.cron import crontabber
from ..base import IntegrationTestCaseBase
from socorro.cron.jobs.serverstatus import ServerStatusCronApp


#==============================================================================
@attr(integration='postgres')
class IntegrationTestServerStatus(IntegrationTestCaseBase):

    def setUp(self):
        super(IntegrationTestServerStatus, self).setUp()
        # Clean out anything in server_status or partition_info
        self.conn.cursor().execute('DELETE FROM processors')
        self.conn.cursor().execute('DELETE FROM server_status')
        self.conn.cursor().execute('DELETE FROM report_partition_info')
        ServerStatusCronApp._get_message_count = Mock()

    def tearDown(self):
        # TODO drop reports partitions
        self.conn.cursor().execute('DELETE FROM server_status')
        self.conn.cursor().execute('DELETE FROM report_partition_info')
        self.conn.cursor().execute('DELETE FROM reports')
        self.conn.cursor().execute('DELETE FROM processors')
        self.conn.commit()
        super(IntegrationTestServerStatus, self).tearDown()

    def _setup_config_manager(self, config_file):
        _super = super(IntegrationTestServerStatus, self)._setup_config_manager

        self.rabbit_queue_mocked = Mock()

        class Empty:
            pass

        class M:
            def connection(self):
                e = Empty()
                e.queue_status_standard = Empty()
                e.queue_status_standard.method = Empty()
                e.queue_status_standard.method.message_count = 1
                return e

        self.rabbit_queue_mocked.return_value = M()

        config_manager, json_file = _super(
            'socorro.cron.jobs.serverstatus.ServerStatusCronApp|5m',
            config=config_file,
            extra_value_source={'queue_class': self.rabbit_queue_mocked}
        )
        return config_manager, json_file

    def test_server_status(self):
        """ Simple test of status monitor
            'make test-socorro' copies test_serverstatus.ini-dist to .ini
            for this test
        """
        config_manager, json_file = self.\
            _setup_config_manager('./config/test_serverstatus.ini')

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
            now());
        """)
        cursor.execute("""
            INSERT INTO reports
            (uuid, signature, completed_datetime,
            started_datetime, date_processed)
            VALUES
            ('456', 'MWSBAR.DLL@0x2589f', now(), now()-'2 minutes'::interval,
            now());
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
        print self.rabbit_queue_mocked.mock_calls
        cursor.execute('select * from reports')
        stuff = cursor.fetchall()
        cursor.execute('select count(*) from server_status')
        res_expected = 1
        res, = cursor.fetchone()
        self.assertEqual(res, res_expected)

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
        self.assertEqual(res, res_expected)

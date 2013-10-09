# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os
import json
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
        self.conn.cursor().execute('DELETE FROM server_status')
        self.conn.cursor().execute('DELETE FROM report_partition_info')


    def tearDown(self):
        self.conn.rollback()
        # TODO drop reports partitions
        super(IntegrationTestServerStatus, self).tearDown()


    def _setup_config_manager(self):
        _super = super(IntegrationTestServerStatus, self)._setup_config_manager
        config_manager, json_file = _super(
          'socorro.cron.jobs.serverstatus.ServerStatusCronApp|5m',
        )
        return config_manager, json_file


    def test_server_status(self):
        """ Simple test of status monitor """
        config_manager, json_file = self._setup_config_manager()

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
            (uuid, signature, completed_datetime, started_datetime, date_processed)
            VALUES
            ('123', 'legitimate(sig)', now(), now()-'1 minute'::interval, now());
        """)
        cursor.execute("""
            INSERT INTO reports
            (uuid, signature, completed_datetime, started_datetime, date_processed)
            VALUES
            ('456', 'MWSBAR.DLL@0x2589f', now(), now()-'2 minutes'::interval, now());
        """)

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
        cursor.execute('select * from reports')
        stuff  = cursor.fetchall()
        print "%r" % stuff
        cursor.execute('select count(*) from server_status')
        count, = cursor.fetchone()
        print "%r" % count
        assert count == 1


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
        # Clean out anything in server_status
        self.conn.cursor().execute('DELETE FROM server_status')


    def tearDown(self):
        self.conn.rollback()
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
        cursor.execute('SELECT weekly_report_partitions()')

        # Load sample data
        cursor.execute("""
            INSERT INTO processors
            (id, lastseendatetime, name, startdatetime)
            VALUES
            (1, now(), 'test', now())
        """)
        cursor.execute("""
            INSERT INTO reports
            (uuid, signature)
            VALUES
            ('123', 'legitimate(sig)');
        """)
        cursor.execute("""
            INSERT INTO reports
            (uuid, signature)
            VALUES
            ('456', 'MWSBAR.DLL@0x2589f');
        """)

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

        cursor.execute('select count(*) from server_status')
        count, = cursor.fetchone()
        assert count == 1


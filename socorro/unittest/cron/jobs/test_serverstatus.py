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


SERVER_STATUS_SAMPLE = [
   '"id","date_recently_completed","date_oldest_job_queued","avg_process_sec","avg_wait_sec","waiting_job_count","processors_count","date_created"',
   '336320,,,0,0,0,0,2012-01-13 17:31:14.429213+00',
   '336321,2012-01-14 01:30:01.957697+00,2012-01-14 01:29:50.991768+00,2.00377,8.87334,375,10,2012-01-14 01:30:01.943564+00',
   '336322,2012-01-14 01:35:01.532351+00,2012-01-14 01:29:49.979796+00,3.05329,137.668,6510,10,2012-01-14 01:35:01.547402+00',
   '336323,2012-01-14 01:40:02.140589+00,2012-01-14 01:38:58.936814+00,3.03835,44.4502,1659,10,2012-01-14 01:40:02.155084+00',
   '336324,2012-01-14 01:45:01.919644+00,2012-01-14 01:44:50.577393+00,2.82401,6.93124,428,10,2012-01-14 01:45:01.943402+00',
   '336325,2012-01-14 01:50:01.806359+00,2012-01-14 01:49:46.762647+00,2.86931,6.87754,484,10,2012-01-14 01:50:01.845242+00',
   '336326,2012-01-14 01:55:01.485826+00,2012-01-14 01:54:51.591813+00,2.83094,6.95963,492,10,2012-01-14 01:55:01.491986+00',
   '336327,2012-01-14 02:00:01.655048+00,2012-01-14 01:59:51.511313+00,2.82097,6.94025,444,10,2012-01-14 02:00:01.657366+00',
   '336328,2012-01-14 02:05:01.976598+00,2012-01-14 02:04:50.550518+00,2.84925,7.0182,445,10,2012-01-14 02:05:01.988433+00'
   '336329,2012-01-14 02:10:01.234326+00,2012-01-14 02:09:59.05536+00,2.63734,12.3921,15,10,2012-01-14 02:10:01.681995+00',
]


#==============================================================================
@attr(integration='postgres')
class IntegrationTestServerStatus(IntegrationTestCaseBase):

    def setUp(self):
        super(IntegrationTestServerStatus, self).setUp()


    def tearDown(self):
        super(IntegrationTestServerStatus, self).tearDown()
        self.conn.cursor().execute("""
        TRUNCATE TABLE reports CASCADE;
        TRUNCATE TABLE server_status CASCADE;
        TRUNCATE TABLE processors CASCADE;
        """)
        self.conn.commit()

    def _setup_config_manager(self, days_into_past):
        datestring = ((datetime.datetime.utcnow() -
                       datetime.timedelta(days=days_into_past))
                       .strftime('%Y-%m-%d'))
        filename = os.path.join(self.tempdir, 'sample-%s.csv' % datestring)
        with open(filename, 'w') as f:
            f.write('\n'.join(SERVER_STATUS_SAMPLE))

        query = 'file://' + filename.replace(datestring, '%s')

        _super = super(IntegrationTestServerStatus, self)._setup_config_manager
        config_manager, json_file = _super(
          'socorro.cron.jobs.serverstatus.ServerStatusCronApp|5m',
          extra_value_source={
            #'crontabber.class-ServerStatusCronApp.query': query,
            #'crontabber.class-ServerStatusCronApp.days_into_past': days_into_past,
          }
        )
        return config_manager, json_file

    def test_basic_run_job_without_reports(self):
        config_manager, json_file = self._setup_config_manager(3)

        cursor = self.conn.cursor()
        for table in ['reports', 'server_status', 'processors']:
            cursor.execute('select count(*) from %s' % table)
            count, = cursor.fetchone()
            assert count == 0, "%s table not cleaned" % table

        self.conn.cursor().execute("""
            INSERT INTO processors
            (id, lastseendatetime, name, startdatetime)
            VALUES(
                1, now(), 'test', now()
            )
        """)
        self.conn.cursor().execute("""insert into reports
        (uuid,signature)
        values
        ('123', 'legitimate(sig)');
        """)
        self.conn.cursor().execute("""insert into reports
        (uuid,signature)
        values
        ('456', 'MWSBAR.DLL@0x2589f');
        """)

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

        # it means that all bugs are rejected
        cursor.execute('select count(*) from server_status')
        count, = cursor.fetchone()
        assert count == 1


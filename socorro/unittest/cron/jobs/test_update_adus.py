# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import mock
from socorro.cron import crontabber
from socorro.lib.datetimeutil import utc_now
from ..base import TestCaseBase


class TestUpdateADUs(TestCaseBase):

    def setUp(self):
        super(TestUpdateADUs, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.mocked_connection = mock.Mock()
        self.psycopg2 = self.psycopg2_patcher.start()

    def tearDown(self):
        super(TestUpdateADUs, self).tearDown()
        self.psycopg2_patcher.stop()

    def test_run_all(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.cron.jobs.update_adus.UpdateADUsCronApp|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            for call in self.psycopg2().cursor().callproc.mock_calls:
                __, call_args, __ = call
                proc_name, date = call_args
                self.assertEqual(proc_name, 'update_adu')
                yesterday = utc_now() - datetime.timedelta(days=1)
                self.assertEqual(date, [yesterday.strftime('%Y-%m-%d')])

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import mock
from socorro.cron import crontabber
from ..base import TestCaseBase


#==============================================================================
class TestWeeklyReportsPartitions(TestCaseBase):

    def setUp(self):
        super(TestWeeklyReportsPartitions, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.psycopg2 = self.psycopg2_patcher.start()

    def tearDown(self):
        super(TestWeeklyReportsPartitions, self).tearDown()
        self.psycopg2_patcher.stop()

    def _setup_config_manager(self):
        _super = super(TestWeeklyReportsPartitions, self)._setup_config_manager
        config_manager, json_file = _super(
            'socorro.cron.jobs.weekly_reports_partitions.'
            'WeeklyReportsPartitionsCronApp|1d',
        )
        return config_manager, json_file

    def test_run_weekly_reports_partitions(self):
        config_manager, json_file = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['weekly-reports-partitions']
            assert not information['weekly-reports-partitions']['last_error']
            assert information['weekly-reports-partitions']['last_success']

            # see https://bugzilla.mozilla.org/show_bug.cgi?id=828071
            self.assertEqual(self.psycopg2().cursor().commit.call_count, 1)

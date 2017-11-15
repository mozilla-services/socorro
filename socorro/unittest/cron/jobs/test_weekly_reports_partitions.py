# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from socorro.cron.crontabber_app import CronTabberApp
from socorro.unittest.cron.jobs.base import IntegrationTestBase


class TestWeeklyReportsPartitions(IntegrationTestBase):

    def _setup_config_manager(self):
        return super(TestWeeklyReportsPartitions, self)._setup_config_manager(
            jobs_string=(
                'socorro.cron.jobs.weekly_reports_partitions.WeeklyReportsPartitionsCronApp|1d'
            ),
        )

    def test_run_weekly_reports_partitions(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['weekly-reports-partitions']
            assert not information['weekly-reports-partitions']['last_error']
            assert information['weekly-reports-partitions']['last_success']

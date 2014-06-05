# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr

from crontabber.app import CronTabber
from socorro.unittest.cron.jobs.base import IntegrationTestBase

from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


#==============================================================================
@attr(integration='postgres')
class TestWeeklyReportsPartitions(IntegrationTestBase):

    def get_standard_config(self):
        return get_config_manager_for_crontabber().get_config()

    def _setup_config_manager(self):
        _super = super(TestWeeklyReportsPartitions, self)._setup_config_manager
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.weekly_reports_partitions.'
                'WeeklyReportsPartitionsCronApp|1d',
        )

    def test_run_weekly_reports_partitions(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['weekly-reports-partitions']
            assert not information['weekly-reports-partitions']['last_error']
            assert information['weekly-reports-partitions']['last_success']

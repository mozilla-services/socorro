# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.cron.crontabber_app import CronTabberApp
from socorro.unittest.cron.jobs.base import IntegrationTestBase


class TestFAKEFetchADIFromHive(IntegrationTestBase):

    def _setup_config_manager(self):
        return super(TestFAKEFetchADIFromHive, self)._setup_config_manager(
            jobs_string=(
                'socorro.cron.jobs.fetch_adi_alt.FAKEFetchADIFromHiveCronApp|1d'
            ),
        )

    def test_mocked_fetch(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['fetch-adi-from-hive']
            assert not information['fetch-adi-from-hive']['last_error']

            config.logger.info.assert_called_with(
                'Faking the fetching of ADI from Hive :)'
            )

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock

from socorro.cron.crontabber_app import CronTabberApp
from socorro.unittest.cron.jobs.base import IntegrationTestBase


class IntegrationTestElasticsearchCleanup(IntegrationTestBase):

    def _setup_config_manager(self):
        return super(IntegrationTestElasticsearchCleanup, self)._setup_config_manager(
            jobs_string='socorro.cron.jobs.elasticsearch_cleanup.ElasticsearchCleanupCronApp|30d'
        )

    @mock.patch('socorro.external.es.connection_context.ConnectionContext')
    def test_run(self, connection_context):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['elasticsearch-cleanup']
            assert not information['elasticsearch-cleanup']['last_error']
            assert information['elasticsearch-cleanup']['last_success']

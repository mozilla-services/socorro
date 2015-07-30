# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock

from nose.tools import ok_

from crontabber.app import CronTabber
from socorro.unittest.cron.jobs.base import IntegrationTestBase

from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


class IntegrationTestElasticsearchCleanup(IntegrationTestBase):

    def _setup_config_manager(self):
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.elasticsearch_cleanup.'
                 'ElasticsearchCleanupCronApp|30d',
        )

    @mock.patch('socorro.external.es.connection_context.ConnectionContext')
    def test_run(self, connection_context):
        with self._setup_config_manager().context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            ok_(information['elasticsearch-cleanup'])
            ok_(not information['elasticsearch-cleanup']['last_error'])
            ok_(information['elasticsearch-cleanup']['last_success'])

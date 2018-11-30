# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock

from socorro.cron.crontabber_app import CronTabberApp
from socorro.unittest.cron.crontabber_tests_base import get_config_manager, load_structure


class TestElasticsearchCleanupAppCronApp(object):
    def _setup_config_manager(self):
        return get_config_manager(
            jobs='socorro.cron.jobs.elasticsearch_cleanup.ElasticsearchCleanupCronApp|30d'
        )

    @mock.patch('socorro.external.es.connection_context.ConnectionContext')
    def test_run(self, connection_context, db_conn):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_one('elasticsearch-cleanup')

            information = load_structure(db_conn)
            assert information['elasticsearch-cleanup']
            assert not information['elasticsearch-cleanup']['last_error']
            assert information['elasticsearch-cleanup']['last_success']

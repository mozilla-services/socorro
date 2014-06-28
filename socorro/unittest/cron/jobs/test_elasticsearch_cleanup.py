# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import mock
import os
import pyelasticsearch

from nose.plugins.attrib import attr
from nose.tools import assert_raises

from configman import ConfigurationManager
from crontabber.app import CronTabber
from socorro.unittest.cron.jobs.base import IntegrationTestBase


from socorro.external.elasticsearch.crashstorage import \
    ElasticSearchCrashStorage
from socorro.lib.datetimeutil import utc_now
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)

# Remove debugging noise during development
import logging
logging.getLogger('pyelasticsearch').setLevel(logging.ERROR)
logging.getLogger('elasticutils').setLevel(logging.ERROR)
logging.getLogger('requests.packages.urllib3.connectionpool')\
       .setLevel(logging.ERROR)


@attr(integration='elasticsearch')
class IntegrationTestElasticsearchCleanup(IntegrationTestBase):

    def _setup_config_manager(self):
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.elasticsearch_cleanup.'
                'ElasticsearchCleanupCronApp|30d',
        )

    def __init__(self, *args, **kwargs):
        super(
            IntegrationTestElasticsearchCleanup,
            self
        ).__init__(*args, **kwargs)

        storage_config = self._setup_storage_config()
        with storage_config.context() as config:
            self.storage = ElasticSearchCrashStorage(config)

    def tearDown(self):
        # Clean up created indices.
        self.storage.es.delete_index('socorro*')
        super(IntegrationTestElasticsearchCleanup, self).tearDown()

    def _setup_storage_config(self):
        mock_logging = mock.Mock()

        storage_conf = ElasticSearchCrashStorage.get_required_config()
        storage_conf.add_option('logger', default=mock_logging)

        return ConfigurationManager(
            [storage_conf],
            values_source_list=[os.environ],
            argv_source=[]
        )

    def test_right_indices_are_deleted(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            # clear the indices cache so the index is created on every test
            self.storage.indices_cache = set()

            es = self.storage.es

            # Create old indices to be deleted.
            self.storage.create_index('socorro200142', {})
            self.storage.create_index('socorro200000', {})

            # Create an old aliased index.
            self.storage.create_index('socorro200201_20030101', {})
            es.update_aliases({
                'actions': [{
                    'add': {
                        'index': 'socorro200201_20030101',
                        'alias': 'socorro200201'
                    }
                }]
            })

            # Create a recent aliased index.
            last_week_index = self.storage.get_index_for_crash(
                utc_now() - datetime.timedelta(weeks=1)
            )
            self.storage.create_index('socorro_some_aliased_index', {})
            es.update_aliases({
                'actions': [{
                    'add': {
                        'index': 'socorro_some_aliased_index',
                        'alias': last_week_index
                    }
                }]
            })

            # Create a recent index that should not be deleted.
            now_index = self.storage.get_index_for_crash(utc_now())
            self.storage.create_index(now_index, {})

            # These will raise an error if an index was not correctly created.
            es.status('socorro200142')
            es.status('socorro200000')
            es.status('socorro200201')
            es.status(now_index)
            es.status(last_week_index)

            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['elasticsearch-cleanup']
            assert not information['elasticsearch-cleanup']['last_error']
            assert information['elasticsearch-cleanup']['last_success']

            # Verify the recent index is still there.
            es.status(now_index)
            es.status(last_week_index)

            # Verify the old indices are gone.
            assert_raises(
                pyelasticsearch.exceptions.ElasticHttpNotFoundError,
                es.status,
                'socorro200142'
            )

            assert_raises(
                pyelasticsearch.exceptions.ElasticHttpNotFoundError,
                es.status,
                'socorro200000'
            )

            assert_raises(
                pyelasticsearch.exceptions.ElasticHttpNotFoundError,
                es.status,
                'socorro200201'
            )

    def test_other_indices_are_not_deleted(self):
        """Verify that non-week-based indices are not removed. For example,
        the socorro_email index should not be deleted by the cron job.
        """
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            # clear the indices cache so the index is created on every test
            self.storage.indices_cache = set()

            es = self.storage.es

            # Create the socorro emails index.
            self.storage.create_emails_index()

            # This will raise an error if the index was not correctly created.
            es.status('socorro_emails')

            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['elasticsearch-cleanup']
            assert not information['elasticsearch-cleanup']['last_error']
            assert information['elasticsearch-cleanup']['last_success']

            # Verify the email index is still there. This will raise an error
            # if the index does not exist.
            es.status('socorro_emails')

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import elasticsearch

from nose.tools import ok_

from socorro.lib.datetimeutil import utc_now
from socorro.external.es.index_cleaner import IndexCleaner
from socorro.unittest.external.es.base import (
    ElasticsearchTestCase,
    minimum_es_version,
)

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class IntegrationTestIndexCleaner(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(IntegrationTestIndexCleaner, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(IndexCleaner, {
            'resource.elasticsearch.elasticsearch_index': 'socorro%Y%W'
        })

    def setUp(self):
        # Create the supersearch fields.
        self.index_super_search_fields()

        self.indices = []

    def tearDown(self):
        """Remove any indices that may have been created during tests.
        """
        for index in self.indices:
            try:
                self.index_client.delete(index)
            # "Missing" indices have already been deleted, no need to worry.
            except elasticsearch.exceptions.NotFoundError:
                pass

    def get_index_for_date(self, date):
        return date.strftime(self.config.elasticsearch.elasticsearch_index)

    @minimum_es_version('1.0')
    def test_delete_old_indices(self):
        # Create old indices to be deleted.
        self.index_client.create('socorro200142', {})
        self.indices.append('socorro200142')

        self.index_client.create('socorro200000', {})
        self.indices.append('socorro200000')

        # Create an old aliased index.
        self.index_client.create('socorro200201_20030101', {})
        self.indices.append('socorro200201_20030101')
        self.index_client.put_alias(
            index='socorro200201_20030101',
            name='socorro200201',
        )

        # Create a recent aliased index.
        last_week_index = self.get_index_for_date(
            utc_now() - datetime.timedelta(weeks=1)
        )
        self.index_client.create('socorro_some_aliased_index', {})
        self.indices.append('socorro_some_aliased_index')
        self.index_client.put_alias(
            index='socorro_some_aliased_index',
            name=last_week_index,
        )

        # Create a recent index that should not be deleted.
        now_index = self.get_index_for_date(utc_now())
        self.index_client.create(now_index, {})
        self.indices.append(now_index)

        # These will raise an error if an index was not correctly created.
        assert self.index_client.exists('socorro200142')
        assert self.index_client.exists('socorro200000')
        assert self.index_client.exists('socorro200201')
        assert self.index_client.exists(now_index)
        assert self.index_client.exists(last_week_index)

        api = IndexCleaner(self.config)
        api.delete_old_indices()

        # Verify the recent index is still there.
        ok_(self.index_client.exists(now_index))
        ok_(self.index_client.exists(last_week_index))

        # Verify the old indices are gone.
        ok_(not self.index_client.exists('socorro200142'))
        ok_(not self.index_client.exists('socorro200000'))
        ok_(not self.index_client.exists('socorro200201'))

    @minimum_es_version('1.0')
    def test_other_indices_are_not_deleted(self):
        """Verify that non-week-based indices are not removed.
        """
        # Create a temporary index.
        self.index_creator.create_index('socorro_test_temp', {})
        self.indices.append('socorro_test_temp')

        assert self.index_client.exists('socorro_test_temp')

        api = IndexCleaner(self.config)
        api.delete_old_indices()

        # Verify the email index is still there.
        ok_(self.index_client.exists('socorro_test_temp'))

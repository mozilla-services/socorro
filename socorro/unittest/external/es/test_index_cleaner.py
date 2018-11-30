# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import elasticsearch

from socorro.lib.datetimeutil import utc_now
from socorro.external.es.index_cleaner import IndexCleaner
from socorro.unittest.external.es.base import ElasticsearchTestCase

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class IntegrationTestIndexCleaner(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(IntegrationTestIndexCleaner, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(IndexCleaner, {
            'resource.elasticsearch.elasticsearch_index': 'test_socorro%Y%W',
            'resource.elasticsearch.elasticsearch_index_regex': '^test_socorro[0-9]{6}$',
        })

    def setup_method(self, method):
        super(IntegrationTestIndexCleaner, self).setup_method(method)
        self.indices = []

    def create_index(self, index):
        self.index_creator.create_index(index, {})
        self.indices.append(index)
        assert self.index_client.exists(index)

    def teardown_method(self, method):
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

    def test_delete_old_indices(self):
        # Create old indices to be deleted.
        self.create_index('test_socorro200142')
        self.create_index('test_socorro200000')

        # Create an old aliased index.
        self.create_index('test_socorro200201_20030101')
        self.index_client.put_alias(
            index='test_socorro200201_20030101',
            name='test_socorro200201',
        )

        # Create a recent aliased index.
        last_week_index = self.get_index_for_date(
            utc_now() - datetime.timedelta(weeks=1)
        )
        self.create_index('test_socorro_some_aliased_index')
        self.index_client.put_alias(
            index='test_socorro_some_aliased_index',
            name=last_week_index,
        )

        # Create a recent index that should not be deleted.
        now_index = self.get_index_for_date(utc_now())
        self.create_index(now_index)

        # These will raise an error if an index was not correctly created.
        assert self.index_client.exists(now_index)
        assert self.index_client.exists(last_week_index)

        api = IndexCleaner(self.config)
        api.delete_old_indices()

        # Verify the recent index is still there.
        assert self.index_client.exists(now_index)
        assert self.index_client.exists(last_week_index)

        # Verify the old indices are gone.
        assert not self.index_client.exists('test_socorro200142')
        assert not self.index_client.exists('test_socorro200000')
        assert not self.index_client.exists('test_socorro200201')

    def test_delete_old_indices_other_indices_are_not_deleted(self):
        """Verify that non-week-based indices are not removed"""
        # Create a temporary index.
        self.index_creator.create_index('socorro_test_temp', {})

        api = IndexCleaner(self.config)
        api.delete_old_indices()

        # Verify the email index is still there.
        assert self.index_client.exists('socorro_test_temp')

    def test_delete_indices_with_predicate(self):
        self.create_index('test_socorro201801')
        self.create_index('test_socorro201802')
        self.create_index('test_socorro_non_week')

        api = IndexCleaner(self.config)
        api.delete_indices(lambda index: index.endswith('2'))

        # Only week-based indices that match the predicate should be
        # deleted.
        assert self.index_client.exists('test_socorro201801')
        assert not self.index_client.exists('test_socorro201802')
        assert self.index_client.exists('test_socorro_non_week')

    def test_delete_indices_without_predicate(self):
        self.create_index('test_socorro201801')
        self.create_index('test_socorro201802')
        self.create_index('test_socorro_non_week')

        api = IndexCleaner(self.config)
        api.delete_indices()

        # Without a predicate, all week-based indices should be deleted
        assert not self.index_client.exists('test_socorro201801')
        assert not self.index_client.exists('test_socorro201802')
        assert self.index_client.exists('test_socorro_non_week')

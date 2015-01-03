# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import mock
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises
from pyelasticsearch.exceptions import (
    ElasticHttpError,
    ElasticHttpNotFoundError,
    InvalidJsonResponseError,
)

from socorro.external import (
    BadArgumentError,
    DatabaseError,
    MissingArgumentError,
    ResourceNotFound,
)
from socorro.external.elasticsearch import (
    crashstorage,
    base,
)
from socorro.external.elasticsearch.query import Query
from socorro.lib import datetimeutil

from .unittestbase import ElasticSearchTestCase
from .test_supersearch import (
    SUPERSEARCH_FIELDS
)

# Remove debugging noise during development
# import logging
# logging.getLogger('pyelasticsearch').setLevel(logging.ERROR)
# logging.getLogger('elasticutils').setLevel(logging.ERROR)
# logging.getLogger('requests.packages.urllib3.connectionpool')\
#        .setLevel(logging.ERROR)


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestQuery(ElasticSearchTestCase):
    """Test Query with an elasticsearch database containing fake data. """

    def setUp(self):
        super(IntegrationTestQuery, self).setUp()

        config = self.get_config_context()
        self.storage = crashstorage.ElasticSearchCrashStorage(config)
        self.api = Query(config=config)

        # clear the indices cache so the index is created on every test
        self.storage.indices_cache = set()

        # Create the supersearch fields.
        self.storage.es.bulk_index(
            index=config.webapi.elasticsearch_default_index,
            doc_type='supersearch_fields',
            docs=SUPERSEARCH_FIELDS.values(),
            id_field='name',
            refresh=True,
        )

        self.now = datetimeutil.utc_now()

        yesterday = self.now - datetime.timedelta(days=1)
        yesterday = datetimeutil.date_to_string(yesterday)

        # insert data into elasticsearch
        default_crash_report = {
            'uuid': 100,
            'signature': 'js::break_your_browser',
            'date_processed': yesterday,
            'product': 'WaterWolf',
            'version': '1.0',
            'release_channel': 'release',
            'os_name': 'Linux',
            'build': '1234567890',
            'reason': 'MOZALLOC_WENT_WRONG',
            'hangid': None,
            'process_type': None,
        }

        self.storage.save_processed(default_crash_report)

        self.storage.save_processed(
            dict(default_crash_report, uuid=1, product='EarthRaccoon')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=2, version='2.0')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=3, release_channel='aurora')
        )

        # As indexing is asynchronous, we need to force elasticsearch to
        # make the newly created content searchable before we run the tests
        self.storage.es.refresh()

    def tearDown(self):
        # clear the test index
        config = self.get_config_context()
        self.storage.es.delete_index(config.webapi.elasticsearch_index)
        self.storage.es.delete_index(config.webapi.elasticsearch_default_index)

        super(IntegrationTestQuery, self).tearDown()

    def test_get(self):
        query = {
            'query': {
                'match_all': {}
            }
        }
        res = self.api.get(query=json.dumps(query))
        ok_(res)
        ok_('hits' in res)
        eq_(res['hits']['total'], 4)

        query = {
            'query': {
                'filtered': {
                    'query': {
                        'match_all': {}
                    },
                    'filter': {
                        'term': {
                            'product': 'earthraccoon'
                        }
                    }
                }
            }
        }
        res = self.api.get(query=json.dumps(query))
        ok_(res)
        ok_('hits' in res)
        eq_(res['hits']['total'], 1)

    @mock.patch('socorro.external.elasticsearch.query.pyelasticsearch')
    def test_get_with_errors(self, mocked_es):
        # Test missing argument.
        assert_raises(
            BadArgumentError,
            self.api.get,
            query='hello!',
        )

        # Test invalid JSON argument.
        assert_raises(
            MissingArgumentError,
            self.api.get,
        )

        # Test missing index in elasticsearch.
        mocked_connection = mock.Mock()
        mocked_es.ElasticSearch.return_value = mocked_connection

        mocked_connection.search.side_effect = ElasticHttpNotFoundError(
            404, '[[socorro_201801] missing]'
        )
        assert_raises(
            ResourceNotFound,
            self.api.get,
            query='{}',
        )

        # Test invalid JSON response from elasticsearch.
        mocked_connection.search.side_effect = InvalidJsonResponseError('aaa')
        assert_raises(
            DatabaseError,
            self.api.get,
            query='{}',
        )

        # Test HTTP error from elasticsearch.
        mocked_connection.search.side_effect = ElasticHttpError('aaa')
        assert_raises(
            DatabaseError,
            self.api.get,
            query='{}',
        )

    @mock.patch('socorro.external.elasticsearch.query.pyelasticsearch')
    def test_get_with_indices(self, mocked_es):
        mocked_connection = mock.Mock()
        mocked_es.ElasticSearch.return_value = mocked_connection

        # Test default indices.
        self.api.get(
            query='{}'
        )
        mocked_connection.search.assert_called_with(
            {},
            index=[self.api.config.elasticsearch_index],
            doc_type=self.api.config.elasticsearch_doctype
        )

        # Test all indices.
        self.api.get(
            query='{}',
            indices=['ALL']
        )
        mocked_connection.search.assert_called_with(
            {}
        )

        # Test forcing indices.
        self.api.get(
            query='{}',
            indices=['socorro_201801', 'socorro_200047', 'not_an_index']
        )
        mocked_connection.search.assert_called_with(
            {},
            index=['socorro_201801', 'socorro_200047', 'not_an_index'],
            doc_type=self.api.config.elasticsearch_doctype
        )

        # Test default indices with an index schema based on dates.
        index_schema = 'socorro_%Y%W'
        config = self.get_config_context(es_index=index_schema)
        api = Query(config=config)

        last_week = self.now - datetime.timedelta(days=7)

        es = base.ElasticSearchBase(config=config)
        indices = es.generate_list_of_indexes(
            last_week,
            self.now,
        )

        api.get(
            query='{}'
        )
        mocked_connection.search.assert_called_with(
            {},
            index=indices,
            doc_type=self.api.config.elasticsearch_doctype
        )

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import elasticsearch
import json
import mock
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from socorro.external import (
    BadArgumentError,
    DatabaseError,
    MissingArgumentError,
    ResourceNotFound,
)
from socorro.external.es.query import Query
from socorro.lib import datetimeutil
from socorro.unittest.external.es.base import ElasticsearchTestCase

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestQuery(ElasticsearchTestCase):
    """Test Query with an elasticsearch database containing fake data. """

    def __init__(self, *args, **kwargs):
        super(IntegrationTestQuery, self).__init__(*args, **kwargs)

        self.api = Query(config=self.config)

    def test_get(self):
        self.index_crash({'product': 'WaterWolf'})
        self.index_crash({'product': 'EarthRaccoon'})
        self.refresh_index()

        query = {
            'query': {
                'match_all': {}
            }
        }
        res = self.api.post(query=json.dumps(query))
        ok_(res)
        ok_('hits' in res)
        eq_(res['hits']['total'], 2)

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
        res = self.api.post(query=json.dumps(query))
        ok_(res)
        ok_('hits' in res)
        eq_(res['hits']['total'], 1)

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_get_with_errors(self, mocked_es):
        # Test missing argument.
        assert_raises(
            BadArgumentError,
            self.api.post,
            query='hello!',
        )

        # Test invalid JSON argument.
        assert_raises(
            MissingArgumentError,
            self.api.post,
        )

        # Test missing index in elasticsearch.
        mocked_connection = mock.Mock()
        mocked_es.Elasticsearch.return_value = mocked_connection

        mocked_connection.search.side_effect = (
            elasticsearch.exceptions.NotFoundError(
                404, '[[socorro_201801] missing]'
            )
        )
        assert_raises(
            ResourceNotFound,
            self.api.post,
            query='{}',
        )

        # Test a generic error response from elasticsearch.
        mocked_connection.search.side_effect = (
            elasticsearch.exceptions.TransportError('aaa')
        )
        assert_raises(
            DatabaseError,
            self.api.post,
            query='{}',
        )

    @mock.patch('socorro.external.es.connection_context.elasticsearch')
    def test_get_with_indices(self, mocked_es):
        mocked_connection = mock.Mock()
        mocked_es.Elasticsearch.return_value = mocked_connection

        # Test default indices.
        self.api.post(
            query='{}'
        )
        mocked_connection.search.assert_called_with(
            body={},
            index=[self.api.config.elasticsearch.elasticsearch_index],
            doc_type=self.api.config.elasticsearch.elasticsearch_doctype
        )

        # Test all indices.
        self.api.post(
            query='{}',
            indices=['ALL']
        )
        mocked_connection.search.assert_called_with(
            body={}
        )

        # Test forcing indices.
        self.api.post(
            query='{}',
            indices=['socorro_201801', 'socorro_200047', 'not_an_index']
        )
        mocked_connection.search.assert_called_with(
            body={},
            index=['socorro_201801', 'socorro_200047', 'not_an_index'],
            doc_type=self.api.config.elasticsearch.elasticsearch_doctype
        )

        # Test default indices with an index schema based on dates.
        index_schema = 'socorro_%Y%W'
        config = self.get_mware_config(es_index=index_schema)
        api = Query(config=config)

        now = datetimeutil.utc_now()
        last_week = now - datetime.timedelta(days=7)
        indices = api.generate_list_of_indexes(last_week, now)

        api.post(
            query='{}'
        )
        mocked_connection.search.assert_called_with(
            body={},
            index=indices,
            doc_type=api.config.elasticsearch.elasticsearch_doctype
        )

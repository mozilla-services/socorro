# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from unittest import mock

import pytest

from socorro.lib import DatabaseError, MissingArgumentError, ResourceNotFound
from socorro.external.es.base import generate_list_of_indexes
from socorro.external.es.query import Query
from socorro.lib.libdatetime import utc_now, date_to_string
from socorro.tests.external.es.base import ElasticsearchTestCase


class TestIntegrationQuery(ElasticsearchTestCase):
    """Test Query with an elasticsearch database containing fake data."""

    def setup_method(self):
        super().setup_method()
        config = self.get_base_config(cls=Query)
        self.api = Query(config=config)

    def test_get(self):
        datestamp = date_to_string(utc_now())
        self.index_crash(
            processed_crash={"date_processed": datestamp, "product": "WaterWolf"}
        )
        self.index_crash(
            processed_crash={"date_processed": datestamp, "product": "EarthRaccoon"}
        )
        self.es_context.refresh()

        query = {"query": {"match_all": {}}}
        res = self.api.get(query=query)
        assert res["hits"]["total"] == 2

        query = {
            "query": {
                "filtered": {
                    "query": {"match_all": {}},
                    "filter": {"term": {"product": "earthraccoon"}},
                }
            }
        }
        res = self.api.get(query=query)
        assert res["hits"]["total"] == 1

    def test_get_with_errors(self):
        # Test missing argument.
        with pytest.raises(MissingArgumentError):
            self.api.get()

        with pytest.raises(ResourceNotFound):
            query = {"query": {"match_all": {}}}
            self.api.get(query=query, indices=["not_an_index"])

        with pytest.raises(DatabaseError):
            self.api.get(query={"query": {}})

    @mock.patch("socorro.external.es.connection_context.elasticsearch")
    def test_get_with_indices(self, mocked_es):
        mocked_connection = mock.Mock()
        mocked_es.Elasticsearch.return_value = mocked_connection

        # Test indices with dates (the test configuration includes dates).
        self.api.get(query={"query": {}})
        now = utc_now()
        last_week = now - datetime.timedelta(days=7)
        indices = generate_list_of_indexes(
            last_week, now, self.api.context.get_index_template()
        )
        mocked_connection.search.assert_called_with(
            body='{"query": {}}',
            index=indices,
            doc_type=self.es_context.get_doctype(),
        )

        # Test all indices.
        self.api.get(query={"query": {}}, indices=["ALL"])
        mocked_connection.search.assert_called_with(body='{"query": {}}')

        # Test forcing indices.
        self.api.get(
            query={"query": {}},
            indices=["socorro_201801", "socorro_200047", "not_an_index"],
        )
        mocked_connection.search.assert_called_with(
            body='{"query": {}}',
            index=["socorro_201801", "socorro_200047", "not_an_index"],
            doc_type=self.es_context.get_doctype(),
        )

        # Test default indices with an index schema based on dates.
        index_schema = "testsocorro"
        config = self.get_base_config(cls=Query, es_index=index_schema)
        api = Query(config=config)

        api.get(query={"query": {}})
        mocked_connection.search.assert_called_with(
            body='{"query": {}}',
            index=["testsocorro"],
            doc_type=api.context.get_doctype(),
        )

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from unittest import mock

import pytest

from socorro import settings
from socorro.lib import DatabaseError, MissingArgumentError, ResourceNotFound
from socorro.libclass import build_instance
from socorro.lib.libooid import create_new_ooid
from socorro.external.es.base import generate_list_of_indexes
from socorro.external.es.query import Query
from socorro.lib.libdatetime import utc_now, date_to_string


class TestIntegrationQuery:
    """Test Query with an elasticsearch database containing fake data."""

    def build_crashstorage(self):
        return build_instance(
            class_path="socorro.external.es.crashstorage.ESCrashStorage",
            kwargs=settings.ES_STORAGE["options"],
        )

    def test_get(self, es_helper):
        crashstorage = self.build_crashstorage()
        api = Query(crashstorage=crashstorage)

        datestamp = date_to_string(utc_now())
        es_helper.index_crash(
            processed_crash={
                "uuid": create_new_ooid(),
                "date_processed": datestamp,
                "product": "WaterWolf",
            },
        )
        es_helper.index_crash(
            processed_crash={
                "uuid": create_new_ooid(),
                "date_processed": datestamp,
                "product": "EarthRaccoon",
            },
        )
        es_helper.refresh()

        query = {"query": {"match_all": {}}}
        res = api.get(query=query)
        assert res["hits"]["total"] == 2

        query = {
            "query": {
                "constant_score": {
                    "filter": {"term": {"processed_crash.product": "earthraccoon"}},
                }
            }
        }
        res = api.get(query=query)
        assert res["hits"]["total"] == 1

    def test_get_with_errors(self, es_helper):
        crashstorage = self.build_crashstorage()
        api = Query(crashstorage=crashstorage)

        # Test missing argument.
        with pytest.raises(MissingArgumentError):
            api.get()

        with pytest.raises(ResourceNotFound):
            query = {"query": {"match_all": {}}}
            api.get(query=query, indices=["not_an_index"])

        with pytest.raises(DatabaseError):
            api.get(query={"query": {}})

    def test_get_with_indices(self, es_helper, monkeypatch):
        """Verify that .get() uses the correct indices."""
        crashstorage = self.build_crashstorage()
        api = Query(crashstorage=crashstorage)

        # Mock the connection so we can see the list of indexes it's building
        mocked_connection = mock.MagicMock()
        monkeypatch.setattr(api, "get_connection", mocked_connection)

        # Test indices with dates (the test configuration includes dates).
        api.get(query={"query": {}})
        now = utc_now()
        last_week = now - datetime.timedelta(days=7)
        indices = generate_list_of_indexes(
            last_week, now, api.crashstorage.get_index_template()
        )
        mocked_connection.return_value.search.assert_called_with(
            body='{"query": {}}',
            index=indices,
        )

        # Test all indices.
        api.get(query={"query": {}}, indices=["ALL"])
        mocked_connection.return_value.search.assert_called_with(body='{"query": {}}')

        # Test forcing indices.
        api.get(
            query={"query": {}},
            indices=["socorro_201801", "socorro_200047", "not_an_index"],
        )
        mocked_connection.return_value.search.assert_called_with(
            body='{"query": {}}',
            index=["socorro_201801", "socorro_200047", "not_an_index"],
        )

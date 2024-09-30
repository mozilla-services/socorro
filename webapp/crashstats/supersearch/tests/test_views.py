# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import json
import re
from unittest import mock
from urllib.parse import quote

from markus.testing import MetricsMock
import pyquery

from django.conf import settings
from django.urls import reverse
from django.utils.encoding import smart_str

from crashstats.crashstats.models import BugAssociation

from socorro.lib.libdatetime import date_to_string, utc_now
from socorro.lib.libooid import create_new_ooid, date_from_ooid


class TestViews:
    def test_search_metrics(self, client, db, preferred_es_helper):
        url = reverse("supersearch:search")

        with MetricsMock() as metrics_mock:
            response = client.get(url)
            assert response.status_code == 200
        records = metrics_mock.filter_records(
            "timing", stat="socorro.webapp.view.pageview"
        )
        assert len(records) == 1
        assert {
            "ajax:false",
            "api:false",
            "path:/search/",
            "status:200",
        }.issubset(records[0].tags)

    def test_search(self, client, db, preferred_es_helper):
        url = reverse("supersearch:search")

        response = client.get(url)
        assert response.status_code == 200
        assert "Run a search to get some results" in smart_str(response.content)

        # Check the simplified filters are there.
        for field in settings.SIMPLE_SEARCH_FIELDS:
            assert field.capitalize().replace("_", " ") in smart_str(response.content)

    def test_search_fields(self, client, db, preferred_es_helper, user_helper):
        url = reverse("supersearch:search_fields")
        response = client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        # Assert product names in response; these come from libproduct
        assert "Firefox" in data["product"]["values"]
        assert "Focus" in data["product"]["values"]
        assert "Fenix" in data["product"]["values"]

        # Assert fields that are protected aren't in the data
        assert "user_comments" not in data

        # Log in with user with protected data permissions and verify protected fields
        # are listed
        user = user_helper.create_protected_user()
        client.force_login(user)
        response = client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "user_comments" in data

    def test_search_fields_metrics(self, client, db, preferred_es_helper):
        url = reverse("supersearch:search_fields")
        with MetricsMock() as metrics_mock:
            response = client.get(url)
            assert response.status_code == 200
        records = metrics_mock.filter_records(
            "timing", stat="socorro.webapp.view.pageview"
        )
        assert len(records) == 1
        assert {
            "ajax:false",
            "api:false",
            "path:/search/fields/",
            "status:200",
        }.issubset(records[0].tags)

    def test_search_results(self, client, db, preferred_es_helper):
        BugAssociation.objects.create(
            bug_id=123456, signature="nsASDOMWindowEnumerator::GetNext()"
        )

        def build_crash_data(**params):
            crash_id = create_new_ooid()
            data = {
                "date_processed": utc_now(),
                "uuid": crash_id,
                "version": "1.0",
                "os_name": "Linux",
            }
            data.update(params)
            return data

        crash_data = [
            build_crash_data(
                signature="nsASDOMWindowEnumerator::GetNext()",
                product="Firefox",
                build=20220705093820,
            ),
            build_crash_data(
                signature="mySignatureIsCool",
                product="Firefox",
                os_name="<Windows>",
                build=20220608170832,
            ),
            build_crash_data(
                signature="mineIsCoolerThanYours",
                product="Firefox",
                build=None,
            ),
            build_crash_data(
                signature="EMPTY",
                product="Firefox",
                build=None,
            ),
            build_crash_data(
                signature="nsASDOMWindowEnumerator::GetNext()",
                product="Thunderbird",
                build=20220330194208,
            ),
            build_crash_data(
                signature="mySignatureIsCool",
                product="Thunderbird",
                build=20220330194208,
            ),
        ]
        for item in crash_data:
            preferred_es_helper.index_crash(processed_crash=item, refresh=False)
        preferred_es_helper.refresh()

        url = reverse("supersearch:search_results")
        response = client.get(url, {"product": "Firefox"})
        assert response.status_code == 200
        # Test results are existing
        assert 'table id="reports-list"' in smart_str(response.content)
        assert "nsASDOMWindowEnumerator::GetNext()" in smart_str(response.content)
        assert "mySignatureIsCool" in smart_str(response.content)
        assert "mineIsCoolerThanYours" in smart_str(response.content)
        assert "EMPTY" in smart_str(response.content)
        # Make sure first crash report shows up in results
        assert crash_data[0]["uuid"] in smart_str(response.content)
        assert str(crash_data[0]["build"]) in smart_str(response.content)
        assert crash_data[0]["os_name"] in smart_str(response.content)
        # Test facets are existing
        assert 'table id="facets-list-' in smart_str(response.content)
        # Test bugs are existing
        assert '<th scope="col">Bugs</th>' in smart_str(response.content)
        assert "123456" in smart_str(response.content)
        # Test links on terms are existing
        assert "build_id=%3D" + str(crash_data[0]["build"]) in smart_str(
            response.content
        )
        # Refine links to the product should not be "is" queries
        assert "product=Firefox" in smart_str(response.content)
        # Refine links have values that are urlencoded (this is also a field that should
        # not be an "is" query)
        assert "platform=%3CWindows%3E" in smart_str(response.content)

        # Test with empty results--we didn't index any crash reports for this product
        response = client.get(url, {"product": "Fenix"})
        assert response.status_code == 200
        assert 'table id="reports-list"' not in smart_str(response.content)
        assert "No results were found" in smart_str(response.content)

        # Test with a signature param--make sure first crash report shows up
        response = client.get(url, {"signature": "~nsASDOMWindowEnumerator"})
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        assert crash_data[0]["signature"] in smart_str(response.content)
        assert str(crash_data[0]["build"]) in smart_str(response.content)
        # Make sure bugs show up because this has the signature facet by default
        assert ">Bugs</th>" in smart_str(response.content)
        assert "123456" in smart_str(response.content)

        # Test with a different facet--fourth crash report shows up
        response = client.get(url, {"_facets": "build_id", "product": "Thunderbird"})
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        assert 'table id="facets-list-' in smart_str(response.content)
        assert str(crash_data[4]["build"]) in smart_str(response.content)
        # Make sure bug does not show up
        assert "<th>Bugs</th>" not in smart_str(response.content)
        assert "123456" not in smart_str(response.content)

        # Test with a different columns list
        response = client.get(
            url, {"_columns": ["build_id", "platform"], "product": "Thunderbird"}
        )
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        assert 'table id="facets-list-' in smart_str(response.content)
        # The build and platform appear
        assert str(crash_data[4]["build"]) in smart_str(response.content)
        assert crash_data[4]["os_name"] in smart_str(response.content)
        # The crash id is always shown
        assert crash_data[4]["uuid"] in smart_str(response.content)
        # The version and date do not appear
        assert crash_data[4]["version"] not in smart_str(response.content)
        # FIXME(willkg): date is hard to test because it changes forms when indexing

    def test_search_results_missing_parameter_values(
        self, client, db, preferred_es_helper
    ):
        url = reverse("supersearch:search_results")
        # Test missing parameters don't raise an exception.
        response = client.get(
            url, {"product": "Thunderbird", "date": "", "build_id": ""}
        )
        assert response.status_code == 200

    def test_search_results_metrics(self, client, db, preferred_es_helper):
        url = reverse("supersearch:search_results")
        with MetricsMock() as metrics_mock:
            response = client.get(url, {"product": "Firefox"})
            assert response.status_code == 200
        records = metrics_mock.filter_records(
            "timing", stat="socorro.webapp.view.pageview"
        )
        assert len(records) == 1
        assert {
            "ajax:false",
            "api:false",
            "path:/search/results/",
            "status:200",
        }.issubset(records[0].tags)

    def test_search_results_ratelimited(self, client, db, preferred_es_helper):
        url = reverse("supersearch:search_results")
        limit = int(re.findall(r"(\d+)", settings.RATELIMIT_SUPERSEARCH)[0])
        params = {"product": "Firefox"}
        # Double to avoid rate limiting window issues. bug 1148470
        for _ in range(limit * 2):
            client.get(url, params)
        # NOTE(willkg): this way of denoting AJAX requests may not work with all
        # JS frameworks
        response = client.get(url, params, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert response.status_code == 429
        assert smart_str(response.content) == "Too Many Requests"
        assert response["content-type"] == "text/plain"

    def test_search_results_badargumenterror(self, client, db, preferred_es_helper):
        url = reverse("supersearch:search_results")
        params = {"product": "<script>"}
        response = client.get(url, params, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert response.status_code == 400
        assert response["content-type"] == "text/html; charset=utf-8"
        assert "<script>" not in smart_str(response.content)
        assert "&lt;script&gt;" in smart_str(response.content)

    def test_search_results_permissions(
        self, client, db, preferred_es_helper, user_helper
    ):
        """Test that users with protected data access can see all fields."""
        crash_id = create_new_ooid()
        preferred_es_helper.index_crash(
            processed_crash={
                "uuid": crash_id,
                "date_processed": utc_now(),
                "version": "1.0",
                "os_name": "Linux",
                "gmp_library_path": "/home/me/gmp-widevinecdm/4.10.2449.0 ",
                "url": "http://example.org",
            },
        )

        url = reverse("supersearch:search_results")

        # Anonymous users can only see public fields
        response = client.get(
            url,
            {
                "_columns": ["version", "url", "gmp_library_path"],
                "_facets": ["url", "platform"],
            },
        )

        assert response.status_code == 200
        # Public
        assert "Version" in smart_str(response.content)
        assert "Platform facet" in smart_str(response.content)
        # Protected
        assert "Url facet" not in smart_str(response.content)
        assert "http://example.org" not in smart_str(response.content)
        assert "Gmp library path" not in smart_str(response.content)
        assert "widevinecdm" not in smart_str(response.content)

        # Protected data access uers can see all fields
        user = user_helper.create_protected_user()
        client.force_login(user)

        response = client.get(
            url,
            {
                "_columns": ["version", "url", "gmp_library_path"],
                "_facets": ["url", "platform"],
            },
        )

        assert response.status_code == 200
        # Public
        assert "Version" in smart_str(response.content)
        assert "Platform facet" in smart_str(response.content)
        # Protected
        assert "Url facet" in smart_str(response.content)
        assert "http://example.org" in smart_str(response.content)
        assert "Gmp library path" in smart_str(response.content)
        assert "widevinecdm" in smart_str(response.content)

        # Logged out user, can only see public fields
        client.logout()
        response = client.get(
            url,
            {
                "_columns": ["version", "url"],
                "_facets": ["url", "platform"],
            },
        )

        assert response.status_code == 200
        # Public
        assert "Version" in smart_str(response.content)
        assert "Platform facet" in smart_str(response.content)
        # Protected
        assert "Url facet" not in smart_str(response.content)
        assert "http://example.org" not in smart_str(response.content)
        assert "Gmp library path" not in smart_str(response.content)
        assert "widevinecdm" not in smart_str(response.content)

    def test_search_results_parameters(self, client, db, preferred_es_helper):
        """Verify all expected parameters are in the url."""
        calls = []

        def mocked_supersearch_get(**params):
            calls.append(params)
            return {"hits": [], "facets": "", "total": 0}

        with mock.patch(
            "crashstats.supersearch.models.SuperSearchUnredacted.get_implementation"
        ) as mocked_get_implementation:
            mocked_get_implementation.return_value.get.side_effect = (
                mocked_supersearch_get
            )

            url = reverse("supersearch:search_results")

            response = client.get(
                url,
                {
                    "product": ["Firefox", "Thunderbird"],
                    "address": ["0x00000000", "0xa0000000"],
                    "reason": ["^hello", "$thanks"],
                    "java_stack_trace": "Exception",
                },
            )
            assert response.status_code == 200
            # First call is the call to get_versions_for_product(), so we ignore
            # that
            assert len(calls) == 2
            params = calls[1]

            # Verify that all expected parameters are there
            assert "Firefox" in params["product"]
            assert "Thunderbird" in params["product"]
            assert "0x00000000" in params["address"]
            assert "0xa0000000" in params["address"]
            assert "^hello" in params["reason"]
            assert "$thanks" in params["reason"]
            assert "Exception" in params["java_stack_trace"]

    def test_search_results_pagination(self, client, db, preferred_es_helper):
        """Test that the pagination of results works as expected."""

        def build_crash_data(i):
            # Make crash ids unique with the first 6 characters being i
            crash_id = create_new_ooid()
            crash_id = f"{i:06d}{crash_id[6:]}"

            # Make the date_processed unique and sortable by subtracting i * 5 minutes
            date = date_from_ooid(crash_id) - datetime.timedelta(minutes=i * 5)

            return {
                "date_processed": date_to_string(date),
                "uuid": crash_id,
                "signature": "hang | nsASDOMWindowEnumerator::GetNext()",
                "product": "Firefox",
                "version": "1.0",
                "os_name": "Linux",
                "build": 888981,
            }

        crash_ids = []
        for i in range(140):
            data = build_crash_data(i)
            preferred_es_helper.index_crash(processed_crash=data, refresh=False)
            crash_ids.append(data["uuid"])

        preferred_es_helper.refresh()

        url = reverse("supersearch:search_results")

        response = client.get(
            url,
            {
                "signature": "hang | nsASDOMWindowEnumerator::GetNext()",
                "_columns": ["version"],
                "_facets": ["platform"],
                "_sort": "-date",
            },
        )

        assert response.status_code == 200
        # The first crash is newest, so it shows up on first page
        assert crash_ids[0] in smart_str(response.content)

        # Check that the pagination URL contains all three expected parameters.
        doc = pyquery.PyQuery(response.content)
        next_page_url = str(doc(".pagination a").eq(0))
        assert "_facets=platform" in next_page_url
        assert "_columns=version" in next_page_url
        assert "page=2" in next_page_url
        assert "#crash-reports" in next_page_url

        # Verify white spaces are correctly encoded. Note we use `quote` and not
        # `quote_plus`, so white spaces are turned into '%20' instead of '+'.
        assert quote("hang | nsASDOMWindowEnumerator::GetNext()") in next_page_url

        # Test that a negative page value does not break it.
        response = client.get(url, {"page": "-1"})
        assert response.status_code == 200


class TestCustomQuery:
    def test_search_custom_permission(
        self, client, db, preferred_es_helper, user_helper
    ):
        url = reverse("supersearch:search_custom")
        response = client.get(url)
        assert response.status_code == 302

        user = user_helper.create_protected_plus_user()
        client.force_login(user)

        response = client.get(url)
        assert response.status_code == 200
        assert "Run a search to get some results" in smart_str(response.content)

    def test_search_custom_metrics(self, client, db, preferred_es_helper, user_helper):
        user = user_helper.create_protected_plus_user()
        client.force_login(user)

        url = reverse("supersearch:search_custom")
        with MetricsMock() as metrics_mock:
            response = client.get(url)
            assert response.status_code == 200
        records = metrics_mock.filter_records(
            "timing", stat="socorro.webapp.view.pageview"
        )
        assert len(records) == 1
        assert {
            "ajax:false",
            "api:false",
            "path:/search/custom/",
            "status:200",
        }.issubset(records[0].tags)

    def test_search_custom_parameters(
        self, client, db, preferred_es_helper, user_helper
    ):
        preferred_es_helper.health_check()
        user = user_helper.create_protected_plus_user()
        client.force_login(user)

        url = reverse("supersearch:search_custom")
        response = client.get(url, {"signature": "nsA"})
        assert response.status_code == 200
        assert "Run a search to get some results" in smart_str(response.content)
        # Assert the query is in the editor
        assert "{&#34;query&#34;:" in smart_str(response.content)
        # Assert the available indices are there
        template = preferred_es_helper.get_index_template()
        now = utc_now()
        indices = [
            (now - datetime.timedelta(days=7)).strftime(template),
            now.strftime(template),
        ]
        assert ",".join(indices) in smart_str(response.content)

    def test_search_query(self, client, db, preferred_es_helper, user_helper):
        user = user_helper.create_protected_plus_user()
        client.force_login(user)

        url = reverse("supersearch:search_query")
        query = json.dumps({"query": {"match_all": {}}})
        response = client.post(url, {"query": query})
        assert response.status_code == 200

        content = json.loads(response.content)
        # There's nothing indexed, so no results
        assert content["hits"] == {"hits": [], "max_score": None, "total": 0}

    def test_search_query_failure(self, client, db, preferred_es_helper, user_helper):
        user = user_helper.create_protected_plus_user()
        client.force_login(user)

        url = reverse("supersearch:search_query")
        response = client.post(url)
        assert response.status_code == 400
        assert "query" in smart_str(response.content)

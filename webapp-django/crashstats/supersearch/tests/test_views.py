# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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
from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.supersearch.models import Query, SuperSearchUnredacted
from socorro.lib import BadArgumentError


class TestViews(BaseTestViews):
    def setUp(self):
        super().setUp()
        # Mock get_versions_for_product() so it doesn't hit supersearch breaking the
        # supersearch mocking
        self.mock_gvfp = mock.patch(
            "crashstats.crashstats.utils.get_versions_for_product"
        )
        self.mock_gvfp.return_value = ["20.0", "19.1", "19.0", "18.0"]
        self.mock_gvfp.start()

    def tearDown(self):
        self.mock_gvfp.stop()
        super().tearDown()

    def test_search_metrics(self):
        url = reverse("supersearch:search")

        with MetricsMock() as metrics_mock:
            response = self.client.get(url)

        assert response.status_code == 200
        metrics_mock.assert_timing(
            "webapp.view.pageview",
            tags=[
                "ajax:false",
                "api:false",
                "path:search_",
                "status:200",
            ],
        )

    def test_search(self):
        self._login()
        url = reverse("supersearch:search")

        response = self.client.get(url)
        assert response.status_code == 200
        assert "Run a search to get some results" in smart_str(response.content)

        # Check the simplified filters are there.
        for field in settings.SIMPLE_SEARCH_FIELDS:
            assert field.capitalize().replace("_", " ") in smart_str(response.content)

    def test_search_fields(self):
        user = self._login()
        url = reverse("supersearch:search_fields")
        response = self.client.get(url)
        assert response.status_code == 200
        assert "WaterWolf" in smart_str(response.content)
        assert "SeaMonkey" in smart_str(response.content)
        assert "NightTrain" in smart_str(response.content)

        content = json.loads(response.content)
        assert "signature" in content  # It contains at least one known field.

        # Verify non-exposed fields are not listed.
        assert "a_test_field" not in content

        # Verify fields with permissions are not listed.
        assert "exploitability" not in content

        # Verify fields with permissions are listed.
        group = self._create_group_with_permission("view_exploitability")
        user.groups.add(group)

        response = self.client.get(url)
        assert response.status_code == 200
        content = json.loads(response.content)

        assert "exploitability" in content

    def test_search_fields_metrics(self):
        self._login()
        url = reverse("supersearch:search_fields")
        with MetricsMock() as metrics_mock:
            response = self.client.get(url)
        assert response.status_code == 200
        metrics_mock.assert_timing(
            "webapp.view.pageview",
            tags=[
                "ajax:false",
                "api:false",
                "path:search_fields_",
                "status:200",
            ],
        )

    def test_search_results(self):
        BugAssociation.objects.create(
            bug_id=123456, signature="nsASDOMWindowEnumerator::GetNext()"
        )

        def mocked_supersearch_get(**params):
            assert "_columns" in params

            if "WaterWolf" in params.get("product", []):
                results = {
                    "hits": [
                        {
                            "signature": "nsASDOMWindowEnumerator::GetNext()",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "f74a5763-3270-4151-9c49-853710220208",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "<Linux>",
                            "build_id": 888981,
                        },
                        {
                            "signature": "mySignatureIsCool",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "63e199c4-d0a6-4386-93c7-8d72a0220208",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981,
                        },
                        {
                            "signature": "mineIsCoolerThanYours",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "e325b443-1b51-402b-b2c5-ccd630220208",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": None,
                        },
                        {
                            "signature": "EMPTY",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "2e982308-dc57-41a1-b997-b56f40220208",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": None,
                        },
                    ],
                    "facets": {
                        "signature": [
                            {"term": "nsASDOMWindowEnumerator::GetNext()", "count": 1},
                            {"term": "mySignatureIsCool", "count": 1},
                            {"term": "mineIsCoolerThanYours", "count": 1},
                            {"term": "EMPTY", "count": 1},
                        ]
                    },
                    "total": 4,
                }
                results["hits"] = self.only_certain_columns(
                    results["hits"], params["_columns"]
                )
                return results

            elif "SeaMonkey" in params.get("product", []):
                results = {
                    "hits": [
                        {
                            "signature": "nsASDOMWindowEnumerator::GetNext()",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "663c9970-3f35-4b15-beaf-756d60220208",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981,
                        },
                        {
                            "signature": "mySignatureIsCool",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "1c6f67c8-a6ff-45ab-b5c5-4d2c20220208",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981,
                        },
                    ],
                    "facets": {"build_id": [{"term": "888981", "count": 2}]},
                    "total": 2,
                }
                results["hits"] = self.only_certain_columns(
                    results["hits"], params["_columns"]
                )
                return results

            elif "~nsASDOMWindowEnumerator" in params.get("signature", []):
                results = {
                    "hits": [
                        {
                            "signature": "nsASDOMWindowEnumerator::GetNext()",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "ddb79c06-0d2f-4a7a-b2fc-d32a00220208",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 12345678,
                        }
                    ],
                    "facets": {
                        "signature": [
                            {"term": "nsASDOMWindowEnumerator::GetNext()", "count": 1}
                        ]
                    },
                    "total": 1,
                }
                results["hits"] = self.only_certain_columns(
                    results["hits"], params["_columns"]
                )
                return results

            else:
                return {"hits": [], "facets": [], "total": 0}

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_results")
        response = self.client.get(url, {"product": "WaterWolf"})
        assert response.status_code == 200
        # Test results are existing
        assert 'table id="reports-list"' in smart_str(response.content)
        assert "nsASDOMWindowEnumerator::GetNext()" in smart_str(response.content)
        assert "mySignatureIsCool" in smart_str(response.content)
        assert "mineIsCoolerThanYours" in smart_str(response.content)
        assert "EMPTY" in smart_str(response.content)
        assert "f74a5763-3270-4151-9c49-853710220208" in smart_str(response.content)
        assert "888981" in smart_str(response.content)
        assert "Linux" in smart_str(response.content)
        assert "2017-01-31 23:12:57" in smart_str(response.content)
        # Test facets are existing
        assert 'table id="facets-list-' in smart_str(response.content)
        # Test bugs are existing
        assert '<th scope="col">Bugs</th>' in smart_str(response.content)
        assert "123456" in smart_str(response.content)
        # Test links on terms are existing
        assert "build_id=%3D888981" in smart_str(response.content)
        # Refine links to the product should not be "is" queries
        assert "product=WaterWolf" in smart_str(response.content)
        # Refine links have values that are urlencoded (this is also a field that should
        # not be an "is" query)
        assert "platform=%3CLinux%3E" in smart_str(response.content)

        # Test with empty results
        response = self.client.get(url, {"product": "NightTrain", "date": "2012-01-01"})
        assert response.status_code == 200
        assert 'table id="reports-list"' not in smart_str(response.content)
        assert "No results were found" in smart_str(response.content)

        # Test with a signature param
        response = self.client.get(url, {"signature": "~nsASDOMWindowEnumerator"})
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        assert "nsASDOMWindowEnumerator::GetNext()" in smart_str(response.content)
        assert "123456" in smart_str(response.content)

        # Test with a different facet
        response = self.client.get(url, {"_facets": "build_id", "product": "SeaMonkey"})
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        assert 'table id="facets-list-' in smart_str(response.content)
        assert "888981" in smart_str(response.content)
        # Bugs should not be there, they appear only in the signature facet
        assert "<th>Bugs</th>" not in smart_str(response.content)
        assert "123456" not in smart_str(response.content)

        # Test with a different columns list
        response = self.client.get(
            url, {"_columns": ["build_id", "platform"], "product": "WaterWolf"}
        )
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        assert 'table id="facets-list-' in smart_str(response.content)
        # The build and platform appear
        assert "888981" in smart_str(response.content)
        assert "Linux" in smart_str(response.content)
        # The crash id is always shown
        assert "f74a5763-3270-4151-9c49-853710220208" in smart_str(response.content)
        # The version and date do not appear
        assert "1.0" not in smart_str(response.content)
        assert "2017" not in smart_str(response.content)

        # Test missing parameters don't raise an exception.
        response = self.client.get(
            url, {"product": "WaterWolf", "date": "", "build_id": ""}
        )
        assert response.status_code == 200

    def test_search_results_metrics(self):
        def mocked_supersearch_get(**params):
            return {"hits": [], "facets": [], "total": 0}

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_results")
        with MetricsMock() as metrics_mock:
            response = self.client.get(url, {"product": "WaterWolf"})
        assert response.status_code == 200
        metrics_mock.assert_timing(
            "webapp.view.pageview",
            tags=[
                "ajax:false",
                "api:false",
                "path:search_results_",
                "status:200",
            ],
        )

    def test_search_results_ratelimited(self):
        def mocked_supersearch_get(**params):
            return {"hits": [], "facets": [], "total": 0}

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_results")
        limit = int(re.findall(r"(\d+)", settings.RATELIMIT_SUPERSEARCH)[0])
        params = {"product": "WaterWolf"}
        # double to avoid https://bugzilla.mozilla.org/show_bug.cgi?id=1148470
        for i in range(limit * 2):
            self.client.get(url, params)
        # NOTE(willkg): this way of denoting AJAX requests may not work with all
        # JS frameworks
        response = self.client.get(url, params, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert response.status_code == 429
        assert smart_str(response.content) == "Too Many Requests"
        assert response["content-type"] == "text/plain"

    def test_search_results_badargumenterror(self):
        def mocked_supersearch_get(**params):
            raise BadArgumentError("<script>xss")

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_results")
        params = {"product": "WaterWolf"}
        response = self.client.get(url, params, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert response.status_code == 400
        assert response["content-type"] == "text/html; charset=utf-8"
        assert "<script>" not in smart_str(response.content)
        assert "&lt;script&gt;" in smart_str(response.content)

    def test_search_results_admin_mode(self):
        """Test that an admin can see more fields, and that a non-admin cannot."""

        def mocked_supersearch_get(**params):
            assert "_columns" in params

            if "_facets" in params and "url" in params["_facets"]:
                facets = {
                    "platform": [{"term": "Linux", "count": 3}],
                    "url": [{"term": "http://example.org", "count": 3}],
                }
            else:
                facets = {"platform": [{"term": "Linux", "count": 3}]}

            results = {
                "hits": [
                    {
                        "signature": "nsASDOMWindowEnumerator::GetNext()",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "f74a5763-3270-4151-9c49-853710220208",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": 888981,
                        "url": "http://example.org",
                        "exploitability": "high",
                    },
                    {
                        "signature": "mySignatureIsCool",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "63e199c4-d0a6-4386-93c7-8d72a0220208",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": 888981,
                        "url": "http://example.org",
                        "exploitability": "low",
                    },
                    {
                        "signature": "mineIsCoolerThanYours",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "e325b443-1b51-402b-b2c5-ccd630220208",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": None,
                        "url": "http://example.org",
                        "exploitability": "error",
                    },
                ],
                "facets": facets,
                "total": 3,
            }
            results["hits"] = self.only_certain_columns(
                results["hits"], params["_columns"]
            )
            return results

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_results")

        # Logged in user, can see protected data fields
        user = self._login()
        group = self._create_group_with_permission("view_pii")
        user.groups.add(group)

        response = self.client.get(
            url,
            {
                "_columns": ["version", "url", "exploitability"],
                "_facets": ["url", "platform"],
            },
        )

        assert response.status_code == 200
        assert "Url facet" in smart_str(response.content)
        assert "http://example.org" in smart_str(response.content)
        assert "Version" in smart_str(response.content)
        assert "1.0" in smart_str(response.content)

        # Without the correct permission the user cannot see exploitability.
        assert "Exploitability" not in smart_str(response.content)

        exp_group = self._create_group_with_permission("view_exploitability")
        user.groups.add(exp_group)

        response = self.client.get(
            url,
            {
                "_columns": ["version", "url", "exploitability"],
                "_facets": ["url", "platform"],
            },
        )

        assert response.status_code == 200
        assert "Exploitability" in smart_str(response.content)
        assert "high" in smart_str(response.content)

        # Logged out user, cannot see the protected data fields
        self._logout()
        response = self.client.get(
            url,
            {"_columns": ["version", "url"], "_facets": ["url", "platform"]},
        )

        assert response.status_code == 200
        assert "Url facet" not in smart_str(response.content)
        assert "http://example.org" not in smart_str(response.content)
        assert "Version" in smart_str(response.content)
        assert "1.0" in smart_str(response.content)

    def test_search_results_parameters(self):
        def mocked_supersearch_get(**params):
            # Verify that all expected parameters are in the URL.
            assert "product" in params
            assert "WaterWolf" in params["product"]
            assert "NightTrain" in params["product"]

            assert "address" in params
            assert "0x00000000" in params["address"]
            assert "0xa0000000" in params["address"]

            assert "reason" in params
            assert "^hello" in params["reason"]
            assert "$thanks" in params["reason"]

            assert "java_stack_trace" in params
            assert "Exception" in params["java_stack_trace"]

            return {"hits": [], "facets": "", "total": 0}

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_results")

        response = self.client.get(
            url,
            {
                "product": ["WaterWolf", "NightTrain"],
                "address": ["0x00000000", "0xa0000000"],
                "reason": ["^hello", "$thanks"],
                "java_stack_trace": "Exception",
            },
        )
        assert response.status_code == 200

    def test_search_results_pagination(self):
        """Test that the pagination of results works as expected."""

        def mocked_supersearch_get(**params):
            assert "_columns" in params

            # Make sure a negative page does not lead to negative offset value.
            # But instead it is considered as the page 1 and thus is not added.
            assert params.get("_results_offset") == 0

            hits = []
            for i in range(140):
                crashid = f"{i:04d}5763-3270-4151-9c49-853710220208"
                hits.append(
                    {
                        "signature": "hang | nsASDOMWindowEnumerator::GetNext()",
                        "date": "2017-01-31T23:12:57",
                        "uuid": crashid,
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": 888981,
                    }
                )
            return {
                "hits": self.only_certain_columns(hits, params["_columns"]),
                "facets": "",
                "total": len(hits),
            }

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_results")

        response = self.client.get(
            url,
            {
                "signature": "hang | nsASDOMWindowEnumerator::GetNext()",
                "_columns": ["version"],
                "_facets": ["platform"],
            },
        )

        assert response.status_code == 200
        assert "140" in smart_str(response.content)

        # Check that the pagination URL contains all three expected parameters.
        doc = pyquery.PyQuery(response.content)
        next_page_url = str(doc(".pagination a").eq(0))
        assert "_facets=platform" in next_page_url
        assert "_columns=version" in next_page_url
        assert "page=2" in next_page_url
        assert "#crash-reports" in next_page_url

        # Verify white spaces are correctly encoded.
        # Note we use `quote` and not `quote_plus`, so white spaces are
        # turned into '%20' instead of '+'.
        assert quote("hang | nsASDOMWindowEnumerator::GetNext()") in next_page_url

        # Test that a negative page value does not break it.
        response = self.client.get(url, {"page": "-1"})
        assert response.status_code == 200

    def create_custom_query_perm(self):
        user = self._login()
        group = self._create_group_with_permission("run_custom_queries")
        user.groups.add(group)

    def test_search_custom_permission(self):
        def mocked_supersearch_get(**params):
            return None

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_custom")
        response = self.client.get(url)
        assert response.status_code == 302

        self.create_custom_query_perm()

        response = self.client.get(url)
        assert response.status_code == 200
        assert "Run a search to get some results" in smart_str(response.content)

    def test_search_custom(self):
        def mocked_supersearch_get(**params):
            return None

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        self.create_custom_query_perm()

        url = reverse("supersearch:search_custom")
        response = self.client.get(url)
        assert response.status_code == 200
        assert "Run a search to get some results" in smart_str(response.content)

    def test_search_custom_metrics(self):
        def mocked_supersearch_get(**params):
            return None

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        self.create_custom_query_perm()

        url = reverse("supersearch:search_custom")
        with MetricsMock() as metrics_mock:
            response = self.client.get(url)
        assert response.status_code == 200

        metrics_mock.assert_timing(
            "webapp.view.pageview",
            tags=[
                "ajax:false",
                "api:false",
                "path:search_custom_",
                "status:200",
            ],
        )

    def test_search_custom_parameters(self):
        self.create_custom_query_perm()

        def mocked_supersearch_get(**params):
            assert "_return_query" in params
            assert "signature" in params
            assert params["signature"] == ["nsA"]

            return {
                "query": {"query": None},
                "indices": ["socorro200000", "socorro200001"],
            }

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = reverse("supersearch:search_custom")
        response = self.client.get(url, {"signature": "nsA"})
        assert response.status_code == 200
        assert "Run a search to get some results" in smart_str(response.content)
        assert "{&#34;query&#34;: null}" in smart_str(response.content)
        assert "socorro200000" in smart_str(response.content)
        assert "socorro200001" in smart_str(response.content)

    def test_search_query(self):
        self.create_custom_query_perm()

        def mocked_query_get(**params):
            assert "query" in params

            return {"hits": []}

        Query.implementation().get.side_effect = mocked_query_get

        url = reverse("supersearch:search_query")
        response = self.client.post(url, {"query": '{"query": {}}'})
        assert response.status_code == 200

        content = json.loads(response.content)
        assert "hits" in content
        assert content["hits"] == []

        # Test a failure.
        response = self.client.post(url)
        assert response.status_code == 400
        assert "query" in smart_str(response.content)

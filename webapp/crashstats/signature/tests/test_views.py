# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import json
from unittest import mock
from urllib.parse import quote

import pyquery

from django.urls import reverse
from django.utils.encoding import smart_str

from crashstats.crashstats import models
from socorro.lib.libdatetime import date_to_string, utc_now
from socorro.lib.libooid import create_new_ooid, date_from_ooid


TEST_SIGNATURE = "shutdownhang | js::NewProxyObject"


def get_date_range(crash_id=None, date=None):
    if crash_id and not date:
        date = date_from_ooid(crash_id) - datetime.timedelta(days=1)
    if not date:
        raise Exception("crash_id or date must be provided")
    start_date = date.strftime("%Y-%m-%d")
    end_date = (date + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    return start_date, end_date


class TestViews:
    def test_signature_report(self, client, db, es_helper):
        url = reverse("signature:signature_report")
        response = client.get(url, {"signature": TEST_SIGNATURE})
        assert response.status_code == 200
        assert TEST_SIGNATURE in smart_str(response.content)
        assert "Loading" in smart_str(response.content)

    def test_signature_reports(self, client, db, es_helper):
        def build_crash_data(crash_id, **params):
            data = {
                "date_processed": date_to_string(date_from_ooid(crash_id)),
                "uuid": crash_id,
                "product": "Firefox",
                "signature": TEST_SIGNATURE,
                "version": "1.0",
                "os_name": "Linux",
            }
            data.update(params)
            return data

        crash1_id = create_new_ooid()
        crash1 = build_crash_data(
            crash1_id,
            build=888981,
            cpu_info="FakeAMD family 20 model 42",
        )
        crash2_id = create_new_ooid()
        crash2 = build_crash_data(
            crash2_id,
            build=888981,
            cpu_info="AuthenticAMD family 20 model 1",
        )
        crash3_id = create_new_ooid()
        crash3 = build_crash_data(crash3_id, build=None)
        crash4_id = create_new_ooid()
        crash4 = build_crash_data(crash4_id, build=None)

        for crash_data in [crash1, crash2, crash3, crash4]:
            es_helper.index_crash(
                raw_crash={}, processed_crash=crash_data, refresh=False
            )
        es_helper.refresh()

        start_date, end_date = get_date_range(crash1_id)
        crash1_date_processed = date_from_ooid(crash1_id).strftime("%Y-%m-%d %H:%M:%S")

        # Test with no results.
        url = reverse("signature:signature_reports")
        response = client.get(
            url,
            {
                "signature": "wrong signature",
                "product": "Firefox",
                "date": [f">={start_date}", f"<{end_date}"],
            },
        )
        assert response.status_code == 200
        assert 'table id="reports-list"' not in smart_str(response.content)
        assert "No results were found" in smart_str(response.content)

        # Test with results.
        response = client.get(
            url,
            {
                "signature": TEST_SIGNATURE,
                "product": "Firefox",
                "date": [f">={start_date}", f"<{end_date}"],
            },
        )
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        assert crash1["uuid"] in smart_str(response.content)
        assert str(crash1["build"]) in smart_str(response.content)
        assert crash1["os_name"] in smart_str(response.content)
        assert crash1_date_processed in smart_str(response.content)
        # The cpu_info doesn't show up in the reports list by default
        assert crash1["cpu_info"] not in smart_str(response.content)

        # Test with a different columns list.
        response = client.get(
            url,
            {
                "signature": TEST_SIGNATURE,
                "product": "Firefox",
                "date": [f">={start_date}", f"<{end_date}"],
                "_columns": ["build_id", "platform"],
            },
        )
        assert response.status_code == 200
        assert 'table id="reports-list"' in smart_str(response.content)
        # The build and platform appear
        assert str(crash1["build"]) in smart_str(response.content)
        assert crash1["os_name"] in smart_str(response.content)
        # The crash id is always shown
        assert crash1["uuid"] in smart_str(response.content)
        # The version and date do not appear
        assert crash1["version"] not in smart_str(response.content)
        assert crash1_date_processed not in smart_str(response.content)

    def test_missing_parameters(self, client, db, es_helper):
        url = reverse("signature:signature_reports")

        # Test missing parameter.
        response = client.get(url)
        assert response.status_code == 400

        response = client.get(url, {"signature": ""})
        assert response.status_code == 400

    def test_parameter_parsing(self, client, db, es_helper):
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

            date = utc_now().strftime("%Y-%m-%d")

            url = reverse("signature:signature_reports")
            response = client.get(
                url,
                {
                    "signature": TEST_SIGNATURE,
                    "product": ["Firefox", "Thunderbird"],
                    "address": ["0x0", "0xa"],
                    "reason": ["^hello", "$thanks"],
                    "date": [f">={date}"],
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
            assert "0x0" in params["address"]
            assert "0xa" in params["address"]
            assert "^hello" in params["reason"]
            assert "$thanks" in params["reason"]
            assert "Exception" in params["java_stack_trace"]

    def test_signature_reports_pagination(self, client, db, es_helper):
        """Test that the pagination of results works as expected"""

        def build_crash_data(i):
            # Make crash ids unique with the first 6 characters being i
            crash_id = create_new_ooid()
            crash_id = f"{i:06d}{crash_id[6:]}"

            # Make the date_processed unique and sortable by adding i * 5 minutes
            date = date_from_ooid(crash_id) + datetime.timedelta(minutes=i * 5)

            return {
                "date_processed": date_to_string(date),
                "uuid": crash_id,
                "signature": TEST_SIGNATURE,
                "product": "Firefox",
                "version": "1.0",
                "os_name": "Linux",
                "build": 888981,
            }

        crash_ids = []
        for i in range(140):
            data = build_crash_data(i)
            es_helper.index_crash(raw_crash={}, processed_crash=data, refresh=False)
            crash_ids.append(data["uuid"])

        es_helper.refresh()

        start_date, end_date = get_date_range(crash_ids[0])
        url = reverse("signature:signature_reports")

        response = client.get(
            url,
            {
                "signature": TEST_SIGNATURE,
                "product": ["Firefox"],
                "date": [f">={start_date}", f"<{end_date}"],
                "page": "1",
                "_columns": ["platform"],
                "_sort": "-date",
            },
        )

        assert response.status_code == 200

        doc = pyquery.PyQuery(response.content)
        crashids = doc("a.crash-id")

        # Assert that 50 crashes are rendered--that's a full page
        assert len(crashids) == 50

        # Newest crash should be in the page
        assert crash_ids[-1] in smart_str(response.content)

        # Oldest crash should not be in the page
        assert crash_ids[0] not in smart_str(response.content)

        # Check that the pagination URL contains all three expected parameters.
        next_page_url = str(doc(".pagination a").eq(0))
        assert "product=Firefox" in next_page_url
        assert "_columns=platform" in next_page_url
        assert "page=2" in next_page_url

        # Verify white spaces are correctly encoded.
        # Note we use `quote` and not `quote_plus`, so white spaces are turned into
        # '%20' instead of '+'.
        assert quote(TEST_SIGNATURE) in next_page_url

        # Test that a negative page value does not break it.
        response = client.get(url, {"signature": TEST_SIGNATURE, "page": "-1"})
        assert response.status_code == 200

    def test_signature_aggregation(self, client, db, es_helper):
        def build_crash_data(i, products):
            # Make crash ids unique with the first 6 characters being i
            crash_id = create_new_ooid()
            crash_id = f"{i:06d}{crash_id[6:]}"

            # Make the date_processed unique and sortable by adding i minutes
            date = date_from_ooid(crash_id) + datetime.timedelta(minutes=i)

            return {
                "date_processed": date_to_string(date),
                "uuid": crash_id,
                "signature": TEST_SIGNATURE,
                "product": products[i],
                "version": "1.0",
                "build": 888981,
            }

        products = []
        products.extend(["Firefox"] * 9)
        products.extend(["Fenix"] * 5)
        products.extend(["Thunderbird"] * 2)

        crash_ids = []
        for i in range(len(products)):
            data = build_crash_data(i, products)
            es_helper.index_crash(raw_crash={}, processed_crash=data, refresh=False)
            crash_ids.append(data["uuid"])

        es_helper.refresh()

        # Aggregate on platform--there's no data, so no results.
        url = reverse("signature:signature_aggregation", args=("platform",))
        response = client.get(url, {"signature": TEST_SIGNATURE})
        assert response.status_code == 200
        assert "Product" not in smart_str(response.content)
        assert "No results were found" in smart_str(response.content)

        # Aggregate on product
        url = reverse("signature:signature_aggregation", args=("product",))
        response = client.get(url, {"signature": TEST_SIGNATURE})
        assert response.status_code == 200
        assert "Product" in smart_str(response.content)
        assert "Firefox" in smart_str(response.content)
        assert "Fenix" in smart_str(response.content)
        assert "Thunderbird" in smart_str(response.content)

    def test_signature_graphs(self, client, db, es_helper):
        def build_crash_data(i, days, product):
            date = utc_now() - datetime.timedelta(days=days)
            crash_id = create_new_ooid(date)

            return {
                "date_processed": date_to_string(date),
                "uuid": crash_id,
                "signature": TEST_SIGNATURE,
                "product": product,
                "version": "1.0",
                "build": 888981,
            }

        test_data = [
            (0, "Firefox"),
            (0, "Fenix"),
            (0, "Fenix"),
            (0, "Firefox"),
            (0, "Firefox"),
            (0, "Thunderbird"),
            (1, "Firefox"),
            (1, "Fenix"),
            (1, "Firefox"),
            (1, "Firefox"),
            (2, "Firefox"),
            (2, "Firefox"),
            (2, "Firefox"),
        ]

        crash_ids = []
        for i, item in enumerate(test_data):
            data = build_crash_data(i, days=item[0], product=item[1])
            es_helper.index_crash(raw_crash={}, processed_crash=data, refresh=False)
            crash_ids.append(data["uuid"])

        es_helper.refresh()

        # Graph platform which has no data
        url = reverse("signature:signature_graphs", args=("platform",))
        response = client.get(url, {"signature": TEST_SIGNATURE})
        assert response.status_code == 200
        assert "application/json" in response["content-type"]
        struct = json.loads(response.content)

        # We have three days worth of stuff
        assert "aggregates" in struct
        assert len(struct["aggregates"]) == 3

        # We have no kinds of platform
        assert "term_counts" in struct
        assert len(struct["term_counts"]) == 0

        # Graph product which has data
        url = reverse("signature:signature_graphs", args=("product",))
        response = client.get(url, {"signature": TEST_SIGNATURE})
        assert response.status_code == 200
        assert "application/json" in response["content-type"]
        struct = json.loads(response.content)

        # We have 3 days worth of stuff
        assert "aggregates" in struct
        assert len(struct["aggregates"]) == 3

        # We have three kinds of products: Firefox, Fenix, Thunderbird
        assert "term_counts" in struct
        assert len(struct["term_counts"]) == 3

    def test_signature_comments_no_permission(self, client, db):
        """Verify comments are not viewable without view_pii."""
        url = reverse("signature:signature_comments")

        response = client.get(url, {"signature": "whatever"})
        assert response.status_code == 403

    def test_signature_comments(self, client, db, es_helper, user_helper):
        def build_crash_data(crash_id, **params):
            data = {
                "date_processed": date_to_string(date_from_ooid(crash_id)),
                "uuid": crash_id,
                "product": "Firefox",
                "signature": TEST_SIGNATURE,
                "version": "1.0",
                "os_name": "Linux",
            }
            data.update(params)
            return data

        crash1_id = create_new_ooid()
        crash1 = build_crash_data(
            crash1_id,
            user_comments="hello!",
            useragent_locale="locale1",
        )
        crash2_id = create_new_ooid()
        crash2 = build_crash_data(
            crash2_id,
            user_comments="love mozilla",
            useragent_locale="locale2",
        )
        crash3_id = create_new_ooid()
        crash3 = build_crash_data(
            crash3_id,
            user_comments="product is awesome",
            useragent_locale="locale3",
        )
        crash4_id = create_new_ooid()
        crash4 = build_crash_data(
            crash4_id,
            user_comments="it crashed",
            useragent_locale="locale4",
        )

        for crash_data in [crash1, crash2, crash3, crash4]:
            es_helper.index_crash(
                raw_crash={}, processed_crash=crash_data, refresh=False
            )
        es_helper.refresh()

        url = reverse("signature:signature_comments")

        # Anonymous users can't see comments
        response = client.get(url, {"signature": TEST_SIGNATURE, "product": "Firefox"})
        assert response.status_code == 403

        # Log in with user with protected data access
        user = user_helper.create_protected_user()
        client.force_login(user)

        # Test with results.
        response = client.get(url, {"signature": TEST_SIGNATURE, "product": "Firefox"})
        assert response.status_code == 200
        assert "Crash ID" in smart_str(response.content)
        assert crash1_id in smart_str(response.content)
        assert "hello!" in smart_str(response.content)
        assert "love mozilla" in smart_str(response.content)
        assert "product is awesome" in smart_str(response.content)
        assert "it crashed" in smart_str(response.content)

    def test_signature_comments_pagination(self, client, db, es_helper, user_helper):
        """Test that the pagination of comments works as expected"""

        def build_crash_data(i):
            # Make crash ids unique with the first 6 characters being i
            crash_id = create_new_ooid()
            crash_id = f"{i:06d}{crash_id[6:]}"

            # Make the date_processed unique and sortable by adding i * 5 minutes
            date = date_from_ooid(crash_id) + datetime.timedelta(minutes=i * 5)

            return {
                "date_processed": date_to_string(date),
                "uuid": crash_id,
                "signature": TEST_SIGNATURE,
                "product": "Firefox",
                "version": "1.0",
                "os_name": "Linux",
                "user_comments": f"it crashed ==={i}===:",
                "build": 888981,
            }

        crash_ids = []
        for i in range(140):
            data = build_crash_data(i)
            es_helper.index_crash(raw_crash={}, processed_crash=data, refresh=False)
            crash_ids.append(data["uuid"])

        es_helper.refresh()

        user = user_helper.create_protected_user()
        client.force_login(user)

        start_date, end_date = get_date_range(crash_ids[0])
        url = reverse("signature:signature_comments")

        response = client.get(
            url,
            {
                "signature": TEST_SIGNATURE,
                "product": ["Firefox"],
                "date": [f">={start_date}", f"<{end_date}"],
            },
        )
        doc = pyquery.PyQuery(response.content)

        assert response.status_code == 200
        # Newest crash is rendered
        assert crash_ids[-1] in smart_str(response.content)
        assert "===139===" in smart_str(response.content)
        # Oldest crash is not rendered
        assert crash_ids[0] not in smart_str(response.content)
        assert "===0===" not in smart_str(response.content)

        # Check that the pagination URL contains all expected parameters.
        doc = pyquery.PyQuery(response.content)
        next_page_url = str(doc(".pagination a").eq(0))
        assert "product=Firefox" in next_page_url
        assert "page=2" in next_page_url

        response = client.get(
            url,
            {
                "signature": TEST_SIGNATURE,
                "product": ["Firefox"],
                "date": [f">={start_date}", f"<{end_date}"],
                "page": 3,
            },
        )
        assert response.status_code == 200
        # Newest crash is not rendered--it was on page 1
        assert crash_ids[-1] not in smart_str(response.content)
        assert "===139===" not in smart_str(response.content)
        # Oldest crash is rendered
        assert crash_ids[0] in smart_str(response.content)
        assert "===0===" in smart_str(response.content)

    def test_signature_summary(self, client, db, es_helper):
        models.GraphicsDevice.objects.create(
            vendor_hex="0x0086",
            adapter_hex="0x1234",
            vendor_name="Intel",
            adapter_name="Device",
        )
        models.GraphicsDevice.objects.create(
            vendor_hex="0x0086",
            adapter_hex="0x1239",
            vendor_name="Intel",
            adapter_name="Other",
        )

        def build_crash_data(**params):
            crash_id = params.pop("crash_id", create_new_ooid())
            data = {
                "date_processed": date_to_string(date_from_ooid(crash_id)),
                "uuid": crash_id,
                "product": "Fenix",
                "signature": TEST_SIGNATURE,
                "version": "1.0",
                "process_type": "content",
                "cpu_arch": "arm64",
                "os_pretty_version": "Android",
            }
            data.update(params)
            return data

        crash_data = [
            build_crash_data(
                version="100.1.2",
                adapter_device_id="0x1234",
                adapter_vendor_id="0x0086",
                android_cpu_abi="arm64-v8a",
                android_manufacturer="Joan",
                android_model="Jet",
                android_version=15,
                uptime=1000,
            ),
            build_crash_data(
                version="100.1.2",
                adapter_device_id="0x1234",
                adapter_vendor_id="0x0086",
                android_cpu_abi="arm64-v8a",
                android_manufacturer="Jerry",
                android_model="Racecar",
                android_version=15,
                uptime=1000,
            ),
            build_crash_data(
                version="102.1.1",
                adapter_device_id="0x1239",
                adapter_vendor_id="0x0086",
                android_cpu_abi="arm64-v8a",
                android_manufacturer="Jerry",
                android_model="Racecar",
                android_version=15,
                uptime=5000,
            ),
            build_crash_data(
                version="102.1.1",
                adapter_device_id="0x1239",
                adapter_vendor_id="0x0086",
                android_cpu_abi="arm64-v8a",
                android_manufacturer="Jerry",
                android_model="Racecar",
                android_version=15,
                uptime=5000,
            ),
        ]
        for item in crash_data:
            es_helper.index_crash(raw_crash={}, processed_crash=item, refresh=False)
        es_helper.refresh()

        start_date, end_date = get_date_range(date=utc_now())

        url = reverse("signature:signature_summary")
        response = client.get(
            url,
            {
                "signature": TEST_SIGNATURE,
                "product": "Fenix",
                "date": [f">={start_date}", f"<{end_date}"],
            },
        )
        assert response.status_code == 200

        # Make sure all boxes are there
        assert "Operating System" in smart_str(response.content)
        assert "Uptime Range" in smart_str(response.content)
        assert "Product" in smart_str(response.content)
        assert "Architecture" in smart_str(response.content)
        assert "Process Type" in smart_str(response.content)
        assert "Mobile Devices" in smart_str(response.content)
        assert "Graphics Adapter" in smart_str(response.content)

        # Check that some of the expected values are there

        # Operating system
        assert "Android" in smart_str(response.content)

        # Product
        assert "Fenix" in smart_str(response.content)
        assert "102.1.1" in smart_str(response.content)

        # Process type
        assert "content" in smart_str(response.content)

        # Graphics Adapter
        assert "Intel (0x0086)" in smart_str(response.content)

        # Uptime Range
        assert "15-60 min" in smart_str(response.content)

        # Mobile devices content
        assert "arm64-v8a" in smart_str(response.content)
        assert "Jerry" in smart_str(response.content)

    def test_signature_bugzilla(self, client, db, es_helper):
        models.BugAssociation.objects.create(bug_id=111111, signature="Something")
        models.BugAssociation.objects.create(bug_id=111111, signature="OOM | small")
        models.BugAssociation.objects.create(bug_id=123456789, signature="Something")

        # Test with signature that has no bugs
        url = reverse("signature:signature_bugzilla")
        response = client.get(
            url, {"signature": "hang | mozilla::wow::such_signature(smth*)"}
        )
        assert response.status_code == 200
        assert "There are no bugs" in smart_str(response.content)

        # Test with signature that has bugs and related bugs
        response = client.get(url, {"signature": "Something"})
        assert response.status_code == 200
        assert "123456789" in smart_str(response.content)
        assert "111111" in smart_str(response.content)

        # because bug id 123456789 is > than 111111 we expect that order
        # in the rendered output
        content = smart_str(response.content)
        assert (
            content.find("123456789")
            < content.find("111111")
            < content.find("Related Crash Signatures")
            < content.find("Bugs for <code>OOM | small</code>")
        )

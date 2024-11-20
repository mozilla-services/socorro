# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime

import freezegun
import pyquery

from django.urls import reverse
from django.utils.encoding import smart_str

from crashstats.crashstats.models import Signature, BugAssociation
from socorro.lib.libdatetime import utc_now
from socorro.lib.libooid import create_new_ooid


class TestTopCrasherViews:
    def test_topcrashers_bug_data(self, client, db, preferred_es_helper):
        signature = "FakeSignature1"

        BugAssociation.objects.create(bug_id=22222, signature=signature)
        BugAssociation.objects.create(bug_id=33333, signature=signature)

        # Index crash data for signature with associated bugs
        crash_data = []
        now = utc_now() - datetime.timedelta(days=1)
        for _ in range(15):
            crash_data.append(
                {
                    "date_processed": now,
                    "uuid": create_new_ooid(timestamp=now),
                    "signature": signature,
                    "product": "Firefox",
                    "version": "1.0",
                    "dom_fission_enabled": True,
                    "is_garbage_collecting": False,
                    "os_name": "Linux",
                    "process_type": "parent",
                    "report_type": "crash",
                    "startup_crash": True,
                    "uptime": 1000,
                }
            )
        for item in crash_data:
            preferred_es_helper.index_crash(processed_crash=item, refresh=False)
        preferred_es_helper.refresh()

        # Test Bugzilla data is rendered
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "version": "1.0"})
        assert response.status_code == 200
        print(response.content.decode("utf-8"))
        doc = pyquery.PyQuery(response.content)
        # Verify Bugzilla IDs data
        bug_ids = [x.text for x in doc("td.bug_ids_more > a")]
        # Verify bugs are sorted by bug id descending
        assert bug_ids == ["33333", "22222"]

    def test_topcrashers_first_appearance(self, client, db, preferred_es_helper):
        signature = "FakeSignature1"

        Signature.objects.create(
            signature=signature,
            first_date=datetime.datetime(
                2021, 1, 1, 12, 23, 34, tzinfo=datetime.timezone.utc
            ),
            first_build="20000101122334",
        )

        # Index crashes with signature with first build date
        crash_data = []
        now = utc_now() - datetime.timedelta(days=1)
        for _ in range(55):
            crash_data.append(
                {
                    "date_processed": now,
                    "uuid": create_new_ooid(timestamp=now),
                    "signature": signature,
                    "product": "Firefox",
                    "version": "1.0",
                    "dom_fission_enabled": True,
                    "is_garbage_collecting": False,
                    "os_name": "Linux",
                    "process_type": "parent",
                    "report_type": "crash",
                    "startup_crash": True,
                    "uptime": 1000,
                }
            )
        for item in crash_data:
            preferred_es_helper.index_crash(processed_crash=item, refresh=False)
        preferred_es_helper.refresh()

        # Check the first appearance date is there
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "version": "1.0"})
        assert response.status_code == 200
        assert "2021-01-01 12:23:34" in smart_str(response.content)

    def test_topcrashers_multiple_version(self, client, db, preferred_es_helper):
        # Test that querying several versions do not raise an error
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "version": ["1.0", "2.0"]})
        assert response.status_code == 200

    def test_topcrashers_result_count(self, client, db, preferred_es_helper):
        url = reverse("topcrashers:topcrashers")

        # Test default results count is 50
        response = client.get(url, {"product": "Firefox", "version": "1.0"})
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        assert selected_count.text() == "50"

        # Test setting results count to 100
        response = client.get(
            url,
            {"product": "Firefox", "version": "1.0", "_facets_size": "100"},
        )
        assert response.status_code == 200
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        assert selected_count.text() == "100"

    def test_topcrashers_startup_crash(self, client, db, preferred_es_helper):
        def build_crash_data(**params):
            crash_id = create_new_ooid()
            data = {
                "date_processed": utc_now(),
                "uuid": crash_id,
                "signature": "FakeSignature1",
                "dom_fission_enabled": True,
                "is_garbage_collecting": False,
                "os_name": "Linux",
                "process_type": "parent",
                "report_type": "crash",
            }
            data.update(params)
            return data

        crash_data = []

        # Startup crash data--all are startup_crash=True
        for _ in range(55):
            crash_data.append(
                build_crash_data(
                    product="Firefox",
                    version="1.0",
                    startup_crash=True,
                    uptime=1,
                )
            )

        # Potential startup crash data--all are startup_crash=True except first 5
        for i in range(55):
            startup_crash = i > 5
            crash_data.append(
                build_crash_data(
                    product="Firefox",
                    version="2.0",
                    startup_crash=startup_crash,
                    uptime=1 if startup_crash else 500,
                )
            )

        # Not startup crash data--none are startup_crash
        for _ in range(55):
            crash_data.append(
                build_crash_data(
                    product="Firefox",
                    version="3.0",
                    startup_crash=False,
                    uptime=500,
                )
            )

        for item in crash_data:
            preferred_es_helper.index_crash(processed_crash=item, refresh=False)
        preferred_es_helper.refresh()

        startup_crash_msg = 'title="Startup Crash"'
        potential_startup_crash_msg = 'title="Potential Startup Crash"'
        potential_startup_window_crash_msg = (
            'title="Potential Startup Crash, more than half of the crashes happened '
            'during the first minute after launch"'
        )

        # Request Firefox 1.0 where crash data is startup_crash=True
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "version": "1.0"})
        assert response.status_code == 200
        assert startup_crash_msg in smart_str(response.content)
        assert potential_startup_crash_msg not in smart_str(response.content)
        assert potential_startup_window_crash_msg in smart_str(response.content)

        # Request Firefox 2.0 where most crash data is startup_crash=True
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "version": "2.0"})
        assert response.status_code == 200
        assert startup_crash_msg not in smart_str(response.content)
        assert potential_startup_crash_msg in smart_str(response.content)
        assert potential_startup_window_crash_msg in smart_str(response.content)

        # Request Firefox 3.0 where crash data is startup_crash=False
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "version": "3.0"})
        assert response.status_code == 200
        assert startup_crash_msg not in smart_str(response.content)
        assert potential_startup_crash_msg not in smart_str(response.content)
        assert potential_startup_window_crash_msg not in smart_str(response.content)

    def test_product_sans_featured_version(self, client, db, preferred_es_helper):
        # Index a bunch of version=1.0 data so we have an active version
        crash_data = []
        # Use yesterday so featured versions picks up the crash reports
        now = utc_now() - datetime.timedelta(days=1)
        for _ in range(105):
            crash_data.append(
                {
                    "date_processed": now,
                    "uuid": create_new_ooid(timestamp=now),
                    "signature": "FakeSignature1",
                    "product": "Firefox",
                    "version": "1.0",
                    "dom_fission_enabled": True,
                    "is_garbage_collecting": False,
                    "os_name": "Linux",
                    "process_type": "parent",
                    "report_type": "crash",
                    "startup_crash": False,
                    "uptime": 500,
                }
            )

        for item in crash_data:
            preferred_es_helper.index_crash(processed_crash=item, refresh=False)
        preferred_es_helper.refresh()

        # Redirects to the most recent featured version
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox"})
        assert response.status_code == 302
        actual_url = url + "?product=Firefox&version=1.0"
        assert actual_url in response["Location"]

        # This version doesn't exist, but it still renders something and
        # doesn't throw an error
        response = client.get(url, {"product": "Firefox", "version": "9.5"})
        assert response.status_code == 200

    def test_topcrashers_reporttype(self, client, db, preferred_es_helper):
        crashsignature = "FakeCrashSignature1"
        hangsignature = "shutdownhang | foo"

        # Index crash and hang crashes
        crash_data = []
        now = utc_now() - datetime.timedelta(days=1)
        for _ in range(5):
            crash_data.append(
                {
                    "date_processed": now,
                    "uuid": create_new_ooid(timestamp=now),
                    "signature": crashsignature,
                    "product": "Firefox",
                    "version": "1.0",
                    "dom_fission_enabled": True,
                    "is_garbage_collecting": False,
                    "os_name": "Linux",
                    "process_type": "parent",
                    "report_type": "crash",
                    "startup_crash": True,
                    "uptime": 1000,
                }
            )
        for item in crash_data:
            preferred_es_helper.index_crash(processed_crash=item, refresh=False)

        for _ in range(5):
            crash_data.append(
                {
                    "date_processed": now,
                    "uuid": create_new_ooid(timestamp=now),
                    "signature": hangsignature,
                    "product": "Firefox",
                    "version": "1.0",
                    "dom_fission_enabled": True,
                    "is_garbage_collecting": False,
                    "os_name": "Linux",
                    "process_type": "parent",
                    "report_type": "hang",
                    "startup_crash": True,
                    "uptime": 1000,
                }
            )
        for item in crash_data:
            preferred_es_helper.index_crash(processed_crash=item, refresh=False)
        preferred_es_helper.refresh()

        url = reverse("topcrashers:topcrashers")

        # Default yields report_type="crash"
        response = client.get(url, {"product": "Firefox", "version": "1.0"})
        assert response.status_code == 200
        print(response.content.decode("utf-8"))
        assert crashsignature in smart_str(response.content)
        assert hangsignature not in smart_str(response.content)

        # Specify report_type="crash" does the same thing
        response = client.get(
            url, {"product": "Firefox", "version": "1.0", "_report_type": "crash"}
        )
        assert response.status_code == 200
        print(response.content.decode("utf-8"))
        assert crashsignature in smart_str(response.content)
        assert hangsignature not in smart_str(response.content)

        # Specify report_type="hang" shows hangs
        response = client.get(
            url, {"product": "Firefox", "version": "1.0", "_report_type": "hang"}
        )
        assert response.status_code == 200
        print(response.content.decode("utf-8"))
        assert crashsignature not in smart_str(response.content)
        assert hangsignature in smart_str(response.content)

        # Specify report_type="any" shows crashes and hangs
        response = client.get(
            url, {"product": "Firefox", "version": "1.0", "_report_type": "any"}
        )
        assert response.status_code == 200
        print(response.content.decode("utf-8"))
        assert crashsignature in smart_str(response.content)
        assert hangsignature in smart_str(response.content)

    def test_400_by_bad_days(self, client, db, preferred_es_helper):
        url = reverse("topcrashers:topcrashers")
        response = client.get(
            url, {"product": "Firefox", "version": "0.1", "days": "xxxxxx"}
        )
        assert response.status_code == 400
        assert "not a number" in smart_str(response.content)
        assert response["Content-Type"] == "text/html; charset=utf-8"

    def test_400_by_bad_facets_size(self, client, db, preferred_es_helper):
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "_facets_size": "notanumber"})
        assert response.status_code == 400
        assert "Enter a whole number" in smart_str(response.content)
        assert response["Content-Type"] == "text/html; charset=utf-8"

    def test_with_unsupported_product(self, client, db, preferred_es_helper):
        # SnowLion is not in the mocked Products list
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "SnowLion", "version": "0.1"})
        assert response.status_code == 404

    def test_without_any_signatures(self, client, db, preferred_es_helper):
        url = reverse("topcrashers:topcrashers")
        response = client.get(url, {"product": "Firefox", "version": "19.0"})
        assert response.status_code == 200

    def test_modes(self, client, db, preferred_es_helper):
        now = datetime.datetime.utcnow().replace(microsecond=0)
        today = now.replace(hour=0, minute=0, second=0)

        url = reverse("topcrashers:topcrashers")
        with freezegun.freeze_time(now, tz_offset=0):
            now = now.isoformat()
            today = today.isoformat()

            # By default, it returns "real-time" data.
            response = client.get(url, {"product": "Firefox", "version": "19.0"})
            assert response.status_code == 200
            assert now in smart_str(response.content)
            assert today not in smart_str(response.content)

            # Now test the "day time" data.
            response = client.get(
                url,
                {"product": "Firefox", "version": "19.0", "_tcbs_mode": "byday"},
            )
            assert response.status_code == 200
            assert today in smart_str(response.content)
            assert now not in smart_str(response.content)

    def test_by_build(self, client, db, preferred_es_helper):
        url = reverse("topcrashers:topcrashers")
        response = client.get(
            url,
            {"product": "Firefox", "version": "19.0", "_range_type": "build"},
        )
        assert response.status_code == 200

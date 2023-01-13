# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io

import requests_mock
import pytest

from django.conf import settings
from django.core.management import call_command
from django.test.utils import override_settings

from crashstats.crashstats.models import BugAssociation
from crashstats.crashstats.management.commands.bugassociations import find_signatures


SAMPLE_BUGZILLA_RESULTS = {
    "bugs": [
        {"id": "1", "cf_crash_signature": "This sig, while bogus, has a ] bracket"},
        {
            "id": "2",
            "cf_crash_signature": "single [@ BogusClass::bogus_sig (const char**) ] signature",
        },
        {
            "id": "3",
            "cf_crash_signature": "[@ js3250.dll@0x6cb96] [@ valid.sig@0x333333]",
        },
        {
            "id": "4",
            "cf_crash_signature": "[@ layers::Push@0x123456] [@ layers::Push@0x123456]",
        },
        {
            "id": "5",
            "cf_crash_signature": (
                "[@ MWSBAR.DLL@0x2589f] and a broken one [@ sadTrombone.DLL@0xb4s455"
            ),
        },
        {"id": "6", "cf_crash_signature": ""},
        {
            "id": "7",
            "cf_crash_signature": "[@gfx::font(nsTArray<nsRefPtr<FontEntry> > const&)]",
        },
        {
            "id": "8",
            "cf_crash_signature": "[@ legitimate(sig)] \n junk \n [@ another::legitimate(sig) ]",
        },
        {"id": "42"},
    ]
}


class TestBugAssociationsCommand:
    def fetch_data(self):
        return [
            {"bug_id": ba.bug_id, "signature": ba.signature}
            for ba in BugAssociation.objects.order_by("bug_id", "signature")
        ]

    def insert_data(self, bug_id, signature):
        BugAssociation.objects.create(bug_id=bug_id, signature=signature)

    def test_basic_run_job(self, db):
        api_url = settings.BZAPI_BASE_URL + "/bug"
        with requests_mock.Mocker() as req_mock:
            req_mock.get(api_url, json=SAMPLE_BUGZILLA_RESULTS)

            out = io.StringIO()
            call_command("bugassociations", stdout=out)

        associations = self.fetch_data()

        # Verify we have the expected number of associations
        assert len(associations) == 8
        bug_ids = {x["bug_id"] for x in associations}

        # Verify bugs with no crash signatures are missing
        assert 6 not in bug_ids

        bug_8_signatures = [
            item["signature"] for item in associations if item["bug_id"] == 8
        ]

        # New signatures have correctly been inserted
        assert len(bug_8_signatures) == 2
        assert "another::legitimate(sig)" in bug_8_signatures
        assert "legitimate(sig)" in bug_8_signatures

    def test_bzapi_token(self, db):
        with override_settings(BZAPI_TOKEN="this_token"):
            api_url = settings.BZAPI_BASE_URL + "/bug"
            with requests_mock.Mocker() as req_mock:
                req_mock.get(api_url, json=SAMPLE_BUGZILLA_RESULTS)

                out = io.StringIO()
                call_command("bugassociations", stdout=out)

                first_item = req_mock.request_history[0]
                assert first_item.headers["X-BUGZILLA-API-KEY"] == "this_token"

    def test_no_bzapi_token(self, db):
        with override_settings(BZAPI_TOKEN=""):
            api_url = settings.BZAPI_BASE_URL + "/bug"
            with requests_mock.Mocker() as req_mock:
                req_mock.get(api_url, json=SAMPLE_BUGZILLA_RESULTS)

                out = io.StringIO()
                call_command("bugassociations", stdout=out)

                first_item = req_mock.request_history[0]
                assert "X-BUGZILLA-API-KEY" not in first_item.headers

    def test_run_job_with_reports_with_existing_bugs_different(self, db):
        """Verify that an association to a signature that no longer is part
        of the crash signatures list gets removed.
        """
        api_url = settings.BZAPI_BASE_URL + "/bug"
        self.insert_data(bug_id="8", signature="@different")
        with requests_mock.Mocker() as req_mock:
            req_mock.get(api_url, json=SAMPLE_BUGZILLA_RESULTS)

            out = io.StringIO()
            call_command("bugassociations", stdout=out)

        # The previous association, to signature '@different' that is not in
        # crash signatures, is now missing
        associations = self.fetch_data()
        assert "@different" not in [item["signature"] for item in associations]

    def test_run_job_with_reports_with_existing_bugs_same(self, db):
        api_url = settings.BZAPI_BASE_URL + "/bug"
        self.insert_data(bug_id="8", signature="legitimate(sig)")
        with requests_mock.Mocker() as req_mock:
            req_mock.get(api_url, json=SAMPLE_BUGZILLA_RESULTS)

            out = io.StringIO()
            call_command("bugassociations", stdout=out)

        associations = self.fetch_data()
        associations = [
            item["signature"] for item in associations if item["bug_id"] == 8
        ]

        # New signatures have correctly been inserted
        assert len(associations) == 2
        assert associations == ["another::legitimate(sig)", "legitimate(sig)"]


@pytest.mark.parametrize(
    "content, expected",
    [
        # Simple signature
        ("[@ moz::signature]", {"moz::signature"}),
        # Using unicode.
        ("[@ moz::signature]", {"moz::signature"}),
        # 2 signatures and some junk
        (
            "@@3*&^!~[@ moz::signature][@   ns::old     ]",
            {"moz::signature", "ns::old"},
        ),
        # A signature containing square brackets.
        (
            "[@ moz::signature] [@ sig_with[brackets]]",
            {"moz::signature", "sig_with[brackets]"},
        ),
        # A malformed signature.
        ("[@ note there is no trailing bracket", set()),
    ],
)
def test_find_signatures(content, expected):
    assert find_signatures(content) == expected

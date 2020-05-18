# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import io
from unittest import mock

from django.core.management import call_command

from crashstats.crashstats.models import Signature


class FakeModel:
    def __init__(self):
        self._get_steps = []

    def add_get_step(self, response):
        self._get_steps.append({"response": response})

    def get(self, *args, **kwargs):
        if not self._get_steps:
            raise Exception("Unexpected call to .get()")

        step = self._get_steps.pop(0)
        return step["response"]


class TestUpdateSignaturesCommand:
    def fetch_crashstats_signature_data(self):
        return [
            {
                "signature": obj.signature,
                "first_build": str(obj.first_build),
                "first_date": str(obj.first_date),
            }
            for obj in Signature.objects.order_by(
                "signature", "first_build", "first_date"
            )
        ]

    @mock.patch(
        "crashstats.crashstats.management.commands.updatesignatures.SuperSearch"
    )
    def test_no_crashes_to_process(self, mock_supersearch, db):
        supersearch = FakeModel()
        mock_supersearch.return_value = supersearch

        # Mock SuperSearch to return no results
        supersearch.add_get_step({"errors": [], "hits": [], "total": 0, "facets": {}})

        out = io.StringIO()
        call_command("updatesignatures", stdout=out)

        # Assert that nothing got inserted
        assert self.fetch_crashstats_signature_data() == []

    @mock.patch(
        "crashstats.crashstats.management.commands.updatesignatures.SuperSearch"
    )
    def test_signature_insert_and_update(self, mock_supersearch, db):
        supersearch = FakeModel()
        mock_supersearch.return_value = supersearch

        # Verify there's nothing in the signatures table
        data = self.fetch_crashstats_signature_data()
        assert len(data) == 0

        # Mock SuperSearch to return 1 crash
        supersearch.add_get_step(
            {
                "errors": [],
                "hits": [
                    {
                        "build_id": "20180420000000",
                        "date": "2018-05-03T16:00:00.00000+00:00",
                        "signature": "OOM | large",
                    }
                ],
                "total": 1,
                "facets": {},
            }
        )

        out = io.StringIO()
        call_command("updatesignatures", stdout=out)

        # Signature was inserted
        data = self.fetch_crashstats_signature_data()
        assert data == [
            {
                "first_build": "20180420000000",
                "first_date": "2018-05-03 16:00:00+00:00",
                "signature": "OOM | large",
            }
        ]

        # Mock SuperSearch to return 1 crash with different data
        supersearch.add_get_step(
            {
                "errors": [],
                "hits": [
                    {
                        "build_id": "20180320000000",
                        "date": "2018-05-03T12:00:00.00000+00:00",
                        "signature": "OOM | large",
                    }
                ],
                "total": 1,
                "facets": {},
            }
        )

        # Run updatesignatures again
        out = io.StringIO()
        call_command("updatesignatures", stdout=out)

        # Signature was updated with correct data
        data = self.fetch_crashstats_signature_data()
        assert data == [
            {
                "first_build": "20180320000000",
                "first_date": "2018-05-03 12:00:00+00:00",
                "signature": "OOM | large",
            }
        ]

    @mock.patch(
        "crashstats.crashstats.management.commands.updatesignatures.SuperSearch"
    )
    def test_multiple_crash_processing(self, mock_supersearch, db):
        """Test processing multiple crashes with same signature."""
        supersearch = FakeModel()
        mock_supersearch.return_value = supersearch

        # Mock SuperSearch to return 4 crashes covering two signatures
        supersearch.add_get_step(
            {
                "errors": [],
                "hits": [
                    {
                        "build_id": "20180426000000",
                        # This is the earliest date of the three
                        "date": "2018-05-03T16:00:00.00000+00:00",
                        "signature": "OOM | large",
                    },
                    {
                        # This is the earliest build id of the three
                        "build_id": "20180322000000",
                        "date": "2018-05-03T18:00:00.00000+00:00",
                        "signature": "OOM | large",
                    },
                    {
                        "build_id": "20180427000000",
                        "date": "2018-05-03T19:00:00.000000+00:00",
                        "signature": "OOM | large",
                    },
                    {
                        "build_id": "20180322140748",
                        "date": "2018-05-03T18:22:34.969718+00:00",
                        "signature": "shutdownhang | js::DispatchTyped<T>",
                    },
                ],
                "total": 4,
                "facets": {},
            }
        )

        out = io.StringIO()
        call_command("updatesignatures", stdout=out)

        # Two signatures got inserted
        data = self.fetch_crashstats_signature_data()
        assert sorted(data, key=lambda item: item["first_build"]) == [
            {
                "first_build": "20180322000000",
                "first_date": "2018-05-03 16:00:00+00:00",
                "signature": "OOM | large",
            },
            {
                "first_build": "20180322140748",
                "first_date": "2018-05-03 18:22:34.969718+00:00",
                "signature": "shutdownhang | js::DispatchTyped<T>",
            },
        ]

    @mock.patch(
        "crashstats.crashstats.management.commands.updatesignatures.SuperSearch"
    )
    def test_crash_with_no_buildid(self, mock_supersearch, db):
        """Test crashes with no build id are ignored."""
        supersearch = FakeModel()
        mock_supersearch.return_value = supersearch

        # Mock SuperSearch to return 1 crash with no build id
        supersearch.add_get_step(
            {
                "errors": [],
                "hits": [
                    {
                        "build_id": "",
                        "date": "2018-05-03T16:00:00.00000+00:00",
                        "signature": "OOM | large",
                    }
                ],
                "total": 1,
                "facets": {},
            }
        )

        out = io.StringIO()
        call_command("updatesignatures", stdout=out)

        # The crash has no build id, so it gets ignored and nothing gets
        # inserted
        assert self.fetch_crashstats_signature_data() == []

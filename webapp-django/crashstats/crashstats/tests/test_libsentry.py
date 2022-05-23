# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This tests whether sentry is set up correctly in the webapp.

import time

import requests

from django.conf import settings
from django.test.testcases import LiveServerTestCase

from socorro.lib.libsentry import get_sentry_base_url


class TestIntegration(LiveServerTestCase):
    """Verify that sanitization code works with sentry-sdk."""

    def test_integration(self):
        fakesentry_api = get_sentry_base_url(settings.SENTRY_DSN)

        # Flush errors so the list is empty
        resp = requests.post(fakesentry_api + "api/flush/")
        assert resp.status_code == 200

        resp = requests.get(fakesentry_api + "api/errorlist/")
        assert len(resp.json()["errors"]) == 0

        # Call /__broken__ which returns an HTTP 500 and sends an error to Sentry;
        # the url should include a query string and a cookie
        resp = requests.get(
            self.live_server_url + "/__broken__",
            params={"state": "badvalue"},
            cookies={"sessionid": "abcde"},
        )
        assert resp.status_code == 500

        # Pause allowing sentry-sdk to send the error to fakesentry
        time.sleep(1)

        resp = requests.get(fakesentry_api + "api/errorlist/")
        assert len(resp.json()["errors"]) == 1
        error_id = resp.json()["errors"][0]

        # This verifies that sanitization code ran by checking to make sure the
        # querystring was filtered
        resp = requests.get(f"{fakesentry_api}api/error/{error_id}")
        payload = resp.json()["payload"]

        # Verify query string and cookie header are scrubbed; the cookie header can
        # contain session ids and the query_string can contain "code" and "state" which
        # are used in OIDC authentication
        assert payload["request"]["headers"]["Cookie"] == "[Scrubbed]"
        assert payload["request"]["query_string"] == "state=%5BScrubbed%5D"

        # We want to assert that "request" is always scrubbed. There should be at least
        # one instance of this, but not every frame has it and updates to Django and
        # middleware could change where it is. So we do this thing to assert ther's at
        # least one.
        stack_frames = payload["exception"]["values"][0]["stacktrace"]["frames"]
        has_request = False
        for i, frame in enumerate(stack_frames):
            if "request" in frame["vars"]:
                assert frame["vars"]["request"] == "[Scrubbed]"
                has_request = True

        assert has_request is True

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.urls import reverse
from django.utils.encoding import smart_str

from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.status.models import StatusMessage


class TestViews(BaseTestViews):
    def test_no_messages(self):
        # Use any URL that has a view that uses the base template that
        # shows status messages
        url = reverse("crashstats:home")

        response = self.client.get(url)
        assert response.status_code == 200
        assert "#status-message" not in smart_str(response.content)

    def test_status_message(self):
        url = reverse("crashstats:home")

        status = StatusMessage.objects.create(
            message="an incident is ongoing", severity="critical"
        )

        response = self.client.get(url)
        assert response.status_code == 200
        assert 'class="status-message' in smart_str(response.content)
        assert "severity-critical" in smart_str(response.content)
        assert status.message in smart_str(response.content)

        # Now disable that status and verify it doesn't show anymore.
        status.enabled = False
        status.save()

        response = self.client.get(url)
        assert response.status_code == 200
        assert status.message not in smart_str(response.content)

    def test_bug_ids(self):
        url = reverse("crashstats:home")

        StatusMessage.objects.create(
            message="an incident is ongoing; bug #500 has more info",
            severity="critical",
        )

        response = self.client.get(url)
        assert response.status_code == 200
        print(smart_str(response.content))
        bug_html = (
            '<a href="https://bugzilla.mozilla.org/show_bug.cgi?id=500">bug #500</a>'
        )
        assert bug_html in smart_str(response.content)

    def test_html_is_escaped(self):
        url = reverse("crashstats:home")

        StatusMessage.objects.create(
            message="<script>bad stuff&</script>", severity="critical"
        )

        response = self.client.get(url)
        assert response.status_code == 200
        escaped_text = "&lt;script&gt;bad stuff&amp;&lt;/script&gt;"
        assert escaped_text in smart_str(response.content)

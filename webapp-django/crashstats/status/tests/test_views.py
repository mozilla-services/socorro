from django.core.urlresolvers import reverse

from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.status.models import StatusMessage


class TestViews(BaseTestViews):

    def test_status_message(self):
        # Use any URL really.
        url = reverse('documentation:supersearch_home')

        response = self.client.get(url)
        assert response.status_code == 200
        assert '#status-message' not in response.content

        status = StatusMessage.objects.create(
            message='an incident is ongoing',
            severity='critical',
        )

        response = self.client.get(url)
        assert response.status_code == 200
        assert 'class="status-message' in response.content
        assert 'severity-critical' in response.content
        assert status.message in response.content

        # Now disable that status and verify it doesn't show anymore.
        status.enabled = False
        status.save()

        response = self.client.get(url)
        assert response.status_code == 200
        assert status.message not in response.content

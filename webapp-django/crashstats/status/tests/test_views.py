from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.status.models import StatusMessage


class TestViews(BaseTestViews):

    def test_status_message(self):
        # Use any URL really.
        url = reverse('documentation:supersearch_home')

        response = self.client.get(url)
        assert response.status_code == 200
        assert '#status-message' not in smart_text(response.content)

        status = StatusMessage.objects.create(
            message='an incident is ongoing',
            severity='critical',
        )

        response = self.client.get(url)
        assert response.status_code == 200
        assert 'class="status-message' in smart_text(response.content)
        assert 'severity-critical' in smart_text(response.content)
        assert status.message in smart_text(response.content)

        # Now disable that status and verify it doesn't show anymore.
        status.enabled = False
        status.save()

        response = self.client.get(url)
        assert response.status_code == 200
        assert status.message not in smart_text(response.content)

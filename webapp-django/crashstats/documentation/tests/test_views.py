from django.urls import reverse
from django.utils.encoding import smart_text

from crashstats.crashstats.tests.test_views import BaseTestViews


class TestViews(BaseTestViews):
    def test_supersearch_home(self):
        url = reverse('documentation:supersearch_home')
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'What is Super Search?' in smart_text(response.content)

    def test_supersearch_examples(self):
        url = reverse('documentation:supersearch_examples')
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'Examples' in smart_text(response.content)

    def test_supersearch_api(self):
        url = reverse('documentation:supersearch_api')
        response = self.client.get(url)
        assert response.status_code == 200
        assert '_results_number' in smart_text(response.content)
        assert '_aggs.*' in smart_text(response.content)
        assert 'signature' in smart_text(response.content)

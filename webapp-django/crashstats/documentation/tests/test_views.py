from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from crashstats.crashstats.tests.test_views import BaseTestViews


class TestViews(BaseTestViews):

    def test_supersearch_home(self):
        url = reverse('documentation:supersearch_home')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('What is Super Search?' in response.content)

    def test_supersearch_examples(self):
        url = reverse('documentation:supersearch_examples')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Examples' in response.content)

    def test_supersearch_api(self):
        url = reverse('documentation:supersearch_api')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('_results_number' in response.content)
        ok_('_aggs.*' in response.content)
        ok_('signature' in response.content)

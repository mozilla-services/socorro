from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from crashstats.crashstats.tests.test_views import BaseTestViews


class TestViews(BaseTestViews):

    def test_home(self):
        url = reverse('home:home', args=('WaterWolf',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('WaterWolf Crash Data' in response.content)
        ok_('WaterWolf 19.0' in response.content)

        # Test with a different duration.
        response = self.client.get(url, {'days': 14})
        eq_(response.status_code, 200)
        ok_('data-duration="14"' in response.content)

        # Test with a different version.
        response = self.client.get(url, {'version': '4.0.1'})
        eq_(response.status_code, 200)
        ok_('WaterWolf 4.0.1' in response.content)
        ok_('WaterWolf 19.0' not in response.content)

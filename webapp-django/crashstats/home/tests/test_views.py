from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.conf import settings

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

    def test_homepage_redirect(self):
        response = self.client.get('/')
        eq_(response.status_code, 302)
        destination = reverse('home:home', args=[settings.DEFAULT_PRODUCT])
        ok_(destination in response['Location'])

    def test_homepage_products_redirect_without_versions(self):
        url = '/home/products/WaterWolf'
        # some legacy URLs have this
        url += '/versions/'

        redirect_code = settings.PERMANENT_LEGACY_REDIRECTS and 301 or 302
        destination = reverse('home:home', args=['WaterWolf'])

        response = self.client.get(url)
        eq_(response.status_code, redirect_code)
        intermediate_dest = response['Location']

        response = self.client.get(intermediate_dest)
        eq_(response.status_code, redirect_code)
        ok_(destination in response['Location'], response['Location'])

    def test_home_400(self):
        url = reverse('home:home', args=('WaterWolf',))
        response = self.client.get(url, {'days': 'xxx'})
        eq_(response.status_code, 400)
        ok_('Enter a whole number' in response.content)
        eq_(response['Content-Type'], 'text/html; charset=utf-8')

from django.core.urlresolvers import reverse
from django.conf import settings

from crashstats.crashstats.tests.test_views import BaseTestViews


class TestViews(BaseTestViews):

    def test_home(self):
        url = reverse('home:home', args=('WaterWolf',))
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'WaterWolf Crash Data' in response.content
        assert 'WaterWolf 19.0' in response.content

        # Test with a different duration.
        response = self.client.get(url, {'days': 14})
        assert response.status_code == 200
        assert 'data-duration="14"' in response.content

        # Test with a different version.
        response = self.client.get(url, {'version': '4.0.1'})
        assert response.status_code == 200
        assert 'WaterWolf 4.0.1' in response.content
        assert 'WaterWolf 19.0' not in response.content

    def test_home_product_without_featured_versions(self):
        url = reverse('home:home', args=('SeaMonkey',))
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'SeaMonkey Crash Data' in response.content
        assert 'SeaMonkey 10.5' in response.content
        assert 'SeaMonkey 9.5' in response.content

        # Test with a different version.
        response = self.client.get(url, {'version': '10.5'})
        assert response.status_code == 200
        assert 'SeaMonkey 10.5' in response.content
        assert 'SeaMonkey 9.5' not in response.content

    def test_homepage_redirect(self):
        response = self.client.get('/')
        assert response.status_code == 302
        destination = reverse('home:home', args=[settings.DEFAULT_PRODUCT])
        assert destination in response['Location']

    def test_homepage_products_redirect_without_versions(self):
        url = '/home/products/WaterWolf'
        # some legacy URLs have this
        url += '/versions/'

        redirect_code = settings.PERMANENT_LEGACY_REDIRECTS and 301 or 302
        destination = reverse('home:home', args=['WaterWolf'])

        response = self.client.get(url)
        assert response.status_code == redirect_code
        intermediate_dest = response['Location']

        response = self.client.get(intermediate_dest)
        assert response.status_code == redirect_code
        assert destination in response['Location'] == response['Location']

    def test_home_400(self):
        url = reverse('home:home', args=('WaterWolf',))
        response = self.client.get(url, {'days': 'xxx'})
        assert response.status_code == 400
        assert 'Enter a whole number' in response.content
        assert response['Content-Type'] == 'text/html; charset=utf-8'

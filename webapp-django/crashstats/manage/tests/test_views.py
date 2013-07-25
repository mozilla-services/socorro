import json
import datetime
import re
import urlparse

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings

import mock
from nose.tools import eq_, ok_

from crashstats.crashstats.tests.test_views import (
    BaseTestViews,
    Response
)


class TestViews(BaseTestViews):

    @mock.patch('requests.get')
    def setUp(self, rget):
        super(TestViews, self).setUp()
        # we do this here so that the current/versions thing
        # is cached since that's going to be called later
        # in every view more or less
        def mocked_get(url, **options):
            if 'products/versions' in url:
                return Response("""
                {
                  "hits": [
                    {
                        "is_featured": true,
                        "throttle": 1.0,
                        "end_date": "string",
                        "start_date": "integer",
                        "build_type": "string",
                        "product": "WaterWolf",
                        "version": "19.0",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        from crashstats.crashstats.models import CurrentProducts, CurrentVersions

        versions = '+'.join([
            '%s:%s' % (ver['product'], ver['version'])
            for ver in CurrentVersions().get()
            if ver['product'] == settings.DEFAULT_PRODUCT
        ])
        api = CurrentProducts()
        # because WaterWolf is the default product and because BaseTestViews.setUp
        # calls CurrentVersions already, we need to prepare this call so that
        # each call to the home page can use the cache
        api.get(versions=versions)

    def _login(self):
        User.objects.create_user('kairo', 'kai@ro.com', 'secret')
        assert self.client.login(username='kairo', password='secret')

    def test_home_page_not_signed_in(self):
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        assert response.status_code == 302
        # because the home also redirects to the first product page
        # we can't use assertRedirects
        eq_(urlparse.urlparse(response['location']).path, '/')
        # now, going to the home page (will redirect) it will show a warning
        # message about the fact that you're not logged in
        response = self.client.get('/', follow=True)
        ok_('You are not logged in' in response.content)

    def test_home_page_signed_in(self):
        self._login()
        # at the moment it just redirects
        home_url = reverse('manage:home')
        response = self.client.get(home_url)
        eq_(response.status_code, 200)

        # certain links on that page
        featured_versions_url = reverse('manage:featured_versions')
        ok_(featured_versions_url in response.content)
        fields_url = reverse('manage:fields')
        ok_(fields_url in response.content)

    @mock.patch('requests.put')
    @mock.patch('requests.get')
    def test_featured_versions(self, rget, rput):
        self._login()
        url = reverse('manage:featured_versions')

        put_calls = []  # some mutable

        def mocked_put(url, **options):
            assert '/releases/featured/' in url
            data = options['data']
            put_calls.append(data)
            return Response("true")

        rput.side_effect = mocked_put

        def mocked_get(url, **options):
            if 'products' in url:
                today = datetime.date.today()
                tomorrow = today + datetime.timedelta(days=1)
                yesterday = today - datetime.timedelta(days=1)
                dates = {
                    'start_date_19': today,
                    'end_date_19': tomorrow,
                    'start_date_18': today,
                    'end_date_18': today,
                    'start_date_17': tomorrow,
                    'end_date_17': tomorrow + datetime.timedelta(days=1),
                    'start_date_16': yesterday - datetime.timedelta(days=1),
                    'end_date_16': yesterday,
                }
                return Response("""
                    {
                        "products": [
                            "WaterWolf"
                        ],
                        "hits": {
                            "WaterWolf": [{
                            "featured": true,
                            "throttle": 90.0,
                            "end_date": "%(end_date_19)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "19.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_19)s"
                            },
                            {
                            "featured": false,
                            "throttle": 33.333,
                            "end_date": "%(end_date_18)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "18.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_18)s"
                            },
                            {
                            "featured": true,
                            "throttle": 20.0,
                            "end_date": "%(end_date_17)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "17.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_17)s"
                            },
                            {
                            "featured": false,
                            "throttle": 20.0,
                            "end_date": "%(end_date_16)s",
                            "product": "WaterWolf",
                            "release": "Nightly",
                            "version": "16.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_16)s"
                            }
                            ]
                        },
                        "total": 2
                    }
                """ % dates)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('19.0.1' in response.content)
        ok_('18.0.1' in response.content)
        # because its start_date is in the future
        ok_('17.0.1' not in response.content)
        # because its end_date is in the past
        ok_('17.0.1' not in response.content)

        # also, note how the percentages are written out
        # (know thy fixtures)
        ok_('90%' in response.content)
        ok_('33.3%' in response.content)

        input_regex = re.compile('<input .*?>', re.M | re.DOTALL)
        checkboxes = [
            x for x in
            input_regex.findall(response.content)
            if 'type="checkbox"' in x
        ]
        eq_(len(checkboxes), 2)
        checkboxes_by_value = dict(
            (re.findall('value="(.*)"', x)[0], x)
            for x in checkboxes
        )
        ok_('checked' in checkboxes_by_value['19.0.1'])
        ok_('checked' not in checkboxes_by_value['18.0.1'])

        # post in a change
        update_url = reverse('manage:update_featured_versions')
        response = self.client.post(update_url, {
            'WaterWolf': '18.0.1'
        })
        eq_(response.status_code, 302)
        put_call = put_calls[0]
        eq_(put_call['WaterWolf'], '18.0.1')

    def test_fields(self):
        url = reverse('manage:fields')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_field_lookup(self, rget):
        url = reverse('manage:field_lookup')

        response = self.client.get(url)
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        # missing 'name' parameter
        eq_(response.status_code, 400)

        def mocked_get(url, **options):
            assert '/field/' in url
            ok_('name/Android_Display' in url)
            return Response("""
            {
                "name": "Android_Display",
                "product": null,
                "transforms": {
                    "1.X processed json": "",
                    "collector:raw json": "",
                    "data name": "Android_Display",
                    "database": "",
                    "mdsw pipe dump": "",
                    "pj transform": "",
                    "processed json 2012": "",
                    "processor transform": "",
                    "ted's mdsw json": ""
                }
            }
            """)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'name': 'Android_Display'})
        eq_(response.status_code, 200)

        data = json.loads(response.content)
        eq_(data['product'], None)
        eq_(len(data['transforms']), 9)

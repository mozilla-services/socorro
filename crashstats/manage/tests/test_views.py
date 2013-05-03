import datetime
import re
import urlparse

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

import mock
from nose.tools import eq_, ok_

from crashstats.crashstats.tests.test_views import (
    BaseTestViews,
    Response
)


class TestViews(BaseTestViews):

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
        # we don't want to use assertRedirects because it will render the
        # page we are redirected to
        assert response.status_code == 302
        eq_(
            urlparse.urlparse(response['location']).path,
            reverse('manage:featured_versions')
        )

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
                            "Firefox"
                        ],
                        "hits": {
                            "Firefox": [{
                            "featured": true,
                            "throttle": 90.0,
                            "end_date": "%(end_date_19)s",
                            "product": "Firefox",
                            "release": "Nightly",
                            "version": "19.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_19)s"
                            },
                            {
                            "featured": false,
                            "throttle": 33.333,
                            "end_date": "%(end_date_18)s",
                            "product": "Firefox",
                            "release": "Nightly",
                            "version": "18.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_18)s"
                            },
                            {
                            "featured": true,
                            "throttle": 20.0,
                            "end_date": "%(end_date_17)s",
                            "product": "Firefox",
                            "release": "Nightly",
                            "version": "17.0.1",
                            "has_builds": true,
                            "start_date": "%(start_date_17)s"
                            },
                            {
                            "featured": false,
                            "throttle": 20.0,
                            "end_date": "%(end_date_16)s",
                            "product": "Firefox",
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
            'Firefox': '18.0.1'
        })
        eq_(response.status_code, 302)
        put_call = put_calls[0]
        eq_(put_call['Firefox'], '18.0.1')

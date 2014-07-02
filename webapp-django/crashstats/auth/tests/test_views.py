import json
import re

from nose.tools import eq_, ok_

from django.conf import settings
from django.core.urlresolvers import reverse

from crashstats.base.tests.testbase import DjangoTestCase
from ..browserid_mock import mock_browserid


class TestViews(DjangoTestCase):

    def _login_attempt(self, email, assertion='fakeassertion123', next=None):
        if not next:
            next = self._home_url
        with mock_browserid(email):
            post_data = {
                'assertion': assertion,
                'next': next
            }
            return self.client.post(
                '/browserid/login/',
                post_data
            )

    @property
    def _home_url(self):
        return reverse('crashstats:home', args=(settings.DEFAULT_PRODUCT,))

    def test_invalid(self):
        """Bad BrowserID form (i.e. no assertion) -> failure."""
        response = self._login_attempt(None, None)
        eq_(response.status_code, 403)
        context = json.loads(response.content)
        eq_(context['redirect'], self._home_url)

    def test_bad_verification(self):
        """Bad verification -> failure."""
        response = self._login_attempt(None)
        eq_(response.status_code, 403)
        context = json.loads(response.content)
        eq_(context['redirect'], self._home_url)

    def test_successful_redirect(self):
        response = self._login_attempt(
            'peter@example.com',
        )
        eq_(response.status_code, 200)
        context = json.loads(response.content)
        eq_(context['redirect'], self._home_url)


class TestDebugLogin(DjangoTestCase):

    def test_render(self):
        url = reverse('auth:debug_login')
        _caches = {
            'default': {
                'BACKEND': 'path.to.SomeCache'
            }
        }
        with self.settings(
            SESSION_COOKIE_SECURE=True,
            CACHES=_caches,
            DEBUG=True,
            BROWSERID_AUDIENCES=['http://socorro']
        ):
            response = self.client.get(url)
            eq_(response.status_code, 200)
            ok_('data-session-cookie-secure="true"' in response.content)
            ok_('data-cache-setting="SomeCache"' in response.content)
            ok_('data-debug="true"' in response.content)
            ok_(
                'data-audiences="[&#34;http://socorro&#34;]"'
                in response.content
            )

    def test_get_cache_value(self):
        url = reverse('auth:debug_login')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # rendering it will set a data-cache-value
        regex = re.compile('data-cache-value="(\d+)"')
        cache_value = regex.findall(response.content)[0]
        response = self.client.get(url, {'test-caching': True})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(int(cache_value), structure['cache_value'])

    def test_get_cookie_value(self):
        url = reverse('auth:debug_login')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # rendering it will set a data-cache-value
        regex = re.compile('data-cookie-value="(\d+)"')
        cookie_value = regex.findall(response.content)[0]
        response = self.client.get(url, {'test-cookie': True})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(int(cookie_value), structure['cookie_value'])

from nose.tools import eq_, ok_
from django.conf import settings
from django.test import TestCase

from funfactory.urlresolvers import reverse

from ..browserid_mock import mock_browserid


class TestViews(TestCase):
    def _login_attempt(self, email, assertion='fakeassertion123'):
        with mock_browserid(email):
            r = self.client.post(reverse('auth:mozilla_browserid_verify'),
                                 {'assertion': assertion})
        return r

    @property
    def _home_url(self):
        return reverse('crashstats.home', args=(settings.DEFAULT_PRODUCT,))

    def test_invalid(self):
        """Bad BrowserID form (i.e. no assertion) -> failure."""
        response = self._login_attempt(None, None)
        eq_(response.status_code, 302)
        # not using assertRedirects because that makes it render the home URL
        # which means we need to mock the calls to the middleware
        ok_(self._home_url in response['Location'])

    def test_bad_verification(self):
        """Bad verification -> failure."""
        response = self._login_attempt(None)
        eq_(response.status_code, 302)
        ok_(self._home_url in response['Location'])

    def test_bad_email(self):
        response = self._login_attempt('tmickel@mit.edu')
        eq_(response.status_code, 302)
        ok_(self._home_url in response['Location'])

    def test_good_email(self):
        response = self._login_attempt(settings.ALLOWED_PERSONA_EMAILS[0])
        eq_(response.status_code, 302)
        ok_(self._home_url in response['Location'])

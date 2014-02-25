import json

from nose.tools import eq_, ok_

from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse

from ..browserid_mock import mock_browserid


class TestViews(TestCase):

    def shortDescription(self):
        # Stop nose using the test docstring and instead the test method name.
        pass

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
        return reverse('crashstats.home', args=(settings.DEFAULT_PRODUCT,))

    def test_invalid(self):
        """Bad BrowserID form (i.e. no assertion) -> failure."""
        response = self._login_attempt(None, None)
        eq_(response.status_code, 403)
        context = json.loads(response.content)
        ok_(context['redirect'].endswith('?bid_login_failed=1'))

    def test_bad_verification(self):
        """Bad verification -> failure."""
        response = self._login_attempt(None)
        eq_(response.status_code, 403)
        context = json.loads(response.content)
        ok_(context['redirect'].endswith('?bid_login_failed=1'))

    def test_successful_redirect(self):
        response = self._login_attempt(
            'peter@example.com',
        )
        eq_(response.status_code, 200)
        context = json.loads(response.content)
        eq_(context['redirect'], self._home_url)

import json

from nose.tools import eq_

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

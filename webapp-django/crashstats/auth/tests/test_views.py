import urlparse
import mock
from nose.tools import eq_, ok_

from django.conf import settings
from django.test import TestCase
from django.utils.importlib import import_module
from django.core.urlresolvers import reverse

from ..browserid_mock import mock_browserid


class TestViews(TestCase):

    def shortDescription(self):
        # Stop nose using the test docstring and instead the test method name.
        pass

    def get_messages(self):
        return self.client.session['_messages']

    def setUp(self):
        super(TestViews, self).setUp()

        self.ldap_patcher = mock.patch('ldap.initialize')
        self.initialize = self.ldap_patcher.start()
        self.connection = mock.MagicMock('connection')
        self.connection.set_option = mock.MagicMock()
        self.connection.simple_bind_s = mock.MagicMock()
        self.initialize.return_value = self.connection

        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()  # we need to make load() work, or the cookie is worthless
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

    def tearDown(self):
        super(TestViews, self).tearDown()
        self.ldap_patcher.stop()

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
        eq_(response.status_code, 302)
        # not using assertRedirects because that makes it render the home URL
        # which means we need to mock the calls to the middleware
        ok_(self._home_url in response['Location'])
        ok_(response['Location'].endswith('?bid_login_failed=1'))

    def test_bad_verification(self):
        """Bad verification -> failure."""
        response = self._login_attempt(None)
        eq_(response.status_code, 302)
        ok_(self._home_url in response['Location'])
        ok_(response['Location'].endswith('?bid_login_failed=1'))

    def test_bad_email(self):
        self.connection.search_s = mock.MagicMock(return_value=[])
        response = self._login_attempt('closebut@notcloseengouh.com')
        eq_(response.status_code, 302)
        ok_(self._home_url in response['Location'])
        ok_(response['Location'].endswith('?bid_login_failed=1'))

        message, = self.get_messages()
        eq_(
            message.message,
            "You logged in as closebut@notcloseengouh.com but you don't have "
            "sufficient privileges."
        )

    def test_good_email(self):
        result = {
            'abc123': {'uid': 'abc123', 'mail': 'peter@example.com'},
        }

        self.connection.search_s = mock.MagicMock(return_value=result.items())
        response = self._login_attempt('peter@example.com')
        eq_(response.status_code, 302)
        eq_(urlparse.urlparse(response['Location']).path, self._home_url)
        ok_(not response['Location'].endswith('?bid_login_failed=1'))

        message, = self.get_messages()
        eq_(message.message, 'You have successfully logged in.')

    def test_successful_redirect(self):
        result = {
            'abc123': {'uid': 'abc123', 'mail': 'peter@example.com'},
        }
        self.connection.search_s = mock.MagicMock(return_value=result.items())
        response = self._login_attempt(
            'peter@example.com',
            next='/something/?else=here'
        )
        eq_(response.status_code, 302)
        ok_(response['Location'].endswith('/something/?else=here'))

        message, = self.get_messages()
        eq_(message.message, 'You have successfully logged in.')

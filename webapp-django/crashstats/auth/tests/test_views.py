import mock
import urllib
from nose.tools import eq_, ok_

from django.conf import settings
from django.test import TestCase

from funfactory.urlresolvers import reverse

from ..browserid_mock import mock_browserid


class TestViews(TestCase):

    def setUp(self):
        super(TestViews, self).setUp()

        self.ldap_patcher = mock.patch('ldap.initialize')
        self.initialize = self.ldap_patcher.start()
        self.connection = mock.MagicMock('connection')
        self.connection.set_option = mock.MagicMock()
        self.connection.simple_bind_s = mock.MagicMock()
        self.initialize.return_value = self.connection

    def tearDown(self):
        super(TestViews, self).tearDown()
        self.ldap_patcher.stop()

    def _login_attempt(self, email, assertion='fakeassertion123', goto=None):
        with mock_browserid(email):
            post_data = {'assertion': assertion}
            if goto:
                post_data['goto'] = urllib.quote(goto)
            r = self.client.post(
                reverse('auth:mozilla_browserid_verify'),
                post_data
            )
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
        def search_s(base, scope, filterstr, *args, **kwargs):
            return []
        self.connection.search_s = mock.MagicMock(side_effect=search_s)

        response = self._login_attempt('closebut@notcloseengouh.com')
        eq_(response.status_code, 302)
        ok_(self._home_url in response['Location'])

    def test_good_email(self):
        result = {
            'abc123': {'uid': 'abc123', 'mail': 'peter@example.com'},
        }

        def search_s(base, scope, filterstr, *args, **kwargs):
            if 'ou=groups' in base:
                group_name = settings.LDAP_GROUP_NAMES[0]
                if ('peter@example.com' in filterstr and
                        'cn=%s' % group_name in filterstr):
                    return result.items()
            else:
                # basic lookup
                if 'peter@example.com' in filterstr:
                    return result.items()
            return []

        self.connection.search_s = mock.MagicMock(side_effect=search_s)
        response = self._login_attempt('peter@example.com')
        eq_(response.status_code, 302)
        ok_(self._home_url in response['Location'])

    def test_redirect(self):
        result = {
            'abc123': {'uid': 'abc123', 'mail': 'peter@example.com'},
        }

        def search_s(base, scope, filterstr, *args, **kwargs):
            if 'ou=groups' in base:
                group_name = settings.LDAP_GROUP_NAMES[0]
                if ('peter@example.com' in filterstr and
                        'cn=%s' % group_name in filterstr):
                    return result.items()
            else:
                # basic lookup
                if 'peter@example.com' in filterstr:
                    return result.items()
            return []

        self.connection.search_s = mock.MagicMock(side_effect=search_s)
        response = self._login_attempt('peter@example.com', goto='/query/')
        eq_(response.status_code, 302)
        ok_('/query/' in response['Location'])

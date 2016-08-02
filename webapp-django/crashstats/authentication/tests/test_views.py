import datetime
import json
import re

import mock
from nose.tools import eq_, ok_
from oauth2client import crypt

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats.tests.test_views import BaseTestViews
from ..browserid_mock import mock_browserid


User = get_user_model()


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
        return reverse('home:home', args=(settings.DEFAULT_PRODUCT,))

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


class TestOAuth2Views(BaseTestViews):

    def setUp(self):
        super(TestOAuth2Views, self).setUp()
        self.patcher = mock.patch('oauth2client.client.verify_id_token')
        self.patched_verify_id_token = self.patcher.start()

    def tearDown(self):
        super(TestOAuth2Views, self).tearDown()
        self.patcher.stop()

    def test_oauth2_signout(self):
        # Generally, the signout view is supposed to be POSTed to
        # from a piece of AJAX but you can still load it with GET.

        url = reverse('auth:oauth2_signout')
        response = self.client.post(url)
        # because you're not signed in
        eq_(response.status_code, 302)

        self._login()
        # just viewing the page
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url)
        eq_(response.status_code, 200)
        ok_(json.loads(response.content)['OK'])

        response = self.client.get(url)
        # because you're not signed in any more
        eq_(response.status_code, 302)

    def test_oauth2_signin(self):

        def mocked_verify_id_token(token, client_id):
            return {
                'aud': settings.OAUTH2_CLIENT_ID,
                'iss': settings.OAUTH2_VALID_ISSUERS[0],
                'email_verified': True,
                'email': 'test@example.com',
                'family_name': 'Addams',
            }

        self.patched_verify_id_token.side_effect = mocked_verify_id_token
        assert settings.OAUTH2_CLIENT_ID
        assert settings.OAUTH2_CLIENT_SECRET
        assert not self.client.session.keys()

        url = reverse('auth:oauth2_signin')
        response = self.client.post(url, {
            'token': '123456789'
        })
        eq_(response.status_code, 200)
        ok_(json.loads(response.content)['OK'])
        ok_(self.client.session.keys())

        # it should have created a user
        user = User.objects.get(email='test@example.com')
        eq_(user.first_name, '')
        eq_(user.last_name, 'Addams')
        ok_(user.last_login)
        ok_(user.date_joined)
        ok_(not user.has_usable_password())

    def test_oauth2_signin_existing_user(self):
        user = User.objects.create(
            username='anything',
            email='TEST@example.com',
            first_name='First',
            last_name='Last',
        )

        def mocked_verify_id_token(token, client_id):
            return {
                'aud': settings.OAUTH2_CLIENT_ID,
                'iss': settings.OAUTH2_VALID_ISSUERS[0],
                'email_verified': True,
                'email': 'test@example.com',
                'given_name': '',  # empty but not None!
                'family_name': 'Different',
            }

        self.patched_verify_id_token.side_effect = mocked_verify_id_token

        url = reverse('auth:oauth2_signin')
        response = self.client.post(url, {
            'token': '123456789'
        })
        eq_(response.status_code, 200)
        ok_(json.loads(response.content)['OK'])
        ok_(self.client.session.keys())

        # it should have created a user
        user = User.objects.get(id=user.id)
        eq_(user.first_name, '')
        eq_(user.last_name, 'Different')
        ok_(user.last_login)
        ok_(user.date_joined)
        ok_(not user.has_usable_password())

    def test_oauth2_signin_existing_inactive_user(self):
        user = User.objects.create(
            username='anything',
            email='TEST@example.com',
            first_name='First',
            last_name='Last',
        )
        user.is_active = False
        user.save()

        def mocked_verify_id_token(token, client_id):
            return {
                'aud': settings.OAUTH2_CLIENT_ID,
                'iss': settings.OAUTH2_VALID_ISSUERS[0],
                'email_verified': True,
                'email': 'test@example.com',
                'given_name': '',  # empty but not None!
                'family_name': 'Different',
            }

        self.patched_verify_id_token.side_effect = mocked_verify_id_token

        url = reverse('auth:oauth2_signin')
        response = self.client.post(url, {
            'token': '123456789'
        })
        eq_(response.status_code, 403)

    def test_oauth2_signin_email_not_verified(self):

        def mocked_verify_id_token(token, client_id):
            return {
                'aud': settings.OAUTH2_CLIENT_ID,
                'iss': settings.OAUTH2_VALID_ISSUERS[0],
                'email_verified': False,
                'email': 'test@example.com',
                'given_name': '',  # empty but not None!
                'family_name': 'Different',
            }

        self.patched_verify_id_token.side_effect = mocked_verify_id_token

        url = reverse('auth:oauth2_signin')
        response = self.client.post(url, {
            'token': '123456789'
        })
        eq_(response.status_code, 403)

    def test_oauth2_signin_bad_token(self):

        def mocked_verify_id_token(token, client_id):
            assert token == 'junk', token
            raise crypt.AppIdentityError('bad!')

        self.patched_verify_id_token.side_effect = mocked_verify_id_token

        url = reverse('auth:oauth2_signin')
        response = self.client.post(url, {
            'token': 'junk'
        })
        eq_(response.status_code, 403)

    def test_oauth2_signin_bad_verification_data(self):

        def mocked_verify_id_token(token, client_id):
            if token == 'bad client id':
                return {
                    'aud': 'other junk',
                    'iss': settings.OAUTH2_VALID_ISSUERS[0],
                }
            if token == 'bad issuer':
                return {
                    'aud': settings.OAUTH2_CLIENT_ID,
                    'iss': 'junk.malware.com',
                }
            raise NotImplementedError(token)

        self.patched_verify_id_token.side_effect = mocked_verify_id_token

        url = reverse('auth:oauth2_signin')
        response = self.client.post(url, {
            'token': 'bad client id'
        })
        eq_(response.status_code, 403)

        response = self.client.post(url, {
            'token': 'bad issuer'
        })
        eq_(response.status_code, 403)

    def test_signout_meta_tag(self):
        """If the user has been signed in too long, we expect there
        to be a meta tag in the DOM that is used by the JavaScript to
        force a sign-out."""
        # Doesn't really matter which URL we use, as long as it's one
        # that you can view whilst being anonymous.
        url = reverse('documentation:home')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        head = response.content.split('</head>')[0]
        ok_('<meta name="signin"' not in head)

        # let's be signed in
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        head = response.content.split('</head>')[0]
        # Still not there because the server does NOT think you need
        # to sign out.
        ok_('<meta name="signin"' not in head)

        # Reload because the fixture user doesn't have a last_login
        # when it's first returned.
        user = User.objects.get(id=user.id)
        user.last_login -= datetime.timedelta(
            seconds=settings.LAST_LOGIN_MAX
        )
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        head = response.content.split('</head>')[0]
        ok_('<meta name="signin" content="signout"' in head)

    def test_signout_meta_tag_inactive_user(self):
        """If you're signed in and view a private page (e.g. the
        Your Profile page), and you refresh, you have to be an active
        user to be able to continue to view it. This is not true for
        publicly available pages like the home page.
        But if you are signed in but your user account is, for some
        reason, not active the JavaScript code should force the user
        to sign out."""
        # A URL you can visit anonymously
        url = reverse('documentation:home')
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        head = response.content.split('</head>')[0]
        ok_('<meta name="signin" content="signout"' not in head)

        user = User.objects.get(id=user.id)
        user.is_active = False
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        head = response.content.split('</head>')[0]
        ok_('<meta name="signin" content="signout"' in head)


class TestDebugLogin(DjangoTestCase):

    def test_render(self):
        url = reverse('auth:debug_login')
        with self.settings(
            SESSION_COOKIE_SECURE=True,
            DEBUG=True,
            BROWSERID_AUDIENCES=[
                'http://socorro',
                'http://crashstats.com'
            ]
        ):
            response = self.client.get(url)
            eq_(response.status_code, 200)
            ok_('data-session-cookie-secure="true"' in response.content)
            ok_('data-debug="true"' in response.content)
            ok_(
                'data-audiences="http://socorro,http://crashstats.com"'
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

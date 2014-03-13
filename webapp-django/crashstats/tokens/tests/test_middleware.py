import datetime
import json

from nose.tools import eq_, ok_, assert_raises

from django.contrib.auth.models import User, Permission
from django.conf import settings
from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.contrib.contenttypes.models import ContentType

from crashstats.tokens import models
from crashstats.tokens.middleware import APIAuthenticationMiddleware


class TestMiddleware(TestCase):

    django_session_middleware = SessionMiddleware()
    django_auth_middleware = AuthenticationMiddleware()
    middleware = APIAuthenticationMiddleware()

    def test_impropertly_configured(self):
        request = RequestFactory().get('/')
        assert_raises(
            ImproperlyConfigured,
            self.middleware.process_request,
            request
        )

    def _get_request(self, **headers):
        # boilerplate stuff
        request = RequestFactory(**headers).get('/')
        self.django_session_middleware.process_request(request)
        self.django_auth_middleware.process_request(request)
        assert request.user
        return request

    def test_no_token_key(self):
        request = self._get_request()
        eq_(self.middleware.process_request(request), None)

    def test_non_existant_token_key(self):
        request = self._get_request(HTTP_AUTH_TOKEN='xxx')

        response = self.middleware.process_request(request)
        eq_(response.status_code, 403)
        # the response content will be JSON
        result = json.loads(response.content)
        eq_(result['error'], 'API Token not matched')

    def test_expired_token(self):
        user = User.objects.create(username='peterbe')
        token = models.Token.objects.create(
            user=user,
        )
        token.expires -= datetime.timedelta(
            days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS
        )
        token.save()
        request = self._get_request(HTTP_AUTH_TOKEN=token.key)

        response = self.middleware.process_request(request)
        eq_(response.status_code, 403)
        result = json.loads(response.content)
        eq_(result['error'], 'API Token found but expired')

    def test_token_valid(self):
        user = User.objects.create(username='peterbe')
        token = models.Token.objects.create(
            user=user,
        )
        request = self._get_request(HTTP_AUTH_TOKEN=token.key)

        response = self.middleware.process_request(request)
        eq_(response, None)
        eq_(request.user, user)

    def test_token_permissions(self):
        user = User.objects.create(username='peterbe')
        token = models.Token.objects.create(
            user=user,
        )
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label='crashstats',
        )
        permission = Permission.objects.create(
            codename='play',
            content_type=ct
        )
        token.permissions.add(permission)
        Permission.objects.create(
            codename='fire',
            content_type=ct
        )
        # deliberately not adding this second permission

        request = self._get_request(HTTP_AUTH_TOKEN=token.key)
        # do the magic to the request
        self.middleware.process_request(request)
        eq_(request.user, user)
        ok_(request.user.has_perm('crashstats.play'))
        ok_(not request.user.has_perm('crashstats.fire'))

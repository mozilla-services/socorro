# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import json

import pytest

from django import http
from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.test.client import RequestFactory

from crashstats.crashstats.tests.testbase import DjangoTestCase
from crashstats.tokens import models
from crashstats.tokens.middleware import APIAuthenticationMiddleware


def get_response(req):
    return http.HttpResponse("hello")


class TestMiddleware(DjangoTestCase):

    django_session_middleware = SessionMiddleware(get_response)
    django_auth_middleware = AuthenticationMiddleware(get_response)
    middleware = APIAuthenticationMiddleware(get_response)

    def test_impropertly_configured(self):
        request = RequestFactory().get("/")
        with pytest.raises(ImproperlyConfigured):
            self.middleware.process_request(request)

    def _get_request(self, **headers):
        # boilerplate stuff
        request = RequestFactory(**headers).get("/")
        self.django_session_middleware.process_request(request)
        self.django_auth_middleware.process_request(request)
        assert request.user
        return request

    def test_no_token_key(self):
        request = self._get_request()
        assert self.middleware.process_request(request) is None

    def test_non_existant_token_key(self):
        request = self._get_request(HTTP_AUTH_TOKEN="xxx")

        response = self.middleware.process_request(request)
        assert response.status_code == 403
        # the response content will be JSON
        result = json.loads(response.content)
        assert result["error"] == "API Token not matched"

    def test_expired_token(self):
        user = User.objects.create(username="peterbe")
        token = models.Token.objects.create(user=user)
        token.expires -= datetime.timedelta(
            days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS
        )
        token.save()
        request = self._get_request(HTTP_AUTH_TOKEN=token.key)

        response = self.middleware.process_request(request)
        assert response.status_code == 403
        result = json.loads(response.content)
        assert result["error"] == "API Token found but expired"

    def test_token_valid(self):
        user = User.objects.create(username="peterbe")
        token = models.Token.objects.create(user=user)
        request = self._get_request(HTTP_AUTH_TOKEN=token.key)

        response = self.middleware.process_request(request)
        assert response is None
        assert request.user == user

    def test_token_permissions(self):
        user = User.objects.create(username="peterbe")
        token = models.Token.objects.create(user=user)
        ct, __ = ContentType.objects.get_or_create(model="", app_label="crashstats")
        permission = Permission.objects.create(codename="play", content_type=ct)
        token.permissions.add(permission)
        Permission.objects.create(codename="fire", content_type=ct)
        # deliberately not adding this second permission

        request = self._get_request(HTTP_AUTH_TOKEN=token.key)
        # do the magic to the request
        self.middleware.process_request(request)
        assert request.user == user
        assert request.user.has_perm("crashstats.play")
        assert not request.user.has_perm("crashstats.fire")

    def test_token_on_inactive_user(self):
        user = User.objects.create(username="peterbe")
        user.is_active = False
        user.save()
        token = models.Token.objects.create(user=user)
        request = self._get_request(HTTP_AUTH_TOKEN=token.key)

        response = self.middleware.process_request(request)
        assert response.status_code == 403
        result = json.loads(response.content)
        assert result["error"] == "User of API token not active"

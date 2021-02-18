# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from functools import partial

from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django import http

from crashstats.tokens import models


def json_forbidden_response(msg):
    body = json.dumps({"error": msg})
    return http.HttpResponseForbidden(
        body + "\n", content_type="application/json; charset=UTF-8"
    )


def has_perm(all, codename, obj=None):
    codename = codename.split(".", 1)[1]
    return all.filter(codename=codename).count()


class APIAuthenticationMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_request(request)
        if not response:
            response = self.get_response(request)
        self.delete_unused_sessions(request, response)
        return response

    def delete_unused_sessions(self, request, response):
        """Delete unused sessions

        The Auth-Token login creates a Django session. If the view doesn't save
        anything to the session, we clear it because this is an API and we don't
        need to maintain empty sessions between requests.

        """
        session_keys = [
            key for key in request.session.keys() if not key.startswith("_auth_user")
        ]
        if not session_keys:
            request.session.clear()
            request.session.flush()
            # Delete the anoncsrf token so that doesn't set a cookie; this is
            # set by django-session-csrf
            if hasattr(request, "_anon_csrf_key"):
                delattr(request, "_anon_csrf_key")

    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "The API Authenication middleware requires the "
                "authentication middleware to be installed. Edit your "
                "MIDDLEWARE setting to insert "
                "'django.contrib.auth.middleware.AuthenticationMiddleware' "
                "before the RemoteUserMiddleware class."
            )

        key = request.META.get("HTTP_AUTH_TOKEN")
        if not key:
            return

        try:
            token = models.Token.objects.select_related("user").get(key=key)
            if token.is_expired:
                return json_forbidden_response("API Token found but expired")
        except models.Token.DoesNotExist:
            return json_forbidden_response("API Token not matched")

        user = token.user

        if not user.is_active:
            return json_forbidden_response("User of API token not active")

        # it actually doesn't matter so much which backend
        # we use as long as it's something
        user.backend = "django.contrib.auth.backends.ModelBackend"
        user.has_perm = partial(has_perm, token.permissions.all())
        # User is valid. Set request.user and persist user in the session
        # by logging the user in.
        request.user = user
        auth.login(request, user)

        # For an API request, we don't want mere logging in to trigger saving of a
        # session.
        request.session.modified = False

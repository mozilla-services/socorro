import json
from functools import partial

from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django import http

from . import models


def json_forbidden_response(msg):
    body = json.dumps({'error': msg})
    return http.HttpResponseForbidden(
        body + '\n',
        mimetype='application/json; charset=UTF-8'
    )


def has_perm(all, codename):
    codename = codename.split('.', 1)[1]
    return all.filter(codename=codename).count()


class APIAuthenticationMiddleware(object):

    def process_request(self, request):
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The API Authenication middleware requires the"
                " authentication middleware to be installed. Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class.")

        key = request.META.get('HTTP_AUTH_TOKEN')
        if not key:
            return
        try:
            token = models.Token.objects.select_related('user').get(key=key)
            if token.is_expired:
                return json_forbidden_response(
                    'API Token found but expired'
                )
        except models.Token.DoesNotExist:
            return json_forbidden_response('API Token not matched')

        user = token.user
        # it actually doesn't matter so much which backend
        # we use as long as it's something
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        user.has_perm = partial(has_perm, token.permissions.all())
        # User is valid. Set request.user and persist user in the session
        # by logging the user in.
        request.user = user
        auth.login(request, user)

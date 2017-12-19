import base64
import datetime
import hashlib
import random

from django import http
from django.contrib.auth import get_user_model
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.contrib import auth
from django.utils.encoding import smart_bytes

from oauth2client import client, crypt

from crashstats.crashstats.utils import json_view


User = get_user_model()


def default_username(email):
    # Store the username as a base64 encoded sha1 of the email address
    # this protects against data leakage because usernames are often
    # treated as public identifiers (so we can't use the email address).
    return base64.urlsafe_b64encode(
        hashlib.sha1(smart_bytes(email)).digest()
    ).rstrip(b'=')


@json_view
def debug_login(request):
    if request.GET.get('test-caching'):
        return {'cache_value': cache.get('cache_value')}

    if request.GET.get('test-cookie'):
        return {'cookie_value': int(request.COOKIES.get('cookie_value', 0))}

    cache_value = random.randint(10, 100)
    cache.set('cache_value', cache_value, 10)
    cookie_value = random.randint(10, 100)
    context = {
        'SESSION_COOKIE_SECURE': settings.SESSION_COOKIE_SECURE,
        'cache_setting': settings.CACHES['default']['BACKEND'].split('.')[-1],
        'cache_value': cache_value,
        'cookie_value': cookie_value,
        'DEBUG': settings.DEBUG,
    }
    response = render(request, 'auth/debug_login.html', context)
    future = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
    response.set_cookie('cookie_value', cookie_value, expires=future)
    return response


@json_view
def oauth2_signout(request):
    """If people click the "Sign out" link, an AJAX post will trigger
    a post to this view. But if the user right-clicks to, for example,
    "Open Link in New Tab" they'll arrive here.

    If they arrive here, in any way, and are NOT signed in, redirect
    out.
    """
    if not request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        auth.logout(request)
        return {'OK': True}

    return render(request, 'auth/signout.html')


@require_POST
@json_view
def oauth2_signin(request):
    token = request.POST['token']
    try:
        idinfo = client.verify_id_token(
            token,
            settings.OAUTH2_CLIENT_ID
        )
    except crypt.AppIdentityError:
        return http.HttpResponseForbidden(
            'Invalid Identity token'
        )

    if idinfo['aud'] != settings.OAUTH2_CLIENT_ID:
        return http.HttpResponseForbidden(
            'Invalid Client ID ({})'.format(idinfo['aud'])
        )
    if idinfo['iss'] not in settings.OAUTH2_VALID_ISSUERS:
        return http.HttpResponseForbidden(
            'Invalid issuer ({})'.format(idinfo['iss'])
        )
    if not idinfo['email_verified']:
        return http.HttpResponseForbidden(
            'Email not verified'
        )
    # log in the user
    try:
        user = User.objects.get(email__iexact=idinfo['email'])
        if not user.is_active:
            return http.HttpResponseForbidden(
                'Inactivated user'
            )
        # We already had a user by that email address, but if the
        # first or last name is different, override what we already had.
        if (
            idinfo.get('given_name') is not None and
            user.first_name != idinfo['given_name']
        ):
            user.first_name = idinfo['given_name']
            user.save()
        if (
            idinfo.get('family_name') is not None and
            user.last_name != idinfo['family_name']
        ):
            user.last_name = idinfo['family_name']
            user.save()
    except User.DoesNotExist:
        user = User.objects.create(
            username=default_username(idinfo['email']),
            email=idinfo['email'],
            first_name=idinfo.get('given_name', ''),
            last_name=idinfo.get('family_name', ''),
        )
    user.backend = 'django.contrib.auth.backends.AllowAllUsersModelBackend'
    request.user = user
    auth.login(request, user)

    # Make a note that we used Google to sign in.
    # This is helpful for the sake of how we present the sign-out link.
    request.session['signin_method'] = 'google'

    return {'OK': True}

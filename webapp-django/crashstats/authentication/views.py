import datetime
import random

from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.core.cache import cache

from django_browserid.views import Verify

from crashstats.crashstats.utils import json_view


class CustomBrowserIDVerify(Verify):

    @property
    def failure_url(self):
        # if we don't do this, upon failure it might redirect
        # to `/?bid_login_failed=1` which will redirect to
        # `/home/products/:defaultproduct` without the `?bid_login_failed=1`
        # part which doesn't tell browserID that it went wrong
        return reverse('crashstats:home', args=(settings.DEFAULT_PRODUCT,))

    @property
    def success_url(self):
        return reverse('crashstats:home', args=(settings.DEFAULT_PRODUCT,))


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
        'BROWSERID_AUDIENCES': getattr(settings, 'BROWSERID_AUDIENCES', []),
    }
    response = render(request, 'auth/debug_login.html', context)
    future = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)
    response.set_cookie('cookie_value', cookie_value, expires=future)
    return response

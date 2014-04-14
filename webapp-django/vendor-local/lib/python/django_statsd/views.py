from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django_statsd.clients import statsd

boomerang = {
 'window.performance.navigation.redirectCount': 'nt_red_cnt',
 'window.performance.navigation.type': 'nt_nav_type',
 'window.performance.timing.connectEnd': 'nt_con_end',
 'window.performance.timing.connectStart': 'nt_con_st',
 'window.performance.timing.domComplete': 'nt_domcomp',
 'window.performance.timing.domContentLoaded': 'nt_domcontloaded',
 'window.performance.timing.domInteractive': 'nt_domint',
 'window.performance.timing.domLoading': 'nt_domloading',
 'window.performance.timing.domainLookupEnd': 'nt_dns_end',
 'window.performance.timing.domainLookupStart': 'nt_dns_st',
 'window.performance.timing.fetchStart': 'nt_fet_st',
 'window.performance.timing.loadEventEnd': 'nt_load_end',
 'window.performance.timing.loadEventStart': 'nt_load_st',
 'window.performance.timing.navigationStart': 'nt_nav_st',
 'window.performance.timing.redirectEnd': 'nt_red_end',
 'window.performance.timing.redirectStart': 'nt_red_st',
 'window.performance.timing.requestStart': 'nt_req_st',
 'window.performance.timing.responseEnd': 'nt_res_end',
 'window.performance.timing.responseStart': 'nt_res_st',
 'window.performance.timing.unloadEventEnd': 'nt_unload_end',
 'window.performance.timing.unloadEventStart': 'nt_unload_st'
}

types = {
 '0': 'navigate',
 '1': 'reload',
 '2': 'back_forward',
 '255': 'reserved'
}

# These are the default keys that we will try and record.
stick_keys = [
 'window.performance.timing.domComplete',
 'window.performance.timing.domInteractive',
 'window.performance.timing.domLoading',
 'window.performance.timing.loadEventEnd',
 'window.performance.timing.responseStart',
 'window.performance.navigation.redirectCount',
 'window.performance.navigation.type',
]


def process_key(start, key, value):
    if 'timing' in key:
        # Some values will be zero. We want the output of that to
        # be zero relative to start.
        value = max(start, int(value)) - start
        statsd.timing(key, value)
    elif key == 'window.performance.navigation.type':
        statsd.incr('%s.%s' % (key, types[value]))
    elif key == 'window.performance.navigation.redirectCount':
        statsd.incr(key, int(value))


def _process_summaries(start, keys):
    calculated = {
        'network': keys['window.performance.timing.responseStart'] - start,
        'app': keys['window.performance.timing.domLoading'] -
               keys['window.performance.timing.responseStart'],
        'dom': keys['window.performance.timing.domComplete'] -
               keys['window.performance.timing.domLoading'],
        'rendering': keys['window.performance.timing.loadEventEnd'] -
                     keys['window.performance.timing.domComplete'],
    }
    for k, v in calculated.items():
        # If loadEventEnd still does not get populated, we could end up with
        # negative numbers here.
        statsd.timing('window.performance.calculated.%s' % k, max(v, 0))


@require_http_methods(['GET', 'HEAD'])
def _process_boomerang(request):
    if 'nt_nav_st' not in request.GET:
        raise ValueError('nt_nav_st not in request.GET, make sure boomerang'
            ' is made with navigation API timings as per the following'
            ' http://yahoo.github.com/boomerang/doc/howtos/howto-9.html')

    # This when the request started, everything else will be relative to this
    # for the purposes of statsd measurement.
    start = int(request.GET['nt_nav_st'])

    keys = {}
    for k in getattr(settings, 'STATSD_RECORD_KEYS', stick_keys):
        v = request.GET.get(boomerang[k])
        if not v or v == 'undefined':
            continue
        if k in boomerang:
            process_key(start, k, v)
            keys[k] = v

    try:
        _process_summaries(start, keys)
    except KeyError:
        pass


@require_http_methods(['POST'])
def _process_stick(request):
    start = request.POST.get('window.performance.timing.navigationStart', None)
    if not start:
        return http.HttpResponseBadRequest()

    start = int(start)
    keys = {}
    for k in getattr(settings, 'STATSD_RECORD_KEYS', stick_keys):
        v = request.POST.get(k, None)
        if v:
            keys[k] = int(request.POST[k])
            process_key(start, k, request.POST[k])

    # Only process the network when we have these.
    for key in ['window.performance.timing.loadEventEnd',
                'window.performance.timing.responseStart']:
        if key not in keys:
            return

    _process_summaries(start, keys)


clients = {
 'boomerang': _process_boomerang,
 'stick': _process_stick,
}


@csrf_exempt
def record(request):
    """
    This is a Django method you can link to in your URLs that process
    the incoming data. Be sure to add a client parameter into your request
    so that we can figure out how to process this request. For example
    if you are using boomerang, you'll need: client = boomerang.

    You can define a method in STATSD_RECORD_GUARD that will do any lookup
    you need for imposing security on this method, so that not just anyone
    can post to it.
    """
    if 'client' not in request.REQUEST:
        return http.HttpResponseBadRequest()

    client = request.REQUEST['client']
    if client not in clients:
        return http.HttpResponseBadRequest()

    guard = getattr(settings, 'STATSD_RECORD_GUARD', None)
    if guard:
        if not callable(guard):
            raise ValueError('STATSD_RECORD_GUARD must be callable')
        result = guard(request)
        if result:
            return result

    try:
        response = clients[client](request)
    except (ValueError, KeyError):
        return http.HttpResponseBadRequest()

    if response:
        return response
    return http.HttpResponse('recorded')

"""Example views. Feel free to delete this app."""

import logging
import json
import datetime
import time
import os

from django import http
from django.shortcuts import render

import bleach
import commonware

from jingo import env, register
from funfactory.log import log_cef
from mobility.decorators import mobile_template
from session_csrf import anonymous_csrf

log = commonware.log.getLogger('playdoh')

@register.filter
def unixtime(value, millis=False, format='%Y-%m-%d'):
    log.debug(value)
    d = datetime.datetime.strptime(value, format)
    epoch_seconds = time.mktime(d.timetuple())
    if millis:
        return epoch_seconds * 1000 + d.microsecond/1000
    else:
        return epoch_seconds


def _basedata(request):
    data = {}
    data['product']  = request.path.split('/')[-1]
    with open('currentversions.json') as f:
        currentversions = json.loads(f.read())
        data['currentversions'] = currentversions['currentversions']
    return data

@mobile_template('crashstats/{mobile/}products.html')
def home(request, template=None):
    # e.g. curl -H "Host: socorro-mware-zlb.webapp.phx1.mozilla.com" -u dbrwaccess 'http://localhost/bpapi/adu/byday/p/Firefox/v/15.0a1;14.0a2;13.0b2;12.0/rt/any/os/Windows;Mac;Linux/start/2012-05-03/end/2012-05-10'
    data = _basedata(request)

    with open('adubyday.json') as f:
        data['adubyday'] = json.loads(f.read())

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topcrasher.html')
def topcrasher(request, template=None):
    # ${host}/crashes/signatures/product/${p}/version/${v}/crash_type/browser/to_date/${end_date}/duration/${dur}/limit/${limit}"
    # e.g. curl -u dbrwaccess "http://socorro-mware-zlb.webapp.phx1.mozilla.com/bpapi/crashes/signatures/product/Firefox/version/14.0a1/crash_type/browser/end_date/2012-05-10T11%3A00%3A00%2B0000/duration/168/limit/300/"
    data = _basedata(request)
    with open('tcbs.json') as f:
        data['tcbs'] = json.loads(f.read())

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}daily.html')
def daily(request, template=None):

    data = _basedata(request)
    return render(request, template, data)

@mobile_template('crashstats/{mobile/}builds.html')
def builds(request, template=None):

    data = _basedata(request)
    return render(request, template, data)

@mobile_template('crashstats/{mobile/}hangreport.html')
def hangreport(request, template=None):

    data = _basedata(request)
    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topchangers.html')
def topchangers(request, template=None):

    data = _basedata(request)
    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportlist.html')
def reportlist(request, template=None):

    data = _basedata(request)
    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportindex.html')
def reportindex(request, template=None):

    data = _basedata(request)
    return render(request, template, data)

@mobile_template('crashstats/{mobile/}query.html')
def query(request, template=None):
    # e.g. curl -H "Host: socorro-mware-zlb.webapp.phx1.mozilla.com" -u dbrwaccess 'http://localhost/bpapi/search/signatures/products/Firefox/in/signature/search_mode/contains/to/2012-04-22%2011%3A09%3A37/from/2012-04-15%2011%3A09%3A37/report_type/any/report_process/any/result_number/100/'

    data = _basedata(request)
    with open('query.json') as f:
        data['query'] = json.loads(f.read())
    log.debug(data['query'])
    return render(request, template, data)


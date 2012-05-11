"""Example views. Feel free to delete this app."""

import logging
import json
import datetime
import time
import os

from django import http
from django.shortcuts import render

from models import SocorroMiddleware

import bleach
import commonware

from jingo import env, register
from funfactory.log import log_cef
from mobility.decorators import mobile_template
from session_csrf import anonymous_csrf

log = commonware.log.getLogger('playdoh')

@register.filter
def unixtime(value, millis=False, format='%Y-%m-%d'):
    d = datetime.datetime.strptime(value, format)
    epoch_seconds = time.mktime(d.timetuple())
    if millis:
        return epoch_seconds * 1000 + d.microsecond/1000
    else:
        return epoch_seconds

@mobile_template('crashstats/{mobile/}products.html')
def home(request, product, template=None):
    data = {}
    data['product']  = product
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['adubyday'] = mware.adu_by_day()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topcrasher.html')
def topcrasher(request, template=None):
    data = {}
    data['product'] = request.path.split('/')[-2]

    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['tcbs'] = mware.tcbs()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}daily.html')
def daily(request, template=None):
    data = {}
    data['product']  = request.path.split('/')[-1]

    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['adubyday'] = mware.adu_by_day()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}builds.html')
def builds(request, product, template=None):
    data = {}
    data['product']  = product
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}hangreport.html')
def hangreport(request, product, template=None):
    data = {}
    data['product']  = product
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topchangers.html')
def topchangers(request, template=None):
    data = {}
    data['product']  = request.path.split('/')[-1]

    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportlist.html')
def reportlist(request, template=None):
    data = {}
    data['product']  = request.path.split('/')[-1]

    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportindex.html')
def reportindex(request, template=None):
    data = {}
    data['product']  = request.path.split('/')[-1]

    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}query.html')
def query(request, template=None):
    data = {}
    data['product']  = request.path.split('/')[-1]

    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['query'] = mware.search()

    return render(request, template, data)


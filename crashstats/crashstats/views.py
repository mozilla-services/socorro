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
def home(request, product=None, versions=None, template=None):
    data = {}
    data['product'] = product
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['adubyday'] = mware.adu_by_day(product='Firefox',
        versions='13.0a1;14.0a2;13.0b2;12.0', os_names='Windows;Mac;Linux',
        start_date='2012-05-03', end_date='2012-05-10')

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topcrasher.html')
def topcrasher(request, product=None, version=None, days=None, crash_type=None,
               os_name=None, template=None):
    data = {}
    data['product'] = product
    data['version'] = version
    data['days'] = days
    data['crash_type'] = crash_type
    data['os_name'] = os_name
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['tcbs'] = mware.tcbs(product='Firefox', version='14.0a1',
        end_date='2012-05-10T11%3A00%3A00%2B0000', duration='168', limit='300')


    return render(request, template, data)

@mobile_template('crashstats/{mobile/}daily.html')
def daily(request, template=None):
    data = {}
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['adubyday'] = mware.adu_by_day(product='Firefox',
        versions='13.0a1;14.0a2;13.0b2;12.0', os_names='Windows;Mac;Linux',
        start_date='2012-05-03', end_date='2012-05-10')

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}builds.html')
def builds(request, product=None, template=None):
    data = {}
    data['product'] = product
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}hangreport.html')
def hangreport(request, product=None, version=None, template=None):
    data = {}
    data['product'] = product
    data['version'] = version
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topchangers.html')
def topchangers(request, product=None, versions=None, template=None):
    data = {}
    data['product'] = product
    data['versions'] = versions
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportlist.html')
def reportlist(request, template=None):
    data = {}
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportindex.html')
def reportindex(request, crash_id=None, template=None):
    data = {}
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}query.html')
def query(request, template=None):
    data = {}
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    data['query'] = mware.search(product='Firefox', 
        versions='13.0a1;14.0a2;13.0b2;12.0', os_names='Windows;Mac;Linux',
        start_date='2012-05-03', end_date='2012-05-10', limit='100')

    return render(request, template, data)


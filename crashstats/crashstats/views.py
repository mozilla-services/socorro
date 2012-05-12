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

# FIXME validate/scrub all info
# TODO would be better as a decorator
def _basedata(product=None, version=None):
    data = {}
    mware = SocorroMiddleware()
    data['currentversions'] = mware.current_versions()
    for release in data['currentversions']:
        if product == release['product']:
            data['product'] = product
            break
    for release in data['currentversions']:
        if version == release['version']:
            data['version'] = version
            break
    return data

@mobile_template('crashstats/{mobile/}products.html')
def home(request, product, versions=None, template=None):
    data = _basedata(product)

    # FIXME hardcoded default, find a better place for this to live
    os_names = ['Windows', 'Mac', 'Linux']

    duration = request.GET.get('duration')

    if duration is None or duration not in ['3','7','14']:
        duration = 7
    else:
       duration = int(duration)
        
    data['duration'] = duration
    
    if versions is None:
        versions = []
        for release in data['currentversions']:
            if release['product'] == product and release['featured']:
                versions.append(release['version'])
    else:
        versions = versions.split(';')

    if len(versions) == 1:
        data['version'] = versions[0]

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=duration)
 
    log.debug(start_date)
    log.debug(end_date)

    mware = SocorroMiddleware()
    data['adubyday'] = mware.adu_by_day(product, versions, os_names,
                                        start_date, end_date)

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topcrasher.html')
def topcrasher(request, product=None, version=None, days=None, crash_type=None,
               os_name=None, template=None):

    data = _basedata(product, version)

    if days is None or days not in [1,3,7,14,28]:
        days = 7
    data['days'] = days

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days)

    data['crash_type'] = crash_type
    data['os_name'] = os_name

    mware = SocorroMiddleware()
    data['tcbs'] = mware.tcbs(product, version, end_date,
                              duration='168', limit='300')


    return render(request, template, data)

@mobile_template('crashstats/{mobile/}daily.html')
def daily(request, template=None):
    data = _basedata()

    mware = SocorroMiddleware()
    data['adubyday'] = mware.adu_by_day(product='Firefox',
        versions='13.0a1;14.0a2;13.0b2;12.0', os_names='Windows;Mac;Linux',
        start_date='2012-05-03', end_date='2012-05-10')

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}builds.html')
def builds(request, product=None, template=None):
    data = _basedata(product)

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}hangreport.html')
def hangreport(request, product=None, version=None, template=None):
    data = _basedata(product, version)

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}topchangers.html')
def topchangers(request, product=None, versions=None, template=None):
    data = _basedata(product, versions)

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportlist.html')
def reportlist(request, template=None):
    data = _basedata()

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}reportindex.html')
def reportindex(request, crash_id=None, template=None):
    data = _basedata(product, versions)

    return render(request, template, data)

@mobile_template('crashstats/{mobile/}query.html')
def query(request, template=None):
    data = _basedata()

    mware = SocorroMiddleware()
    data['query'] = mware.search(product='Firefox', 
        versions='13.0a1;14.0a2;13.0b2;12.0', os_names='Windows;Mac;Linux',
        start_date='2012-05-03', end_date='2012-05-10', limit='100')

    return render(request, template, data)


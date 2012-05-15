import logging
import json
import datetime
import time
import os

from collections import defaultdict

from django import http
from django.shortcuts import render

from models import SocorroMiddleware, BugzillaAPI

import bleach
import commonware

from jingo import env, register
from funfactory.log import log_cef
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

def daterange(start_date, end_date, format='%Y-%m-%d'):
    for n in range((end_date - start_date).days):
        yield (start_date + datetime.timedelta(n)).strftime(format)

def plot_graph(start_date, end_date, adubyday):
    graph_data = {
        'startDate': adubyday['start_date'],
        'endDate': end_date.strftime('%Y-%m-%d'),
        'count': len(adubyday['versions']),
    }

    for i, version in enumerate(adubyday['versions'], start=1):
        graph_data['item%s' % i] = version['version']
        graph_data['ratio%s' % i] = []
        points = defaultdict(int)

        for s in version['statistics']:
            time = unixtime(s['date'], millis=True)
            if time in points:
                (crashes, users) = points[time]
            else:
                crashes = users = 0
            users += s['users']
            crashes += s['crashes']
            points[time] = (crashes, users)

        for day in daterange(start_date, end_date):
            time = unixtime(day, millis=True)

            if time in points:
                (crashes, users) = points[time]
                ratio = (float(crashes) / float(users) ) * 100.0
            else:
                ratio = None

            graph_data['ratio%s' % i].append([int(time), ratio])

    return graph_data

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

def home(request, product, versions=None):
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

    end_date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=duration)

    mware = SocorroMiddleware()
    adubyday = mware.adu_by_day(product, versions, os_names,
                                        start_date, end_date)

    data['graph_data'] = json.dumps(plot_graph(start_date, end_date, adubyday))

    return render(request, 'crashstats/products.html', data)

def topcrasher(request, product=None, version=None, days=None, crash_type=None,
               os_name=None):

    data = _basedata(product, version)

    if days is None or days not in ['1', '3', '7', '14', '28']:
        days = 7
    days = int(days)
    data['days'] = days

    end_date = datetime.datetime.utcnow()

    if crash_type is None or \
       crash_type not in ['all', 'browser', 'plugin', 'content']:
        crash_type = 'browser'

    data['crash_type'] = crash_type

    if os_name is None or os_name not in ['Windows', 'Linux', 'Mac OS X']:
        os_name = None

    data['os_name'] = os_name

    mware = SocorroMiddleware()
    tcbs = mware.tcbs(product, version, crash_type, end_date,
                      duration=(days * 24), limit='300')

    signatures = [c['signature'] for c in tcbs['crashes']]

    bugs = {}
    for b in mware.bugs(signatures)['bug_associations']:
        bug_id = b['bug_id']
        signature = b['signature']
        if signature in bugs:
            bugs[signature].append(bug_id)
        else:
            bugs[signature] = [bug_id]

    for crash in tcbs['crashes']:
        sig = crash['signature']
        if sig in bugs:
            if 'bugs' in crash:
                crash['bugs'].extend(bugs[sig])
            else:
                crash['bugs'] = bugs[sig]

    data['tcbs'] = tcbs

    return render(request, 'crashstats/topcrasher.html', data)

def daily(request):
    data = _basedata()

    product = request.GET.get('p')
    if product is None:
        product = 'Firefox'
    data['product'] = product

    versions = []
    for release in data['currentversions']:
        if release['product'] == product and release['featured']:
            versions.append(release['version'])

    os_names = ['Windows', 'Mac', 'Linux']

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=7)

    mware = SocorroMiddleware()
    adubyday = mware.adu_by_day(product, versions, os_names,
                                start_date, end_date)

    data['graph_data'] = json.dumps(plot_graph(start_date, end_date, adubyday))

    return render(request, 'crashstats/daily.html', data)

def builds(request, product=None):
    data = _basedata(product)

    return render(request, 'crashstats/builds.html', data)

def hangreport(request, product=None, version=None):
    data = _basedata(product, version)

    return render(request, 'crashstats/hangreport.html', data)

def topchangers(request, product=None, versions=None):
    data = _basedata(product, versions)

    return render(request, 'crashstats/topchangers.html', data)

def report_index(request, crash_id=None):
    data = _basedata()

    mware = SocorroMiddleware()
    data['report'] = mware.report_index(crash_id)

    return render(request, 'crashstats/report_index.html', data)

def report_list(request):
    data = _basedata()

    signature = request.GET.get('signature')
    product_version = request.GET.get('version')
    start_date = request.GET.get('date')
    result_number = 250

    mware = SocorroMiddleware()
    data['report_list'] = mware.report_list(signature, product_version,
                                            start_date, result_number)

    return render(request, 'crashstats/report_list.html', data)

def query(request):
    data = _basedata()

    mware = SocorroMiddleware()
    data['query'] = mware.search(product='Firefox', 
        versions='13.0a1;14.0a2;13.0b2;12.0', os_names='Windows;Mac;Linux',
        start_date='2012-05-03', end_date='2012-05-10', limit='100')

    return render(request, 'crashstats/query.html', data)

def buginfo(request, signatures=None):
    data = _basedata()

    bugs = request.GET.get('id').split(',')
    fields = request.GET.get('include_fields').split(',')

    bzapi = BugzillaAPI()
    data['bugs'] = json.dumps(bzapi.buginfo(bugs, fields))

    return render(request, 'crashstats/buginfo.html', data)

def correlation(request, correlation_type, product=None, version=None,
                template=None):
    data = _basedata()
    
    return render(request, 'crashstats/correlation.html', data)

"""Example views. Feel free to delete this app."""

import logging

from django import http
from django.shortcuts import render

import bleach
import commonware
from funfactory.log import log_cef
from mobility.decorators import mobile_template
from session_csrf import anonymous_csrf

import json

log = commonware.log.getLogger('playdoh')

def _basedata(request):
    data = {}
    data['product']  = request.path.split('/')[-1]
    with open('currentversions.json') as f:
        currentversions = json.loads(f.read())
        data['currentversions'] = currentversions['currentversions']
    return data

@mobile_template('crashstats/{mobile/}products.html')
def home(request, template=None):

    data = _basedata(request)
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

    data = _basedata(request)
    return render(request, template, data)

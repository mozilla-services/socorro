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

@mobile_template('crashstats/{mobile/}products.html')
def home(request, template=None):
    """Main crashstats view."""

    data = {'product': request.path.split('/')[-1]}
    with open('data.json') as f:
        data = (data.items() + json.loads(f.read()).items())

    return render(request, template, data)

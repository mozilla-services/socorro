import hashlib

from collections import OrderedDict
import requests
from six.moves.urllib.parse import urlparse

from django import http
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import connection
from django.shortcuts import redirect, render

from crashstats.manage.decorators import superuser_required
from crashstats.manage import forms
from crashstats.manage import utils
from crashstats.supersearch.models import SuperSearchMissingFields
from crashstats.crashstats.models import GraphicsDevices
from crashstats.crashstats.utils import json_view


@superuser_required
def crash_me_now(request):
    # NOTE(willkg): This intentionally throws an error so that we can test
    # unhandled error handling.
    1 / 0  # noqa


@superuser_required
def site_status(request):
    context = {}

    # Get version information for deployed parts
    version_info = {}
    for url in settings.OVERVIEW_VERSION_URLS.split(','):
        hostname = urlparse(url).netloc
        url = url.strip()
        try:
            data = requests.get(url).json()
        except Exception as exc:
            data = {'error': str(exc)}
        version_info[hostname] = data

    context['version_info'] = version_info

    # Get alembic migration data
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version_num FROM alembic_version')
            alembic_version = cursor.fetchone()[0]
            alembic_error = ''
    except Exception as exc:
        alembic_version = ''
        alembic_error = 'error: %s' % exc
    context['alembic_version'] = alembic_version
    context['alembic_error'] = alembic_error

    # Get Django migration data
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT id, app, name, applied FROM django_migrations')
            cols = [col[0] for col in cursor.description]
            django_db_data = [dict(zip(cols, row)) for row in cursor.fetchall()]
            django_db_error = ''
    except Exception as exc:
        django_db_data = []
        django_db_error = 'error: %s' % exc
    context['django_db_data'] = django_db_data
    context['django_db_error'] = django_db_error

    # Get crontabber data
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT app_name, next_run, last_run, last_success, error_count, last_error '
                'FROM crontabber WHERE error_count > 0'
            )
            cols = [col[0] for col in cursor.description]
            crontabber_data = [dict(zip(cols, row)) for row in cursor.fetchall()]
            crontabber_error = ''
    except Exception as exc:
        crontabber_data = []
        crontabber_error = 'error: %s' % exc
    context['crontabber_data'] = crontabber_data
    context['crontabber_error'] = crontabber_error
    context['title'] = 'Site status'

    return render(request, 'admin/site_status.html', context)


@superuser_required
def analyze_model_fetches(request):
    context = {}
    all_ = cache.get('all_classes') or []
    records = []
    for item in all_:
        itemkey = hashlib.md5(item.encode('utf-8')).hexdigest()

        data = {}
        data['times'] = {}
        data['times']['hits'] = cache.get('times_HIT_%s' % itemkey, 0)
        data['times']['misses'] = cache.get('times_MISS_%s' % itemkey, 0)
        data['times']['both'] = (
            data['times']['hits'] + data['times']['misses']
        )
        data['uses'] = {}
        data['uses']['hits'] = cache.get('uses_HIT_%s' % itemkey, 0)
        data['uses']['misses'] = cache.get('uses_MISS_%s' % itemkey, 0)
        data['uses']['both'] = (
            data['uses']['hits'] + data['uses']['misses']
        )
        data['uses']['hits_percentage'] = (
            data['uses']['both'] and
            round(
                100.0 * data['uses']['hits'] / data['uses']['both'],
                1
            ) or
            'n/a'
        )
        records.append((item, data))
    context['records'] = records
    context['title'] = 'Analyze model fetches'

    return render(request, 'admin/analyze-model-fetches.html', context)


@superuser_required
def supersearch_fields_missing(request):
    context = {}
    missing_fields = SuperSearchMissingFields().get()

    context['missing_fields'] = missing_fields['hits']
    context['missing_fields_count'] = missing_fields['total']
    context['title'] = 'Super search missing fields'

    return render(request, 'admin/supersearch_fields_missing.html', context)


@superuser_required
def graphics_devices(request):
    context = {}
    form = forms.GraphicsDeviceForm()
    upload_form = forms.GraphicsDeviceUploadForm()

    if request.method == 'POST' and 'file' in request.FILES:
        upload_form = forms.GraphicsDeviceUploadForm(
            request.POST,
            request.FILES
        )
        if upload_form.is_valid():
            if upload_form.cleaned_data['database'] == 'pcidatabase.com':
                function = utils.pcidatabase__parse_graphics_devices_iterable
            else:
                function = utils.pci_ids__parse_graphics_devices_iterable

            payload = list(function(upload_form.cleaned_data['file']))
            api = GraphicsDevices()
            result = api.post(data=payload)
            messages.success(
                request,
                'Graphics device CSV upload successfully saved.'
            )
            return redirect('siteadmin:graphics_devices')

    elif request.method == 'POST':
        form = forms.GraphicsDeviceForm(request.POST)
        if form.is_valid():
            payload = [{
                'vendor_hex': form.cleaned_data['vendor_hex'],
                'adapter_hex': form.cleaned_data['adapter_hex'],
                'vendor_name': form.cleaned_data['vendor_name'],
                'adapter_name': form.cleaned_data['adapter_name'],
            }]
            api = GraphicsDevices()
            result = api.post(data=payload)
            if result:
                messages.success(
                    request,
                    'Graphics device saved.'
                )
            return redirect('siteadmin:graphics_devices')

    context['title'] = "Graphics devices"
    context['form'] = form
    context['upload_form'] = upload_form
    return render(request, 'admin/graphics_devices.html', context)


@json_view
@superuser_required
def graphics_devices_lookup(request):
    form = forms.GraphicsDeviceLookupForm(request.GET)
    if form.is_valid():
        vendor_hex = form.cleaned_data['vendor_hex']
        adapter_hex = form.cleaned_data['adapter_hex']
        api = GraphicsDevices()
        result = api.get(vendor_hex=vendor_hex, adapter_hex=adapter_hex)
        return result
    else:
        return http.HttpResponseBadRequest(str(form.errors))


@superuser_required
def debug_view(request):
    """This view is for ephemeral debugging of issues"""

    context = {}

    # Map of key -> val that will get displayed in a big table in the debug
    # view in the order they were inserted
    debug_info = OrderedDict()

    # Add IP address related headers to figure out rate-limiting issues. #1475993
    for meta_header in ['HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR']:
        debug_info['request.META["' + meta_header + '"]'] = request.META.get(meta_header, 'none')

    context['debug_info'] = debug_info
    context['title'] = 'Debug information'

    return render(request, 'admin/debug_view.html', context)

import hashlib

from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION
from django.core.cache import cache
from django.db import connection
from django.shortcuts import redirect, render

import requests

from crashstats.crashstats.models import GraphicsDevices
from crashstats.supersearch.models import SuperSearchMissingFields
from crashstats.crashstats.utils import json_view
from crashstats.manage.decorators import superuser_required

from . import forms
from . import utils


def log_action(user_id, action_flag, change_message):
    LogEntry.objects.create(
        user_id=user_id,
        content_type_id=None,
        object_id=None,
        object_repr='',
        action_flag=action_flag,
        change_message=change_message
    )


@superuser_required
def home(request, default_context=None):
    context = default_context or {}
    return render(request, 'manage/home.html', context)


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
    return render(request, 'manage/analyze-model-fetches.html', context)


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
            log_action(
                user_id=request.user.id,
                action_flag=ADDITION,
                change_message='graphics_devices: CSV upload: result: %s, lines: %s, %r' % (
                    result, len(payload), upload_form.cleaned_data['database']
                )
            )
            messages.success(
                request,
                'Graphics device CSV upload successfully saved.'
            )
            return redirect('manage:graphics_devices')

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
            log_action(
                user_id=request.user.id,
                action_flag=ADDITION,
                change_message='graphics_devices: added item: %s %r' % (
                    result, sorted(payload[0].items())
                )
            )
            if result:
                messages.success(
                    request,
                    'Graphics device saved.'
                )
            return redirect('manage:graphics_devices')

    context['page_title'] = "Graphics Devices"
    context['form'] = form
    context['upload_form'] = upload_form
    return render(request, 'manage/graphics_devices.html', context)


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
def supersearch_fields_missing(request):
    context = {}
    missing_fields = SuperSearchMissingFields().get()

    context['missing_fields'] = missing_fields['hits']
    context['missing_fields_count'] = missing_fields['total']

    return render(request, 'manage/supersearch_fields_missing.html', context)


@superuser_required
def crash_me_now(request):
    if request.method == 'POST':
        form = forms.CrashMeNowForm(request.POST)
        if form.is_valid():
            klass = {
                'NameError': NameError,
                'ValueError': ValueError,
                'AttributeError': AttributeError
            }.get(form.cleaned_data['exception_type'])
            # crash now!
            raise klass(form.cleaned_data['exception_value'])
    else:
        initial = {
            'exception_type': 'NameError',
            'exception_value': 'Webapp Crash Me Now test error',
        }
        form = forms.CrashMeNowForm(initial=initial)
    context = {'form': form}
    return render(request, 'manage/crash_me_now.html', context)


@superuser_required
def site_status(request):
    context = {}

    # Get version information for deployed parts
    version_info = {}
    for url in settings.OVERVIEW_VERSION_URLS.split(','):
        url = url.strip()
        try:
            data = requests.get(url).json()
        except Exception as exc:
            data = {'error': str(exc)}
        version_info[url] = data

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

    return render(request, 'manage/site_status.html', context)

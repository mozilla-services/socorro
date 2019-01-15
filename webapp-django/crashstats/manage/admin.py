import datetime
import hashlib
import json

from collections import OrderedDict
import requests
from six.moves.urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import connection, transaction
from django.shortcuts import redirect, render

from crashstats.crashstats.models import GraphicsDevice
from crashstats.manage import forms
from crashstats.manage import utils
from crashstats.manage.decorators import superuser_required
from crashstats.supersearch.models import SuperSearchMissingFields
from socorro.lib.requestslib import session_with_retries


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
        # There's no crontabber tables in the db when the tests run
        # because it's not managed by Django. Therefore this sql fails
        # in the tests. When this fails, it kills the transaction the tests
        # run in which loses the request session which causes the session
        # middleware to kick up an HTTP 400 which causes the test to fail.
        #
        # Wrapping this in an atomic context prevents that cavalcade of
        # clown shoes from happening.
        with transaction.atomic():
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
    upload_form = forms.GraphicsDeviceUploadForm()

    if request.method == 'POST' and 'file' in request.FILES:
        upload_form = forms.GraphicsDeviceUploadForm(request.POST, request.FILES)
        if upload_form.is_valid():
            devices = utils.pci_ids__parse_graphics_devices_iterable(
                upload_form.cleaned_data['file']
            )

            for item in devices:
                obj, _ = GraphicsDevice.objects.get_or_create(
                    vendor_hex=item['vendor_hex'],
                    adapter_hex=item['adapter_hex']
                )
                obj.vendor_name = item['vendor_name']
                obj.adapter_name = item['adapter_name']
                obj.save()

            messages.success(request, 'Graphics device CSV upload successfully saved.')
            return redirect('siteadmin:graphics_devices')

    context['title'] = "Graphics devices"
    context['upload_form'] = upload_form
    return render(request, 'admin/graphics_devices.html', context)


@superuser_required
def debug_view(request):
    """This view is for ephemeral debugging of issues"""
    context = {}

    # Map of key -> val that will get displayed in a big table in the debug
    # view in the order they were inserted
    debug_info = OrderedDict()

    # Add IP address related headers to figure out rate-limiting issues. #1475993
    for meta_header in ['HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR', 'HTTP_X_REAL_IP']:
        debug_info['request.META["' + meta_header + '"]'] = request.META.get(meta_header, 'none')

    # Add table counts for all non-pg tables
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT c.relname
        FROM pg_catalog.pg_class c
        WHERE c.relkind = 'r'
        """)
        tables = cursor.fetchall()
    for tablename in sorted(tables):
        tablename = tablename[0]
        if tablename.startswith(('pg_', 'sql_', 'lock')):
            continue
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM %s' % tablename)
            debug_info['%s count' % tablename] = cursor.fetchone()[0]

    context['debug_info'] = debug_info
    context['title'] = 'Debug information'

    return render(request, 'admin/debug_view.html', context)

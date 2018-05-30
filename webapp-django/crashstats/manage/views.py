import hashlib

from django import http
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db import connection
from django.shortcuts import redirect, render

from pinax.eventlog.models import log, Log
import requests

from crashstats.crashstats.models import (
    GraphicsDevices,
    Reprocessing,
)
from crashstats.supersearch.models import SuperSearchMissingFields
from crashstats.crashstats.utils import json_view
from crashstats.manage.decorators import superuser_required

from . import forms
from . import utils


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
            log(request.user, 'graphicsdevices.post', {
                'success': result,
                'database': upload_form.cleaned_data['database'],
                'no_lines': len(payload),
            })
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
            log(request.user, 'graphicsdevices.add', {
                'payload': payload,
                'success': result
            })
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
def events(request):
    context = {}

    # The reason we can't use `.distinct('action')` is because
    # many developers use sqlite for local development and
    # that's not supported.
    # If you use postgres, `Log.objects.all().values('action').distinct()`
    # will actually return a unique list of dicts.
    # Either way it's no inefficient convert it to a set and back to a list
    # because there are so few in local dev and moot in prod.
    context['all_actions'] = list(set([
        x['action'] for x in
        Log.objects.all().values('action').distinct()
    ]))
    return render(request, 'manage/events.html', context)


@json_view
@superuser_required
def events_data(request):
    form = forms.FilterEventsForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))
    events_ = Log.objects.all()
    if form.cleaned_data['user']:
        events_ = events_.filter(
            user__email__icontains=form.cleaned_data['user']
        )
    if form.cleaned_data['action']:
        events_ = events_.filter(
            action=form.cleaned_data['action']
        )
    count = events_.count()
    try:
        page = int(request.GET.get('page', 1))
        assert page >= 1
    except (ValueError, AssertionError):
        return http.HttpResponseBadRequest('invalid page')
    items = []
    batch_size = settings.EVENTS_ADMIN_BATCH_SIZE
    batch = Paginator(events_.select_related('user'), batch_size)
    batch_page = batch.page(page)

    def _get_edit_url(action, extra):
        if action == 'user.edit' and extra.get('id'):
            return reverse('admin:auth_user_change', args=(extra.get('id'),))
        if action in ('group.edit', 'group.add') and extra.get('id'):
            return reverse('admin:auth_group_change', args=(extra.get('id'),))

    for event in batch_page.object_list:
        items.append({
            'user': event.user.email,
            'timestamp': event.timestamp.isoformat(),
            'action': event.action,
            'extra': event.extra,
            'url': _get_edit_url(event.action, event.extra)
        })

    return {
        'events': items,
        'count': count,
        'batch_size': batch_size,
        'page': page,
    }


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
def reprocessing(request):
    if request.method == 'POST':
        form = forms.ReprocessingForm(request.POST)
        if form.is_valid():
            crash_id = form.cleaned_data['crash_id']
            url = reverse('manage:reprocessing')
            worked = Reprocessing().post(crash_ids=[crash_id])
            if worked:
                url += '?crash_id={}'.format(crash_id)
                messages.success(
                    request,
                    '{} sent in for reprocessing.'.format(crash_id)
                )
            else:
                messages.error(
                    request,
                    'Currently unable to send in the crash ID '
                    'for reprocessing.'
                )
            log(request.user, 'reprocessing', {
                'crash_id': crash_id,
                'worked': worked,
            })

            return redirect(url)
    else:
        form = forms.ReprocessingForm()
    context = {
        'form': form,
        'crash_id': request.GET.get('crash_id'),
    }
    return render(request, 'manage/reprocessing.html', context)


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

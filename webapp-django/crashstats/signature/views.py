import datetime
import functools
import math
import urllib

import isodate

from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.conf import settings

from socorrolib.lib import BadArgumentError

from crashstats.base.utils import render_exception
from crashstats.api.views import has_permissions
from crashstats.crashstats import models, utils
from crashstats.crashstats.views import pass_default_context
from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchUnredacted,
)
from crashstats.supersearch.views import (
    ValidationError,
    get_allowed_fields,
    get_params,
    get_report_list_parameters,
)


DEFAULT_COLUMNS = (
    'date',
    'product',
    'version',
    'build_id',
    'platform',
    'reason',
    'address',
)


def pass_validated_params(view):
    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        try:
            params = get_params(request)

            if len(params['signature']) > 1:
                raise ValidationError(
                    'Invalid value for "signature" parameter, '
                    'only one value is accepted'
                )

            if not params['signature'] or not params['signature'][0]:
                raise ValidationError(
                    '"signature" parameter is mandatory'
                )
        except ValidationError as e:
            return http.HttpResponseBadRequest(str(e))

        args += (params,)
        return view(request, *args, **kwargs)
    return inner


@pass_validated_params
@pass_default_context
def signature_report(request, params, default_context=None):
    context = default_context

    signature = request.GET.get('signature')
    if not signature:
        return http.HttpResponseBadRequest(
            '"signature" parameter is mandatory'
        )

    context['signature'] = signature

    fields = sorted(
        x['name']
        for x in SuperSearchFields().get().values()
        if x['is_exposed'] and
        x['is_returned'] and
        has_permissions(request.user, x['permissions_needed']) and
        x['name'] != 'signature'  # exclude the signature field
    )
    context['fields'] = [
        {'id': field, 'text': field.replace('_', ' ')} for field in fields
    ]

    columns = request.GET.getlist('_columns')
    columns = [x for x in columns if x in fields]
    context['columns'] = columns or DEFAULT_COLUMNS

    context['channels'] = ','.join(settings.CHANNELS).split(',')
    context['channel'] = settings.CHANNEL

    context['report_list_query_string'] = urllib.urlencode(
        utils.sanitize_dict(
            get_report_list_parameters(params)
        ),
        True
    )

    return render(request, 'signature/signature_report.html', context)


@pass_validated_params
def signature_reports(request, params):
    '''Return the results of a search. '''

    signature = params['signature'][0]

    context = {}
    context['query'] = {
        'total': 0,
        'total_count': 0,
        'total_pages': 0
    }

    allowed_fields = get_allowed_fields(request.user)

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']

    context['params'] = current_query.copy()

    if '_columns' in context['params']:
        del context['params']['_columns']

    context['columns'] = request.GET.getlist('_columns') or DEFAULT_COLUMNS

    # Make sure only allowed fields are used
    context['columns'] = [
        x for x in context['columns'] if x in allowed_fields
    ]

    # Copy the list of columns so that they can differ.
    params['_columns'] = list(context['columns'])

    # The uuid is always displayed in the UI so we need to make sure it is
    # always returned by the model.
    if 'uuid' not in params['_columns']:
        params['_columns'].append('uuid')

    # We require the cpu_info field to show a special marker on some AMD CPU
    # related crash reports.
    if 'cpu_info' not in params['_columns']:
        params['_columns'].append('cpu_info')

    # The `uuid` field is a special case, it is always displayed in the first
    # column of the table. Hence we do not want to show it again in the
    # auto-generated list of columns, so we its name from the list of
    # columns to display.
    if 'uuid' in context['columns']:
        context['columns'].remove('uuid')

    try:
        current_page = int(request.GET.get('page', 1))
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    if current_page <= 0:
        current_page = 1

    results_per_page = 50
    context['current_page'] = current_page
    context['results_offset'] = results_per_page * (current_page - 1)

    params['signature'] = '=' + signature
    params['_results_number'] = results_per_page
    params['_results_offset'] = context['results_offset']
    params['_facets'] = []  # We don't need no facets.

    context['current_url'] = '%s?%s' % (
        reverse('signature:signature_report'),
        current_query.urlencode()
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    search_results['total_pages'] = int(
        math.ceil(
            search_results['total'] / float(results_per_page)
        )
    )
    search_results['total_count'] = search_results['total']

    context['query'] = search_results

    return render(request, 'signature/signature_reports.html', context)


@pass_validated_params
def signature_aggregation(request, params, aggregation):
    '''Return the aggregation of a field. '''

    signature = params['signature'][0]

    context = {}
    context['aggregation'] = aggregation

    allowed_fields = get_allowed_fields(request.user)

    # Make sure the field we want to aggregate on is allowed.
    if aggregation not in allowed_fields:
        return http.HttpResponseBadRequest(
            '<ul><li>'
            'You are not allowed to aggregate on the "%s" field'
            '</li></ul>' % aggregation
        )

    current_query = request.GET.copy()
    context['params'] = current_query.copy()

    params['signature'] = '=' + signature
    params['_results_number'] = 0
    params['_results_offset'] = 0
    params['_facets'] = [aggregation]

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    context['aggregates'] = []
    if aggregation in search_results['facets']:
        context['aggregates'] = search_results['facets'][aggregation]

    context['total_count'] = search_results['total']

    return render(request, 'signature/signature_aggregation.html', context)


@utils.json_view
@pass_validated_params
def signature_graphs(request, params, field):
    '''Return a multi-line graph of crashes per day grouped by field. '''

    signature = params['signature'][0]

    context = {}
    context['aggregation'] = field

    allowed_fields = get_allowed_fields(request.user)

    # Make sure the field we want to aggregate on is allowed.
    if field not in allowed_fields:
        return http.HttpResponseBadRequest(
            '<ul><li>'
            'You are not allowed to group by the "%s" field'
            '</li></ul>' % field
        )

    current_query = request.GET.copy()
    context['params'] = current_query.copy()

    params['signature'] = '=' + signature
    params['_results_number'] = 0
    params['_results_offset'] = 0
    params['_histogram.date'] = [field]
    params['_facets'] = [field]

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    context['aggregates'] = search_results['facets'].get('histogram_date', [])
    context['term_counts'] = search_results['facets'].get(field, [])

    return context


@pass_validated_params
def signature_comments(request, params):
    '''Return a list of non-empty comments. '''

    signature = params['signature'][0]

    context = {}
    context['query'] = {
        'total': 0,
        'total_count': 0,
        'total_pages': 0
    }

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']

    context['params'] = current_query.copy()

    try:
        current_page = int(request.GET.get('page', 1))
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    if current_page <= 0:
        current_page = 1

    results_per_page = 50
    context['current_page'] = current_page
    context['results_offset'] = results_per_page * (current_page - 1)

    params['signature'] = '=' + signature
    params['user_comments'] = '!__null__'
    params['_columns'] = ['uuid', 'user_comments', 'date', 'useragent_locale']
    params['_results_number'] = results_per_page
    params['_results_offset'] = context['results_offset']
    params['_facets'] = []  # We don't need no facets.

    context['current_url'] = '%s?%s' % (
        reverse('signature:signature_report'),
        current_query.urlencode()
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    search_results['total_pages'] = int(
        math.ceil(
            search_results['total'] / float(results_per_page)
        )
    )
    search_results['total_count'] = search_results['total']

    context['query'] = search_results

    return render(request, 'signature/signature_comments.html', context)


@pass_validated_params
def signature_correlations(request, params):
    '''Return a list of correlations combos, to be populated by AJAX calls. '''
    signature = params['signature'][0]

    context = {}

    params['signature'] = '=' + signature
    params['_results_number'] = 0
    params['_facets'] = []
    params['_aggs.product.version'] = 'platform'

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    all_combos = []
    for product in search_results['facets']['product']:
        for version in product['facets']['version']:
            for platform in version['facets']['platform']:
                all_combos.append({
                    'product': product['term'],
                    'version': version['term'],
                    'platform': platform['term'],
                    'count': platform['count'],
                })

    all_combos = sorted(all_combos, key=lambda x: x['count'])
    context['correlation_combos'] = (
        all_combos[:settings.MAX_CORRELATION_COMBOS_PER_SIGNATURE]
    )

    return render(request, 'signature/signature_correlations.html', context)


@utils.json_view
@pass_validated_params
def signature_graph_data(request, params, channel):
    '''Return data for the graph of crashes/ADU against build date'''

    signature = params['signature'][0]

    # Check that a product was specified
    if not params['product'] or not params['product'][0]:
        return http.HttpResponseBadRequest(
            '"product" parameter is mandatory'
        )
    product = params['product'][0]

    # Initialise start and end dates
    start_date = None
    end_date = None

    # Store one day as variable for readability
    one_day = datetime.timedelta(days=1)

    # Check for dates
    if 'date' in params:
        for date in params['date']:
            # Set the earliest given start date as the start date
            if date.startswith('>'):
                if date.startswith('>='):
                    d = isodate.parse_date(date.lstrip('>='))
                else:
                    d = isodate.parse_date(date.lstrip('>')) + one_day
                if not start_date or d < start_date:
                    start_date = d
            # Set the latest given end date as the end date
            elif date.startswith('<'):
                if date.startswith('<='):
                    d = isodate.parse_date(date.lstrip('<='))
                else:
                    d = isodate.parse_date(date.lstrip('<')) - one_day
                if not end_date or d > end_date:
                    end_date = d

    # If start date wasn't given, set it to 7 days before the end date
    # If end date wasn't given either, set it to 7 days before today
    if not start_date:
        if end_date:
            start_date = end_date - datetime.timedelta(days=7)
        else:
            start_date = datetime.datetime.utcnow() - datetime.timedelta(
                days=7
            )

    # If end date wasn't given, set it to today
    if not end_date:
        end_date = datetime.datetime.utcnow()

    # Get the graph data
    api = models.AduBySignature()
    data = api.get(
        signature=signature,
        product_name=product,
        start_date=start_date,
        end_date=end_date,
        channel=channel
    )

    return data


@pass_validated_params
def signature_summary(request, params):
    '''Return a list of specific aggregations. '''

    context = {}

    params['signature'] = '=' + params['signature'][0]
    params['_results_number'] = 0
    params['_facets'] = [
        'platform_pretty_version',
        'cpu_name',
        'process_type',
        'flash_version',
    ]
    params['_histogram.uptime'] = ['product']
    params['_histogram_interval.uptime'] = 60
    params['_aggs.adapter_vendor_id'] = ['adapter_device_id']
    params['_aggs.android_cpu_abi.android_manufacturer.android_model'] = [
        'android_version'
    ]

    # If the user has permissions, show exploitability.
    all_fields = SuperSearchFields().get()
    if has_permissions(
        request.user, all_fields['exploitability']['permissions_needed']
    ):
        params['_histogram.date'] = ['exploitability']

    api = SuperSearchUnredacted()

    # Now make the actual request with all expected parameters.
    try:
        search_results = api.get(**params)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    facets = search_results['facets']

    # We need to make a separate query so that we can show all versions and
    # not just the one asked for.
    params_copy = {
        'signature': params['signature'],
        '_aggs.product.version': ['_cardinality.install_time'],
    }

    try:
        product_results = api.get(**params_copy)
    except BadArgumentError as e:
        # We need to return the error message in some HTML form for jQuery
        # to pick it up.
        return http.HttpResponseBadRequest(render_exception(e))

    if 'product' in product_results['facets']:
        facets['product'] = product_results['facets']['product']
    else:
        facets['product'] = []

    context['product_version_total'] = product_results['total']

    _transform_uptime_summary(facets)
    _transform_graphics_summary(facets)
    _transform_mobile_summary(facets)
    _transform_exploitability_summary(facets)

    context['query'] = search_results

    return render(request, 'signature/signature_summary.html', context)


def _transform_graphics_summary(facets):
    # Augment graphics adapter with data from another service.
    if 'adapter_vendor_id' in facets:
        vendor_hexes = []
        adapter_hexes = []
        for vendor in facets['adapter_vendor_id']:
            for adapter in vendor['facets']['adapter_device_id']:
                vendor_hexes.append(vendor['term'])
                adapter_hexes.append(adapter['term'])

        devices_api = models.GraphicsDevices()

        all_names = devices_api.get_pairs(adapter_hexes, vendor_hexes)
        graphics = []
        for vendor in facets['adapter_vendor_id']:
            for adapter in vendor['facets']['adapter_device_id']:
                entry = {
                    'vendor': vendor['term'],
                    'adapter': adapter['term'],
                    'count': adapter['count'],
                }
                key = (adapter['term'], vendor['term'])
                names = all_names.get(key)
                if names and names[0]:
                    entry['adapter'] = '{} ({})'.format(
                        names[0],
                        adapter['term'],
                    )
                if names and names[1]:
                    entry['vendor'] = '{} ({})'.format(
                        names[1],
                        vendor['term'],
                    )

                graphics.append(entry)

        # By default, results are sorted by vendor count then adapter count.
        # We instead need to sort them by adapter count only. That cannot be
        # done in SuperSearch directly, so we do it here.
        facets['adapter_vendor_id'] = sorted(
            graphics,
            key=lambda x: x['count'],
            reverse=True
        )


def _transform_uptime_summary(facets):
    # Transform uptime data to be easier to consume.
    # Keys are in minutes.
    if 'histogram_uptime' in facets:
        labels = {
            0: '< 1 min',
            1: '1-5 min',
            5: '5-15 min',
            15: '15-60 min',
            60: '> 1 hour'
        }
        uptimes_count = dict((x, 0) for x in labels)

        for uptime in facets['histogram_uptime']:
            for uptime_minutes in sorted(uptimes_count.keys(), reverse=True):
                uptime_seconds = uptime_minutes * 60

                if uptime['term'] >= uptime_seconds:
                    uptimes_count[uptime_minutes] += uptime['count']
                    break

        uptimes = [
            {'term': labels.get(key), 'count': count}
            for key, count in uptimes_count.items()
            if count > 0
        ]
        uptimes = sorted(uptimes, key=lambda x: x['count'], reverse=True)

        facets['histogram_uptime'] = uptimes


def _transform_mobile_summary(facets):
    if 'android_cpu_abi' in facets:
        mobile_devices = []

        for cpu_abi in facets['android_cpu_abi']:
            for manufacturer in cpu_abi['facets']['android_manufacturer']:
                for model in manufacturer['facets']['android_model']:
                    for version in model['facets']['android_version']:
                        mobile_devices.append({
                            'cpu_abi': cpu_abi['term'],
                            'manufacturer': manufacturer['term'],
                            'model': model['term'],
                            'version': version['term'],
                            'count': version['count'],
                        })

        facets['android_cpu_abi'] = mobile_devices


def _transform_exploitability_summary(facets):
    # Transform exploitability facet.
    if 'histogram_date' in facets:
        exploitability_base = {
            'none': 0,
            'low': 0,
            'medium': 0,
            'high': 0,
        }
        for day in facets['histogram_date']:
            exploitability = dict(exploitability_base)
            for expl in day['facets']['exploitability']:
                if expl['term'] in exploitability:
                    exploitability[expl['term']] = expl['count']
            day['exploitability'] = exploitability

        facets['histogram_date'] = sorted(
            facets['histogram_date'],
            key=lambda x: x['term'],
            reverse=True
        )


@pass_validated_params
def signature_bugzilla(request, params):
    '''Return a list of associated bugs. '''
    context = {}

    signature = params['signature'][0]
    context['signature'] = signature

    bugs_api = models.Bugs()
    context['bugs'] = bugs_api.get(
        signatures=[signature]
    )['hits']

    context['bugs'].sort(key=lambda x: x['id'], reverse=True)

    return render(request, 'signature/signature_bugzilla.html', context)

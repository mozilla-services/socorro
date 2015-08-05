import math
import urllib
import isodate
import datetime

from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.conf import settings

from waffle.decorators import waffle_switch

from crashstats.api.views import has_permissions
from crashstats.crashstats import models, utils
from crashstats.crashstats.views import pass_default_context
from crashstats.supersearch.models import (
    SuperSearchUnredacted,
    SuperSearchFields,
)
from crashstats.supersearch.views import (
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


def get_validated_params(request):
    params = get_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

    if len(params['signature']) > 1:
        return http.HttpResponseBadRequest(
            'Invalid value for "signature" parameter, '
            'only one value is accepted'
        )

    if not params['signature'] or not params['signature'][0]:
        return http.HttpResponseBadRequest(
            '"signature" parameter is mandatory'
        )

    return params


@waffle_switch('signature-report')
@pass_default_context
def signature_report(request, default_context=None):
    context = default_context

    params = get_validated_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

    signature = request.GET.get('signature')
    if not signature:
        return http.HttpResponseBadRequest(
            '"signature" parameter is mandatory'
        )

    context['signature'] = signature

    fields = sorted(
        x['name']
        for x in SuperSearchFields().get().values()
        if x['is_exposed']
        and x['is_returned']
        and has_permissions(request.user, x['permissions_needed'])
        and x['name'] != 'signature'  # exclude the signature field
    )
    context['fields'] = [
        {'id': field, 'text': field.replace('_', ' ')} for field in fields
    ]

    context['columns'] = request.GET.getlist('_columns') or DEFAULT_COLUMNS

    context['channels'] = ','.join(settings.CHANNELS).split(',')
    context['channel'] = settings.CHANNEL

    context['report_list_query_string'] = urllib.urlencode(
        utils.sanitize_dict(
            get_report_list_parameters(params)
        ),
        True
    )

    return render(request, 'signature/signature_report.html', context)


@waffle_switch('signature-report')
def signature_reports(request):
    '''Return the results of a search. '''
    params = get_validated_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

    signature = params['signature'][0]

    data = {}
    data['query'] = {
        'total': 0,
        'total_count': 0,
        'total_pages': 0
    }

    allowed_fields = get_allowed_fields(request.user)

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']

    data['params'] = current_query.copy()

    if '_columns' in data['params']:
        del data['params']['_columns']

    data['columns'] = request.GET.getlist('_columns') or DEFAULT_COLUMNS

    # Make sure only allowed fields are used
    data['columns'] = [
        x for x in data['columns'] if x in allowed_fields
    ]

    params['_columns'] = data['columns']

    # The uuid is always displayed in the UI so we need to make sure it is
    # always returned by the model.
    if 'uuid' not in params['_columns']:
        params['_columns'].append('uuid')

    try:
        current_page = int(request.GET.get('page', 1))
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    if current_page <= 0:
        current_page = 1

    results_per_page = 50
    data['current_page'] = current_page
    data['results_offset'] = results_per_page * (current_page - 1)

    params['signature'] = '=' + signature
    params['_results_number'] = results_per_page
    params['_results_offset'] = data['results_offset']
    params['_facets'] = []  # We don't need no facets.

    data['current_url'] = '%s?%s' % (
        reverse('signature:signature_report'),
        current_query.urlencode()
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except models.BadStatusCodeError, e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest('<ul><li>%s</li></ul>' % e)

    search_results['total_pages'] = int(
        math.ceil(
            search_results['total'] / float(results_per_page)
        )
    )
    search_results['total_count'] = search_results['total']

    data['query'] = search_results

    return render(request, 'signature/signature_reports.html', data)


@waffle_switch('signature-report')
def signature_aggregation(request, aggregation):
    '''Return the aggregation of a field. '''
    params = get_validated_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

    signature = params['signature'][0]

    data = {}
    data['aggregation'] = aggregation

    allowed_fields = get_allowed_fields(request.user)

    # Make sure the field we want to aggregate on is allowed.
    if aggregation not in allowed_fields:
        return http.HttpResponseBadRequest(
            '<ul><li>'
            'You are not allowed to aggregate on the "%s" field'
            '</li></ul>' % aggregation
        )

    current_query = request.GET.copy()
    data['params'] = current_query.copy()

    params['signature'] = '=' + signature
    params['_results_number'] = 0
    params['_results_offset'] = 0
    params['_facets'] = [aggregation]

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except models.BadStatusCodeError, e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest('<ul><li>%s</li></ul>' % e)

    data['aggregates'] = []
    if aggregation in search_results['facets']:
        data['aggregates'] = search_results['facets'][aggregation]

    data['total_count'] = search_results['total']

    return render(request, 'signature/signature_aggregation.html', data)


@waffle_switch('signature-report')
@utils.json_view
def signature_graphs(request, field):
    '''Return a multi-line graph of crashes per day grouped by field. '''
    params = get_validated_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

    signature = params['signature'][0]

    data = {}
    data['aggregation'] = field

    allowed_fields = get_allowed_fields(request.user)

    # Make sure the field we want to aggregate on is allowed.
    if field not in allowed_fields:
        return http.HttpResponseBadRequest(
            '<ul><li>'
            'You are not allowed to group by the "%s" field'
            '</li></ul>' % field
        )

    current_query = request.GET.copy()
    data['params'] = current_query.copy()

    params['signature'] = '=' + signature
    params['_results_number'] = 0
    params['_results_offset'] = 0
    params['_histogram.date'] = [field]
    params['_facets'] = [field]

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except models.BadStatusCodeError, e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest('<ul><li>%s</li></ul>' % e)

    data['aggregates'] = search_results['facets']['histogram_date']
    data['term_counts'] = search_results['facets'][field]

    return data


@waffle_switch('signature-report')
def signature_comments(request):
    '''Return a list of non-empty comments. '''
    params = get_validated_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

    signature = params['signature'][0]

    data = {}
    data['query'] = {
        'total': 0,
        'total_count': 0,
        'total_pages': 0
    }

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']

    data['params'] = current_query.copy()

    try:
        current_page = int(request.GET.get('page', 1))
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    if current_page <= 0:
        current_page = 1

    results_per_page = 50
    data['current_page'] = current_page
    data['results_offset'] = results_per_page * (current_page - 1)

    params['signature'] = '=' + signature
    params['user_comments'] = '!__null__'
    params['_columns'] = ['uuid', 'user_comments', 'date', 'useragent_locale']
    params['_results_number'] = results_per_page
    params['_results_offset'] = data['results_offset']
    params['_facets'] = []  # We don't need no facets.

    data['current_url'] = '%s?%s' % (
        reverse('signature:signature_report'),
        current_query.urlencode()
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except models.BadStatusCodeError, e:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest('<ul><li>%s</li></ul>' % e)

    search_results['total_pages'] = int(
        math.ceil(
            search_results['total'] / float(results_per_page)
        )
    )
    search_results['total_count'] = search_results['total']

    data['query'] = search_results

    return render(request, 'signature/signature_comments.html', data)


@waffle_switch('signature-report')
@utils.json_view
def signature_graph_data(request, channel):
    '''Return data for the graph of crashes/ADU against build date'''
    params = get_validated_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

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

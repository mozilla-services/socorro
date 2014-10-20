import math

from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import render

from waffle.decorators import waffle_switch

from crashstats.api.views import has_permissions
from crashstats.crashstats import models
from crashstats.crashstats.views import pass_default_context
from crashstats.supersearch.models import (
    SuperSearchUnredacted,
    SuperSearchFields
)
from crashstats.supersearch.views import (
    get_allowed_fields,
    get_params
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

    data['aggregates'] = []
    if aggregation in search_results['facets']:
        data['aggregates'] = search_results['facets'][aggregation]

    data['total_count'] = search_results['total']

    return render(request, 'signature/signature_aggregation.html', data)


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

import math

from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import render

from waffle.decorators import waffle_switch

from crashstats.crashstats import models
from crashstats.crashstats.views import pass_default_context
from crashstats.supersearch.models import SuperSearchUnredacted
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


@waffle_switch('signature-report')
@pass_default_context
def signature_report(request, signature, default_context=None):
    context = default_context
    context['signature'] = signature

    return render(request, 'signature/signature_report.html', context)


@waffle_switch('signature-report')
def signature_reports(request, signature):
    '''Return the results of a search. '''
    params = get_params(request)
    if isinstance(params, http.HttpResponseBadRequest):
        # There was an error in the form, let's return it.
        return params

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
        reverse('signature:signature_report', args=(signature,)),
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
def signature_aggregation(request, signature, aggregation):
    pass

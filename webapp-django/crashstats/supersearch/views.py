import datetime
import json
import math
from collections import defaultdict

import isodate

from django import http
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.utils import timezone

from ratelimit.decorators import ratelimit

from waffle.decorators import waffle_switch

from socorrolib.lib import BadArgumentError

from crashstats.base.utils import render_exception
from crashstats.api.views import has_permissions
from crashstats.crashstats import models, utils
from crashstats.crashstats.views import pass_default_context

from . import forms
from .form_fields import split_on_operator
from .models import Query, SuperSearchFields, SuperSearchUnredacted


DEFAULT_COLUMNS = (
    'date',
    'signature',
    'product',
    'version',
    'build_id',
    'platform',
)

DEFAULT_FACETS = (
    'signature',
)

DEFAULT_SORT = (
    '-date',
)

# Facetting on those fields doesn't provide useful information.
EXCLUDED_FIELDS_FROM_FACETS = (
    'date',
    'dump',
)


class ValidationError(Exception):
    pass


def get_allowed_fields(user):
    return tuple(
        x['name']
        for x in SuperSearchFields().get().values()
        if x['is_exposed'] and has_permissions(user, x['permissions_needed'])
    )


def get_supersearch_form(request):
    platforms = models.Platforms().get()
    product_versions = models.ProductVersions().get()['hits']

    all_fields = SuperSearchFields().get()

    form = forms.SearchForm(
        all_fields,
        product_versions,
        platforms,
        request.user,
        request.GET
    )
    return form


def get_params(request):
    form = get_supersearch_form(request)

    if not form.is_valid():
        raise ValidationError(str(form.errors))

    params = {}
    for key in form.cleaned_data:
        if hasattr(form.fields[key], 'prefixed_value'):
            value = form.fields[key].prefixed_value
        else:
            value = form.cleaned_data[key]

        params[key] = value

    params['_sort'] = request.GET.getlist('_sort')
    params['_facets'] = request.GET.getlist('_facets', DEFAULT_FACETS)
    params['_columns'] = request.GET.getlist('_columns') or DEFAULT_COLUMNS

    allowed_fields = get_allowed_fields(request.user)

    # Make sure only allowed fields are used.
    params['_sort'] = [
        x for x in params['_sort']
        if x in allowed_fields or
        (x.startswith('-') and x[1:] in allowed_fields)
    ]
    params['_facets'] = [
        x for x in params['_facets'] if x in allowed_fields
    ]
    params['_columns'] = [
        x for x in params['_columns'] if x in allowed_fields
    ]

    # The uuid is always displayed in the UI so we need to make sure it is
    # always returned by the model.
    if 'uuid' not in params['_columns']:
        params['_columns'].append('uuid')

    return params


@ratelimit(
    key='ip',
    rate=utils.ratelimit_rate,
    method=ratelimit.ALL,
    block=True
)
@pass_default_context
def search(request, default_context=None):
    allowed_fields = get_allowed_fields(request.user)

    context = default_context
    context['possible_facets'] = [
        {'id': x, 'text': x.replace('_', ' ')} for x in allowed_fields
        if x not in EXCLUDED_FIELDS_FROM_FACETS
    ]

    context['possible_columns'] = [
        {'id': x, 'text': x.replace('_', ' ')} for x in allowed_fields
    ]

    context['sort'] = request.GET.getlist('_sort', DEFAULT_SORT)
    context['facets'] = request.GET.getlist('_facets', DEFAULT_FACETS)
    context['columns'] = request.GET.getlist('_columns') or DEFAULT_COLUMNS

    # Fields data for the simple search UI.
    form = get_supersearch_form(request)
    context['simple_search_data'] = [
        # field name, options, placeholder values
        (x, form.fields[x].choices, [x[1] for x in form.fields[x].choices[:3]])
        for x in settings.SIMPLE_SEARCH_FIELDS
    ]

    return render(request, 'supersearch/search.html', context)


@ratelimit(
    key='ip',
    rate=utils.ratelimit_rate,
    method=ratelimit.ALL,
    block=True
)
def search_results(request):
    '''Return the results of a search. '''
    try:
        params = get_params(request)
    except ValidationError as e:
        # There was an error in the form, let's return it.
        return http.HttpResponseBadRequest(str(e))

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

    if '_columns' in context['params']:
        del context['params']['_columns']

    if '_facets' in context['params']:
        del context['params']['_facets']

    context['sort'] = list(params['_sort'])

    # Copy the list of columns so that they can differ.
    context['columns'] = list(params['_columns'])

    # The `uuid` field is a special case, it is always displayed in the first
    # column of the table. Hence we do not want to show it again in the
    # auto-generated list of columns, so we remove it from the list of
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

    params['_results_number'] = results_per_page
    params['_results_offset'] = context['results_offset']

    context['current_url'] = '%s?%s' % (
        reverse('supersearch.search'),
        current_query.urlencode()
    )

    api = SuperSearchUnredacted()
    try:
        search_results = api.get(**params)
    except BadArgumentError as exception:
        # We need to return the error message in some HTML form for jQuery to
        # pick it up.
        return http.HttpResponseBadRequest(
            render_exception(exception)
        )

    if 'signature' in search_results['facets']:
        # Bugs for each signature
        signatures = [h['term'] for h in search_results['facets']['signature']]

        if signatures:
            bugs = defaultdict(list)
            bugs_api = models.Bugs()
            for b in bugs_api.get(signatures=signatures)['hits']:
                bugs[b['signature']].append(b['id'])

            for hit in search_results['facets']['signature']:
                sig = hit['term']
                if sig in bugs:
                    if 'bugs' in hit:
                        hit['bugs'].extend(bugs[sig])
                    else:
                        hit['bugs'] = bugs[sig]

    search_results['total_pages'] = int(math.ceil(
        search_results['total'] / float(results_per_page)))
    search_results['total_count'] = search_results['total']

    context['query'] = search_results

    return render(request, 'supersearch/search_results.html', context)


@utils.json_view
def search_fields(request):
    '''Return the JSON document describing the fields used by the JavaScript
    dynamic_form library. '''
    form = get_supersearch_form(request)

    exclude = request.GET.getlist('exclude')
    return form.get_fields_list(exclude=exclude)


def get_report_list_parameters(source):
    '''Return a list of parameters that are compatible with the report/list
    page. This is not ideal and cannot be fully compatible because we have
    operators in supersearch and not in report/list.
    '''
    params = {}

    for key, value in source.items():
        if not value:
            continue

        if key in (
            'hang_type',
            'platform',
            'process_type',
            'product',
            'reason',
        ):
            params[key] = value

        elif key == 'release_channel':
            params['release_channels'] = value

        elif key == 'build_id':
            params['build_id'] = []
            for build in value:
                operator, build = split_on_operator(build)
                if operator:
                    # The report/list/ page is unable to understand operators.
                    continue
                params['build_id'].append(build)

            if not params['build_id']:
                del params['build_id']

        elif key == 'version':
            if 'product' in source:
                params['version'] = []
                for p in source['product']:
                    for v in value:
                        params['version'].append('%s:%s' % (p, v))

        elif key == 'date':
            lower = upper = up_ope = None

            for dt in value:
                operator, dt = split_on_operator(dt)
                dt = isodate.parse_datetime(dt)

                if lower is None or upper is None:
                    lower = upper = dt
                    up_ope = operator
                elif lower > dt:
                    lower = dt
                elif upper < dt:
                    upper = dt
                    up_ope = operator

            def to_hours(delta):
                return delta.days * 24 + delta.seconds / 3600

            if lower == upper:
                # there's only one date
                if up_ope is not None and '<' in up_ope:
                    params['date'] = upper
                else:
                    params['date'] = (
                        timezone.now()
                    )
                    params['range_value'] = to_hours(params['date'] - upper)
                    params['range_unit'] = 'hours'
            else:
                params['date'] = upper
                params['range_value'] = to_hours(upper - lower)
                params['range_unit'] = 'hours'

            params['date'] = params['date'].strftime('%Y-%m-%d %H:%M:%S')

    return params


@waffle_switch('!supersearch-custom-query-disabled')
@permission_required('crashstats.run_custom_queries')
@pass_default_context
def search_custom(request, default_context=None):
    '''Return the basic search page, without any result. '''
    error = None
    query = None

    try:
        params = get_params(request)
    except ValidationError as e:
        # There was an error in the form, but we want to do the default
        # behavior and just display an error message.
        error = str(e)
    else:
        # Get the JSON query that supersearch generates and show it.
        params['_return_query'] = 'true'
        api = SuperSearchUnredacted()
        try:
            query = api.get(**params)
        except BadArgumentError as e:
            error = e

    schema = settings.ELASTICSEARCH_INDEX_SCHEMA
    now = timezone.now()

    possible_indices = []
    for i in range(26):
        index = (now - datetime.timedelta(weeks=i)).strftime(schema)
        possible_indices.append({'id': index, 'text': index})

    context = default_context
    context['elasticsearch_indices'] = possible_indices

    if query:
        context['query'] = json.dumps(query['query'])
        context['indices'] = ','.join(query['indices'])

    context['error'] = error

    return render(request, 'supersearch/search_custom.html', context)


@waffle_switch('!supersearch-custom-query-disabled')
@permission_required('crashstats.run_custom_queries')
@require_POST
@utils.json_view
def search_query(request):
    form = forms.QueryForm(request.POST)
    if not form.is_valid():
        return http.HttpResponseBadRequest(form.errors)

    api = Query()
    try:
        results = api.get(
            query=form.cleaned_data['query'],
            indices=form.cleaned_data['indices']
        )
    except models.BadStatusCodeError as e:
        return http.HttpResponseBadRequest(e.message)

    return results

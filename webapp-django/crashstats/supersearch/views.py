import isodate
import datetime
import math
import urllib
from collections import defaultdict

from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import render

from waffle.decorators import waffle_switch

from crashstats.crashstats import models
from crashstats.crashstats import utils
from crashstats.crashstats.views import pass_default_context
from . import forms
from .form_fields import split_on_operator
from .models import SuperSearch


ALL_POSSIBLE_FIELDS = (
    'address',
    'app_notes',
    'build_id',
    'cpu_info',
    'cpu_name',
    'date',
    'distributor',
    'distributor_version',
    'flash_version',
    'install_age',
    'java_stack_trace',
    'last_crash',
    'platform',
    'platform_version',
    'plugin_name',
    'plugin_filename',
    'plugin_version',
    'processor_notes',
    'product',
    'productid',
    'reason',
    'release_channel',
    'signature',
    'topmost_filenames',
    'uptime',
    'user_comments',
    'version',
    'winsock_lsp',
)

ADMIN_RESTRICTED_FIELDS = (
    'email',
    'url',
)

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

# Facetting on those fields doesn't provide useful information.
EXCLUDED_FIELDS_FROM_FACETS = (
    'date',
)


@waffle_switch('supersearch-all')
@pass_default_context
def search(request, default_context=None):
    allowed_fields = ALL_POSSIBLE_FIELDS
    if request.user.is_authenticated():
        allowed_fields += ADMIN_RESTRICTED_FIELDS

    context = default_context
    context['possible_facets'] = [
        {'id': x, 'text': x.replace('_', ' ')} for x in allowed_fields
        if x not in EXCLUDED_FIELDS_FROM_FACETS
    ]

    context['possible_columns'] = [
        {'id': x, 'text': x.replace('_', ' ')} for x in allowed_fields
    ]

    context['facets'] = request.GET.getlist('_facets') or DEFAULT_FACETS
    context['columns'] = request.GET.getlist('_columns') or DEFAULT_COLUMNS

    return render(request, 'supersearch/search.html', context)


@waffle_switch('supersearch-all')
def search_results(request):
    products = models.ProductsVersions().get()
    versions = models.CurrentVersions().get()
    platforms = models.Platforms().get()

    form = forms.SearchForm(
        products,
        versions,
        platforms,
        request.user.is_authenticated(),
        request.GET
    )

    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    params = {}
    for key in form.cleaned_data:
        if hasattr(form.fields[key], 'prefixed_value'):
            value = form.fields[key].prefixed_value
        else:
            value = form.cleaned_data[key]

        params[key] = value

    data = {}
    data['query'] = {
        'total': 0,
        'total_count': 0,
        'total_pages': 0
    }

    allowed_fields = ALL_POSSIBLE_FIELDS
    if request.user.is_authenticated():
        allowed_fields += ADMIN_RESTRICTED_FIELDS

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']

    data['params'] = current_query.copy()

    if '_columns' in data['params']:
        del data['params']['_columns']

    if '_facets' in params:
        del data['params']['_facets']

    params['_facets'] = request.GET.getlist('_facets') or DEFAULT_FACETS
    data['columns'] = request.GET.getlist('_columns') or DEFAULT_COLUMNS

    # Make sure only allowed fields are used
    params['_facets'] = [
        x for x in params['_facets'] if x in allowed_fields
    ]
    data['columns'] = [
        x for x in data['columns'] if x in allowed_fields
    ]

    try:
        data['current_page'] = int(request.GET.get('page', 1))
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    results_per_page = 50
    data['results_offset'] = results_per_page * (data['current_page'] - 1)

    params['_results_number'] = results_per_page
    params['_results_offset'] = data['results_offset']

    data['current_url'] = '%s?%s' % (
        reverse('supersearch.search'),
        current_query.urlencode()
    )

    api = SuperSearch()
    search_results = api.get(**params)

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

    data['query'] = search_results
    data['report_list_query_string'] = urllib.urlencode(
        utils.sanitize_dict(
            get_report_list_parameters(params)
        ),
        True
    )

    return render(request, 'supersearch/search_results.html', data)


@waffle_switch('supersearch-all')
@utils.json_view
def search_fields(request):
    products = models.ProductsVersions().get()
    versions = models.CurrentVersions().get()
    platforms = models.Platforms().get()

    form = forms.SearchForm(
        products,
        versions,
        platforms,
        request.user.is_authenticated(),
        request.GET
    )
    return form.get_fields_list()


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
                    params['date'] = datetime.datetime.utcnow()
                    params['range_value'] = to_hours(params['date'] - upper)
                    params['range_unit'] = 'hours'
            else:
                params['date'] = upper
                params['range_value'] = to_hours(upper - lower)
                params['range_unit'] = 'hours'

    return params

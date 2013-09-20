import functools
import math
import urllib
from collections import defaultdict

from django import http
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect

from waffle.decorators import waffle_switch

from crashstats.crashstats import models
from crashstats.crashstats import utils
from crashstats.crashstats.views import pass_default_context
from . import forms
from .models import SuperSearch


ALL_POSSIBLE_FIELDS = [
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
]

ADMIN_RESTRICTED_FIELDS = [
    'email',
    'url',
]

DEFAULT_COLUMNS = [
    'date',
    'signature',
    'product',
    'version',
    'build_id',
    'platform',
]

DEFAULT_FACETS = [
    'signature',
]

# Facetting on those fields doesn't provide useful information.
EXCLUDED_FIELDS_FROM_FACETS = [
    'date',
]


def admin_required(view_func):
    @functools.wraps(view_func)
    def inner(request, *args, **kwargs):
        if not request.user.is_authenticated():
            messages.error(
                request,
                'You must be logged in to use the new search UI.'
            )
            return redirect(reverse('crashstats.query'))
        return view_func(request, *args, **kwargs)
    return inner


@waffle_switch('supersearch-all')
@pass_default_context
def search(request, default_context=None):
    context = default_context
    context['possible_facets'] = [
        {'id': x, 'text': x.replace('_', ' ')} for x in ALL_POSSIBLE_FIELDS
        if x not in EXCLUDED_FIELDS_FROM_FACETS
    ]

    context['possible_columns'] = [
        {'id': x, 'text': x.replace('_', ' ')} for x in ALL_POSSIBLE_FIELDS
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

    if '_columns' in current_query:
        del current_query['_columns']

    if '_facets' in current_query:
        del current_query['_facets']

    data['params'] = current_query

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
        utils.sanitize_dict(current_query),
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

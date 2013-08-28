import functools
import isodate
import math
import urllib

from django import http
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect

from waffle.decorators import waffle_switch

from crashstats.crashstats import models
from crashstats.crashstats import utils
from crashstats.crashstats.views import pass_default_context
from crashstats.supersearch import forms
from crashstats.supersearch.models import SuperSearch


DEFAULT_FIELDS = [
    'date_processed',
    'signature',
    'product',
    'version',
    'build',
    'platform',
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
@admin_required
@pass_default_context
def search(request, default_context=None):
    return render(request, 'supersearch/search.html', default_context)


@waffle_switch('supersearch-all')
@admin_required
def search_results(request):
    products = models.ProductsVersions().get()
    versions = models.CurrentVersions().get()
    platforms = models.Platforms().get()

    form = forms.SearchForm(products, versions, platforms, request.GET)

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

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']

    fields = DEFAULT_FIELDS
    if '_fields' in request.GET:
        user_fields = request.GET.get('_fields')
        if not isinstance(user_fields, (tuple, list)):
            user_fields = [user_fields]
        fields = user_fields or fields
        del current_query['_fields']

    data['params'] = current_query
    data['fields'] = fields

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

    for i, crash in enumerate(search_results['hits']):
        search_results['hits'][i]['date_processed'] = isodate.parse_datetime(
            crash['date_processed']
        ).strftime('%b %d, %Y %H:%M')

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
@admin_required
@utils.json_view
def search_fields(request):
    products = models.ProductsVersions().get()
    versions = models.CurrentVersions().get()
    platforms = models.Platforms().get()

    form = forms.SearchForm(products, versions, platforms, request.GET)
    return form.get_fields_list()

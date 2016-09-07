import copy
import json
import datetime
import hashlib
import math
import urllib
import gzip
from collections import defaultdict
from operator import itemgetter
from io import BytesIO

import isoweek

from django import http
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import urlquote

from session_csrf import anonymous_csrf

from . import forms, models, utils
from .decorators import check_days_parameter, pass_default_context

from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchUnredacted
)


# To prevent running in to a known Python bug
# (http://bugs.python.org/issue7980)
# we, here at "import time" (as opposed to run time) make use of time.strptime
# at least once
datetime.datetime.strptime('2013-07-15 10:00:00', '%Y-%m-%d %H:%M:%S')


GRAPHICS_REPORT_HEADER = (
    'signature',
    'url',
    'crash_id',
    'client_crash_date',
    'date_processed',
    'last_crash',
    'product',
    'version',
    'build',
    'branch',
    'os_name',
    'os_version',
    'cpu_info',
    'address',
    'bug_list',
    'user_comments',
    'uptime_seconds',
    'email',
    'adu_count',
    'topmost_filenames',
    'addons_checked',
    'flash_version',
    'hangid',
    'reason',
    'process_type',
    'app_notes',
    'install_age',
    'duplicate_of',
    'release_channel',
    'productid',
)


def make_correlations_count_cache_key(product, version, platform, signature):
    return 'total_correlations-' + hashlib.md5(
        (product + version + platform + signature).encode('utf-8')
    ).hexdigest()


def ratelimit_blocked(request, exception):
    # http://tools.ietf.org/html/rfc6585#page-3
    status = 429

    # If the request is an AJAX on, we return a plain short string.
    # Also, if the request is coming from something like curl, it will
    # send the header `Accept: */*`. But if you take the same URL and open
    # it in the browser it'll look something like:
    # `Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`
    if (
        request.is_ajax() or
        'text/html' not in request.META.get('HTTP_ACCEPT', '')
    ):
        # Return a super spartan message.
        # We could also do something like `{"error": "Too Many Requests"}`
        return http.HttpResponse(
            'Too Many Requests',
            status=status,
            content_type='text/plain'
        )

    return render(request, 'crashstats/ratelimit_blocked.html', status=status)


def robots_txt(request):
    return http.HttpResponse(
        'User-agent: *\n'
        '%s: /' % ('Allow' if settings.ENGAGE_ROBOTS else 'Disallow'),
        content_type='text/plain',
    )


def build_data_object_for_adu_graphs(start_date, end_date, response_items,
                                     report_type='by_version',
                                     code_to_name=None):
    count = len(response_items)
    graph_data = {
        'startDate': start_date,
        'endDate': end_date,
        'count': count,
        'labels': [],
    }

    for count, product_version in enumerate(sorted(response_items,
                                                   reverse=True),
                                            start=1):
        graph_data['ratio%s' % count] = []
        label = product_version.split(':')[-1]
        # the `product_version` can be something like `firefox:23.0:win`
        # so use code_to_name so we can turn it into a nice looking label
        if code_to_name:
            label = code_to_name.get(label, label)
        graph_data['labels'].append(label)

        for day in sorted(response_items[product_version]):
            ratio = response_items[product_version][day]['crash_hadu']
            t = day
            graph_data['ratio%s' % count].append([t, ratio])

    return graph_data


def build_id_to_date(build_id):
    yyyymmdd = str(build_id)[:8]
    return '{}-{}-{}'.format(
        yyyymmdd[:4],
        yyyymmdd[4:6],
        yyyymmdd[6:8],
    )


def build_data_object_for_crashes_per_day_graph(
    start_date, end_date, facets, adi_by_term, date_range_type
):
    if date_range_type == 'build':
        histogram = facets['histogram_build_id']
    else:
        histogram = facets['histogram_date']
    groups = facets['version']
    count = len(groups)
    graph_data = {
        'startDate': start_date,
        'endDate': end_date,
        'count': count,
        'labels': [],
        'ratios': [],
    }

    groups = sorted(groups, key=itemgetter('term'), reverse=True)
    for index, group in enumerate(groups, start=1):
        ratios = []
        term = group['term']

        graph_data['labels'].append(term)

        for block in histogram:
            if date_range_type == 'build':
                # the build_id will be something like 20150810122907
                # which we need to convert to '2015-08-10'
                date = build_id_to_date(block['term'])
            else:
                date = block['term'].split('T')[0]
            count = 0
            for cluster in block['facets']['version']:
                if term == cluster['term']:
                    count += cluster['count']

            total = 0
            throttle = 1.0
            if term in adi_by_term:
                if date in adi_by_term[term]:
                    total, throttle = adi_by_term[term][date]

            if total:
                ratio = round(100.0 * count / total / throttle, 3)
            else:
                ratio = 0.0

            ratios.append([date, ratio])
        graph_data['ratios'].append(ratios)

    return graph_data


def _get_crashes_per_day_with_adu(
    params, start_date, end_date, platforms, _date_range_type
):
    api = SuperSearchUnredacted()
    results = api.get(**params)

    platforms_api = models.Platforms()
    platforms = platforms_api.get()

    # now get the ADI for these product versions
    api = models.ADI()
    adi_counts = api.get(
        product=params['product'],
        versions=params['version'],
        start_date=start_date,
        end_date=end_date,
        platforms=[x['name'] for x in platforms if x.get('display')],
    )

    api = models.ProductBuildTypes()
    product_build_types = api.get(product=params['product'])['hits']

    # This `adi_counts` is a list of dicts that looks like this:
    #    {
    #       'adi_count': 123,
    #       'date': '2015-08-15',
    #       'version': '40.0.2'
    #       'build_type': 'beta',
    #    }
    # We need to turn this around so that it's like this:
    #   {
    #       '40.0.2': {
    #           '2015-08-15': [123, 1.0],
    #            ...
    #       },
    #       ...
    #   }
    # So it can easily be looked up how many counts there are per
    # version per date.
    #
    # Note!! that the 1.0 in the example above is the throttle value
    # for this build_type. We got that from the ProductBuildTypes API.
    adi_by_version = {}

    # If any of the versions end with a 'b' we want to collect
    # and group them together under one.
    # I.e. if we have adi count of '42.0b1':123 and '42.0b2':345
    # then we want to combine that to just '42.0b':123+345

    beta_versions = [x for x in params['version'] if x.endswith('b')]

    def get_parent_version(ver):
        try:
            return [x for x in beta_versions if ver.startswith(x)][0]
        except IndexError:
            return None

    def add_version_to_adi(version, count, date, throttle):
        if version not in adi_by_version:
            adi_by_version[version] = {}

        try:
            before = adi_by_version[version][date][0]
        except KeyError:
            before = 0
        adi_by_version[version][date] = [count + before, throttle]

    for group in adi_counts['hits']:
        version = group['version']
        # Make this a string so it can be paired with the facets 'term'
        # key which is also a date in ISO format.
        date = group['date'].isoformat()
        build_type = group['build_type']
        count = group['adi_count']
        throttle = product_build_types[build_type]

        # If this version was requested, add it to the data structure.
        if version in params['version']:
            add_version_to_adi(version, count, date, throttle)

        # If this version is part of a beta, add it to the data structure.
        parent_version = get_parent_version(version)
        if parent_version is not None:
            version = parent_version
            add_version_to_adi(version, count, date, throttle)

    # We might have queried for aggregates for version ['19.0a1', '18.0b']
    # but SuperSearch will give us facets for versions:
    # ['19.0a1', '18.0b1', '18.0b2', '18.0b3']
    # The facets look something like this:
    #        {
    #            'histogram_date': [
    #                {
    #                    'count': 1234,
    #                    'facets': [
    #                        {'count': 201, 'term': '19.0a1'},
    #                        {'count': 196, 'term': '18.0b1'},
    #                        {'count': 309, 'term': '18.0b2'},
    #                        {'count': 991, 'term': '18.0b3'},
    #                    ],
    #                    'term': '2015-01-10T00:00:00'
    #                },
    #                ...
    #
    #            'version': [
    #                {'count': 45234, 'term': '19.0a1'},
    #                {'count': 39001, 'term': '18.0b1'},
    #                {'count': 56123, 'term': '18.0b2'},
    #                {'count': 90133, 'term': '18.0b3'},
    #
    # Our job is to rewrite that so it looks like this:
    #        {
    #            'histogram_date': [
    #                {
    #                    'count': 1234,
    #                    'facets': [
    #                        {'count': 201, 'term': '19.0a1'},
    #                        {'count': 196+309+991, 'term': '18.0b'},
    #                    ],
    #                    'term': '2015-01-10T00:00:00'
    #                },
    #                ...
    #
    #            'version': [
    #                {'count': 45234, 'term': '19.0a1'},
    #                {'count': 39001+56123+90133, 'term': '18.0b'},
    #

    histogram = results['facets']['histogram_date']
    for date_cluster in histogram:
        parent_totals = defaultdict(int)

        for facet_cluster in list(date_cluster['facets']['version']):
            version = facet_cluster['term']
            parent_version = get_parent_version(version)
            if parent_version is not None:
                parent_totals[parent_version] += facet_cluster['count']
            if version not in params['version']:
                date_cluster['facets']['version'].remove(facet_cluster)
        for version in parent_totals:
            date_cluster['facets']['version'].append({
                'count': parent_totals[version],
                'term': version
            })

    parent_totals = defaultdict(int)
    for facet_cluster in list(results['facets']['version']):
        version = facet_cluster['term']
        parent_version = get_parent_version(version)
        if parent_version is not None:
            parent_totals[parent_version] += facet_cluster['count']
        if version not in params['version']:
            results['facets']['version'].remove(facet_cluster)
    for version in parent_totals:
        results['facets']['version'].append({
            'count': parent_totals[version],
            'term': version,
        })

    graph_data = {}
    graph_data = build_data_object_for_crashes_per_day_graph(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        results['facets'],
        adi_by_version,
        _date_range_type
    )
    graph_data['product_versions'] = get_product_versions_for_crashes_per_day(
        results['facets'],
        params['product'],
    )

    return graph_data, results, adi_by_version


def build_data_object_for_crash_reports(response_items):

    crash_reports = []

    for count, product_version in enumerate(sorted(response_items,
                                                   reverse=True)):
        prod_ver = {}
        prod_ver['product'] = product_version.split(':')[0]
        prod_ver['version'] = product_version.split(':')[1]
        crash_reports.append(prod_ver)

    return crash_reports


def get_product_versions_for_crashes_per_day(facets, product):
    versions = facets['version']
    versions = sorted(versions, key=itemgetter('term'), reverse=True)
    return [
        {'product': product, 'version': group['term']}
        for group in versions
    ]


def get_all_nightlies(context):
    nightlies_only = settings.NIGHTLY_RELEASE_TYPES

    versions = {}
    for product, product_versions in context['active_versions'].items():
        versions[product] = []
        for version in product_versions:
            rel_release = version['build_type'].lower()
            if rel_release in [x.lower() for x in nightlies_only]:
                versions[product].append(version['version'])

    return versions


def get_all_nightlies_for_product(context, product):
    nightlies_only = settings.NIGHTLY_RELEASE_TYPES
    versions = []
    for version in context['active_versions'].get(product, []):
        rel_release = version['build_type'].lower()
        if rel_release in [x.lower() for x in nightlies_only]:
            versions.append(version['version'])

    return versions


def get_latest_nightly(context, product):
    version = None
    for version in context['active_versions'][product]:
        build_type = version['build_type']
        if build_type.lower() == 'nightly' and version['is_featured']:
            version = version['version']
            break

    if version is None:
        # We did not find a featured Nightly, let's simply use the latest
        for version in context['active_versions'].get(product, []):
            if version['build_type'].lower() == 'nightly':
                version = version['version']
                break

    return version


def get_build_type_for_product_versions(product_versions):
    """product_versions is a list that looks something like this:
      ['Firefox:47.0a1']
    Return the build type on matches
    """
    api = models.ProductVersions()
    for product_version in product_versions:
        product, version = product_version.split(':')
        for hit in api.get(product=product, version=version)['hits']:
            return hit['build_type']


def get_timedelta_from_value_and_unit(value, unit):
    if unit == 'weeks':
        date_delta = datetime.timedelta(weeks=value)
    elif unit == 'days':
        date_delta = datetime.timedelta(days=value)
    elif unit == 'hours':
        date_delta = datetime.timedelta(hours=value)
    else:
        date_delta = datetime.timedelta(weeks=1)

    return date_delta


def get_super_search_style_params(**kwargs):
    if 'signature' not in kwargs:
        raise ValueError('"signature" is a mandatory parameter')

    params = {
        'signature': kwargs['signature'],
        'product': kwargs.get('product'),
        'platform': kwargs.get('platform'),
        'date': [],
        'version': [],
    }

    if kwargs.get('start_date'):
        start_date = kwargs.get('start_date').isoformat()
        params['date'].append('>=' + start_date)

    if kwargs.get('end_date'):
        end_date = kwargs.get('end_date').isoformat()
        params['date'].append('<' + end_date)

    if kwargs.get('version'):
        versions = kwargs.get('version')
        if not isinstance(versions, (tuple, list)):
            versions = [versions]

        for version in versions:
            assert ':' in version
            number = version.split(':')[1]
            params['version'].append(number)

    return params


@pass_default_context
@anonymous_csrf
@check_days_parameter([1, 3, 7, 14, 28], default=7)
def topcrasher(request, product=None, versions=None, date_range_type=None,
               crash_type=None, os_name=None, result_count='50', days=None,
               possible_days=None, default_context=None):
    context = default_context or {}

    if product not in context['active_versions']:
        raise http.Http404('Unrecognized product')

    date_range_type = date_range_type or 'report'

    if not versions:
        # :(
        # simulate what the nav.js does which is to take the latest version
        # for this product.
        for pv in context['active_versions'][product]:
            if pv['is_featured']:
                url = reverse('crashstats:topcrasher',
                              kwargs=dict(product=product,
                                          versions=pv['version']))
                return redirect(url)
        raise NotImplementedError("Not sure what's supposed to happen here")
    else:
        versions = versions.split(';')

    if len(versions) == 1:
        context['version'] = versions[0]

    product_versions = context['active_versions'][product]
    if context['version'] not in [x['version'] for x in product_versions]:
        raise http.Http404('Unrecognized version')

    context['has_builds'] = False
    for productversion in product_versions:
        if productversion['version'] == context['version']:
            if productversion['has_builds']:
                context['has_builds'] = True

    end_date = datetime.datetime.utcnow()

    if crash_type not in ['all', 'browser', 'plugin', 'content']:
        crash_type = 'browser'

    context['crash_type'] = crash_type

    os_api = models.Platforms()
    operating_systems = os_api.get()
    if os_name not in (os_['name'] for os_ in operating_systems):
        os_name = None

    context['os_name'] = os_name

    # set the result counts filter in the context to use in
    # the template. This way we avoid hardcoding it twice and
    # have it defined in one common location.
    context['result_counts'] = settings.TCBS_RESULT_COUNTS
    if result_count not in context['result_counts']:
        result_count = settings.TCBS_RESULT_COUNTS[0]

    context['result_count'] = result_count

    api = models.TCBS()
    tcbs = api.get(
        product=product,
        version=context['version'],
        crash_type=crash_type,
        end_date=end_date.date(),
        date_range_type=date_range_type,
        duration=(days * 24),
        limit=result_count,
        os=os_name
    )

    context['numberOfCrashes'] = 0
    signatures = []
    for crash in tcbs['crashes'][:int(result_count)]:
        signatures.append(crash['signature'])
        context['numberOfCrashes'] += crash['count']

    bugs = defaultdict(list)
    api = models.Bugs()
    if signatures:
        for b in api.get(signatures=signatures)['hits']:
            bugs[b['signature']].append(b['id'])

    for crash in tcbs['crashes']:
        crash_counts = []
        # Due to the inconsistencies of OS usage and naming of
        # codes and props for operating systems the hacky bit below
        # is required. Socorro and the world will be a better place
        # once https://bugzilla.mozilla.org/show_bug.cgi?id=790642 lands.
        os_short_name_binding = {'lin': 'linux'}
        for operating_system in operating_systems:
            if operating_system['name'] == 'Unknown':
                # not applicable in this context
                continue
            os_code = operating_system['code'][0:3].lower()
            key = '%s_count' % os_short_name_binding.get(os_code, os_code)
            crash_counts.append([crash[key], operating_system['name']])

        crash['correlation_os'] = max(crash_counts)[1]
        sig = crash['signature']
        if sig in bugs:
            if 'bugs' in crash:
                crash['bugs'].extend(bugs[sig])
            else:
                crash['bugs'] = bugs[sig]
        if 'bugs' in crash:
            crash['bugs'].sort(reverse=True)

    context['tcbs'] = tcbs
    context['report'] = 'topcrasher'
    context['days'] = days
    context['possible_days'] = possible_days
    context['total_crashing_signatures'] = len(signatures)
    context['date_range_type'] = date_range_type

    if request.GET.get('format') == 'csv':
        return _render_topcrasher_csv(request, context, product)

    return render(request, 'crashstats/topcrasher.html', context)


def _render_topcrasher_csv(request, context, product):
    response = http.HttpResponse(content_type='text/csv')
    filedate = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    response['Content-Disposition'] = (
        'attachment; filename="%s_%s_%s.csv"' % (
            product,
            context['version'],
            filedate
        )
    )
    writer = utils.UnicodeWriter(response)
    writer.writerow(['Rank',
                     'Change in Rank',
                     'Percentage of All Crashes',
                     'Previous Percentage',
                     'Signature',
                     'Total',
                     'Win',
                     'Mac',
                     'Linux',
                     'Is Garbage Collecting',
                     'Version Count',
                     'Versions'])
    for crash in context['tcbs']['crashes']:

        writer.writerow([crash.get('currentRank', '') + 1,
                         crash.get('changeInRank', ''),
                         crash.get('percentOfTotal', ''),
                         crash.get('previousPercentOfTotal', ''),
                         crash.get('signature', ''),
                         crash.get('count', ''),
                         crash.get('win_count', ''),
                         crash.get('mac_count', ''),
                         crash.get('linux_count', ''),
                         crash.get('is_gc_count', ''),
                         crash.get('versions_count', ''),
                         crash.get('versions', '')])

    return response


@pass_default_context
def daily(request, default_context=None):
    context = default_context or {}

    # legacy fix
    if 'v[]' in request.GET or 'os[]' in request.GET:
        new_url = (request.build_absolute_uri()
                   .replace('v[]', 'v')
                   .replace('os[]', 'os'))
        return redirect(new_url, permanent=True)

    context['products'] = context['active_versions'].keys()

    platforms_api = models.Platforms()
    platforms = platforms_api.get()

    form_class = forms.DailyFormByVersion

    date_range_types = ['report', 'build']
    hang_types = ['any', 'crash', 'hang-p']

    form = form_class(
        context['active_versions'],
        platforms,
        data=request.GET,
        date_range_types=date_range_types,
        hang_types=hang_types,
    )
    if form.is_valid():
        params = form.cleaned_data
        params['product'] = params.pop('p')
        params['versions'] = sorted(list(set(params.pop('v'))), reverse=True)
        try:
            params['os_names'] = params.pop('os')
        except KeyError:
            params['os_names'] = None
    else:
        return http.HttpResponseBadRequest(str(form.errors))

    if len(params['versions']) > 0:
        context['version'] = params['versions'][0]

    context['product'] = params['product']

    if not params['versions']:
        # need to pick the default featured ones
        params['versions'] = []
        for pv in context['active_versions'][context['product']]:
            if pv['is_featured']:
                params['versions'].append(pv['version'])

    context['available_versions'] = []
    for version in context['active_versions'][params['product']]:
        context['available_versions'].append(version['version'])

    if not params.get('os_names'):
        params['os_names'] = [x['name'] for x in platforms if x.get('display')]

    context['os_names'] = params.get('os_names')

    end_date = params.get('date_end') or datetime.datetime.utcnow()
    if isinstance(end_date, datetime.datetime):
        end_date = end_date.date()
    start_date = (params.get('date_start') or
                  end_date - datetime.timedelta(weeks=2))
    if isinstance(start_date, datetime.datetime):
        start_date = start_date.date()

    context['start_date'] = start_date.strftime('%Y-%m-%d')
    context['end_date'] = end_date.strftime('%Y-%m-%d')

    context['duration'] = abs((start_date - end_date).days)
    context['dates'] = utils.daterange(start_date, end_date)

    context['hang_type'] = params.get('hang_type') or 'any'

    context['date_range_type'] = params.get('date_range_type') or 'report'

    if params.get('hang_type') == 'any':
        hang_type = None
    else:
        hang_type = params.get('hang_type')

    api = models.CrashesPerAdu()
    crashes = api.get(
        product=params['product'],
        versions=params['versions'],
        from_date=start_date,
        to_date=end_date,
        date_range_type=params['date_range_type'],
        os=params['os_names'],
        report_type=hang_type
    )

    code_to_name = dict(
        (x['code'], x['name']) for x in platforms if x.get('display')
    )
    cadu = {}
    cadu = build_data_object_for_adu_graphs(
        context['start_date'],
        context['end_date'],
        crashes['hits'],
        code_to_name=code_to_name
    )
    cadu['product_versions'] = build_data_object_for_crash_reports(
        crashes['hits'],
    )

    data_table = {
        'totals': {},
        'dates': {}
    }

    has_data_versions = set()
    for product_version in crashes['hits']:
        data_table['totals'][product_version] = {
            'crashes': 0,
            'adu': 0,
            'throttle': 0,
            'crash_hadu': 0,
            'ratio': 0,
        }
        for date in crashes['hits'][product_version]:
            crash_info = crashes['hits'][product_version][date]
            has_data_versions.add(crash_info['version'])
            if date not in data_table['dates']:
                data_table['dates'][date] = []
            data_table['dates'][date].append(crash_info)

    if params['date_range_type'] == 'build':
        # for the Date Range = "Build Date" report, we only want to
        # include versions that had data.
        context['versions'] = list(has_data_versions)
    else:
        context['versions'] = params['versions']

    for date in data_table['dates']:
        data_table['dates'][date] = sorted(data_table['dates'][date],
                                           key=itemgetter('version'),
                                           reverse=True)

    if request.GET.get('format') == 'csv':
        return _render_daily_csv(
            request,
            data_table,
            params['product'],
            params['versions'],
            platforms,
            context['os_names'],
        )
    context['data_table'] = data_table
    context['graph_data'] = cadu
    context['report'] = 'daily'

    url = reverse('crashstats:crashes_per_day')
    if request.META.get('QUERY_STRING'):
        url += '?{}'.format(request.META['QUERY_STRING'])
    context['new_daily_report_url'] = url

    return render(request, 'crashstats/daily.html', context)


def _render_daily_csv(request, data, product, versions, platforms, os_names):
    response = http.HttpResponse('text/csv', content_type='text/csv')
    title = 'ADI_' + product + '_' + '_'.join(versions)
    response['Content-Disposition'] = (
        'attachment; filename="%s.csv"' % title
    )
    writer = utils.UnicodeWriter(response)
    head_row = ['Date']
    labels = (
        ('report_count', 'Crashes'),
        ('adu', 'ADI'),
        ('throttle', 'Throttle'),
        ('crash_hadu', 'Ratio'),
    )
    for version in versions:
        for __, label in labels:
            head_row.append('%s %s %s' % (product, version, label))
    writer.writerow(head_row)

    def append_row_blob(blob, labels):
        for key, __ in labels:
            value = blob[key]
            if key == 'throttle':
                value = '%.1f%%' % (100.0 * value)
            elif key in ('crash_hadu', 'ratio'):
                value = '%.3f%%' % value
            else:
                value = str(value)
            row.append(value)

    # reverse so that recent dates appear first
    for date in sorted(data['dates'].keys(), reverse=True):
        crash_info = data['dates'][date]
        """
         `crash_info` is a list that looks something like this:
           [{'adu': 4500,
             'crash_hadu': 43.0,
             'date': u'2012-10-13',
             'product': u'WaterWolf',
             'report_count': 1935,
             'throttle': 1.0,
             'version': u'4.0a2'}]
        """
        row = [date]
        info_by_version = dict((x['version'], x) for x in crash_info)

        # Turn each of them into a dict where the keys is the version
        for version in versions:
            if version in info_by_version:
                blob = info_by_version[version]
                append_row_blob(blob, labels)
            else:
                for __ in labels:
                    row.append('-')

        assert len(row) == len(head_row), (len(row), len(head_row))
        writer.writerow(row)

    return response


@pass_default_context
def crashes_per_day(request, default_context=None):
    context = default_context or {}
    context['products'] = context['active_versions'].keys()

    # This report does not currently support doing a graph by **build date**.
    # So we hardcode the choice to always be regular report.
    # The reason for not entirely deleting the functionality is because
    # we might support it later in the future.
    # The only reason people might get to this page with a
    # date_range_type=build set is if they used the old daily report
    # and clicked on the link to the new Crashes per User report.
    if request.GET.get('date_range_type') == 'build':
        params = dict(request.GET)
        params.pop('date_range_type')
        url = reverse('crashstats:crashes_per_day')
        url += '?' + urllib.urlencode(params, True)
        messages.warning(
            request,
            'The Crashes per User report does not support filtering '
            'by *build* date. '
        )
        return redirect(url)

    platforms_api = models.Platforms()
    platforms = platforms_api.get()

    date_range_types = ['report', 'build']
    hang_types = ['any', 'crash', 'hang-p']
    form = forms.DailyFormByVersion(
        context['active_versions'],
        platforms,
        data=request.GET,
        date_range_types=date_range_types,
        hang_types=hang_types,
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    params = form.cleaned_data
    params['product'] = params.pop('p')
    params['versions'] = sorted(list(set(params.pop('v'))), reverse=True)
    try:
        params['platforms'] = params.pop('os')
    except KeyError:
        params['platforms'] = None

    if len(params['versions']) > 0:
        context['version'] = params['versions'][0]

    context['product'] = params['product']

    if not params['versions']:
        # need to pick the default featured ones
        params['versions'] = []
        for pv in context['active_versions'][context['product']]:
            if pv['is_featured']:
                params['versions'].append(pv['version'])

    context['available_versions'] = []
    for version in context['active_versions'][params['product']]:
        context['available_versions'].append(version['version'])

    if not params.get('platforms'):
        params['platforms'] = [
            x['name'] for x in platforms if x.get('display')
        ]
    context['platforms'] = params.get('platforms')

    end_date = params.get('date_end') or datetime.datetime.utcnow()
    if isinstance(end_date, datetime.datetime):
        end_date = end_date.date()
    start_date = (params.get('date_start') or
                  end_date - datetime.timedelta(weeks=2))
    if isinstance(start_date, datetime.datetime):
        start_date = start_date.date()

    context['start_date'] = start_date.strftime('%Y-%m-%d')
    context['end_date'] = end_date.strftime('%Y-%m-%d')

    context['duration'] = abs((start_date - end_date).days)
    context['dates'] = utils.daterange(start_date, end_date)

    context['hang_type'] = params.get('hang_type') or 'any'

    context['date_range_type'] = params.get('date_range_type') or 'report'

    _date_range_type = params.pop('date_range_type')
    if _date_range_type == 'build':
        params['_histogram.build_id'] = ['version']
        params['_histogram_interval.build_id'] = 1000000
    else:
        params['_histogram.date'] = ['version']
    params['_facets'] = ['version']

    params.pop('date_end')

    params.pop('date_start')
    if _date_range_type == 'build':
        params['build_id'] = [
            '>=' + start_date.strftime('%Y%m%d000000'),
            '<' + end_date.strftime('%Y%m%d000000'),
        ]
    else:
        params['date'] = [
            '>=' + start_date.strftime('%Y-%m-%d'),
            '<' + end_date.strftime('%Y-%m-%d'),
        ]

    params['_results_number'] = 0  # because we don't care about hits
    params['_columns'] = ('date', 'version', 'platform', 'product')
    if params['hang_type'] == 'crash':
        params['hang_type'] = '0'
    elif params['hang_type'] == 'hang-p':
        params['hang_type'] = '-1'
    else:
        params.pop('hang_type')

    # supersearch expects the parameter `versions` (a list or tuple)
    # to be called `version`
    supersearch_params = copy.deepcopy(params)
    supersearch_params['version'] = supersearch_params.pop('versions')
    # in SuperSearch it's called 'Mac' not 'Mac OS X'
    if 'Mac OS X' in supersearch_params['platforms']:
        supersearch_params['platforms'].append('Mac')
        supersearch_params['platforms'].remove('Mac OS X')

    graph_data, results, adi_by_version = _get_crashes_per_day_with_adu(
        supersearch_params,
        start_date,
        end_date,
        platforms,
        _date_range_type
    )

    render_csv = request.GET.get('format') == 'csv'
    data_table = {
        'totals': {},
        'dates': {}
    }
    facets = results['facets']
    has_data_versions = set()
    if _date_range_type == 'build':
        histogram = facets['histogram_build_id']
    else:
        histogram = facets['histogram_date']

    for group in histogram:
        if _date_range_type == 'build':
            date = build_id_to_date(group['term'])
        else:
            date = group['term'].split('T')[0]
        if date not in data_table['dates']:
            data_table['dates'][date] = []
        sorted_by_version = sorted(
            group['facets']['version'],
            key=itemgetter('term'),
            reverse=True
        )

        for facet_group in sorted_by_version:
            term = facet_group['term']
            has_data_versions.add(term)

            count = facet_group['count']
            adi_groups = adi_by_version[term]
            if date in adi_groups:
                total, throttle = adi_groups[date]
                if total:
                    ratio = round(100.0 * count / total / throttle, 3)
                else:
                    ratio = 0.0

                # Why do we divide the count by the throttle?!
                # Consider the case of Release. That one we throttle to 10%
                # meaning that if we received 123 crashes, it happened to
                # about 1230 people actually. We just "discarded" 90% of the
                # records.
                # But, why divide? Because throttle is a floating point
                # number between 0 and 1.0. If it's 1.0 it means we're taking
                # 100% and 234/1.0 == 234. If it's 0.1 it means that
                # 123/0.1 == 1230.
                report_count = int(count / throttle)
                item = {
                    'adi': total,
                    'date': date,
                    'ratio': ratio,
                    'report_count': report_count,
                    'product': params['product'],
                    'throttle': throttle,
                    'version': term,
                }
                # Because this code is using the `_render_daily_csv()` function
                # which is used by the old daily() view function, we have to
                # use the common (and old) names for certain keys
                if render_csv:
                    item['adu'] = item.pop('adi')
                    item['crash_hadu'] = item.pop('ratio')

                data_table['dates'][date].append(item)

    if _date_range_type == 'build':
        # for the Date Range = "Build Date" report, we only want to
        # include versions that had data.
        context['versions'] = list(has_data_versions)
    else:
        context['versions'] = params['versions']

    for date in data_table['dates']:
        data_table['dates'][date] = sorted(
            data_table['dates'][date],
            key=itemgetter('version'),
            reverse=True
        )

    if render_csv:
        return _render_daily_csv(
            request,
            data_table,
            params['product'],
            params['versions'],
            platforms,
            params['platforms'],
        )
    context['data_table'] = data_table
    context['graph_data'] = graph_data
    context['report'] = 'daily'

    errors = []
    for error in results.get('errors', []):
        if not error['type'] == 'shards':
            continue

        week = int(error['index'][-2:])
        year = int(error['index'][-6:-2])
        day = isoweek.Week(year, week).monday()
        percent = error['shards_count'] * 100 / settings.ES_SHARDS_PER_INDEX
        errors.append(
            'The data for the week of {} is ~{}% lower than expected.'.format(
                day, percent
            )
        )
    context['errors'] = errors

    # This 'Crashes per User' report replaces an older version
    # of the report that produces near identical output, but does
    # it using reading aggregates stored in Postgresql.
    # As a transition phase, we offer a link back to the old
    # report using the same current parameters.
    url = reverse('crashstats:daily')
    if request.META.get('QUERY_STRING'):
        url += '?{}'.format(request.META['QUERY_STRING'])
    context['old_daily_report_url'] = url

    return render(request, 'crashstats/crashes_per_day.html', context)


@pass_default_context
@permission_required('crashstats.view_exploitability')
def exploitable_crashes(
    request,
    product=None,
    versions=None,
    default_context=None
):
    """This function is now deprecated in favor of the new one called
    exploitability_report"""
    context = default_context or {}
    if product is None:
        return redirect(
            'crashstats:exploitable_crashes',
            settings.DEFAULT_PRODUCT,
            permanent=True
        )

    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1

    context['current_page'] = page

    results_per_page = settings.EXPLOITABILITY_BATCH_SIZE

    exploitable_crashes = models.CrashesByExploitability()
    exploitable = exploitable_crashes.get(
        product=product,
        version=versions,
        page=page,
        batch=results_per_page
    )
    crashes = []
    bugs = defaultdict(list)
    signatures = [x['signature'] for x in exploitable['hits']]
    if signatures:
        api = models.Bugs()
        for b in api.get(signatures=signatures)['hits']:
            bugs[b['signature']].append(b['id'])
    for crash in exploitable['hits']:
        crash['bugs'] = sorted(bugs.get(crash['signature'], []), reverse=True)
        crashes.append(crash)
    context['crashes'] = crashes
    context['pages'] = int(math.ceil(
        1.0 * exploitable['total'] / results_per_page
    ))
    context['version'] = versions
    context['report'] = 'exploitable'
    context['new_link_url'] = reverse('crashstats:exploitability_report')
    query_string = {'product': product}
    if versions:
        query_string['version'] = versions
    context['new_link_url'] += '?' + urllib.urlencode(query_string, True)
    return render(request, 'crashstats/exploitability.html', context)


@pass_default_context
@permission_required('crashstats.view_exploitability')
def exploitability_report(request, default_context=None):
    context = default_context or {}

    if not request.GET.get('product'):
        url = reverse('crashstats:exploitability_report')
        url += '?' + urllib.urlencode({
            'product': settings.DEFAULT_PRODUCT
        })
        return redirect(url)

    form = forms.ExploitabilityReportForm(
        request.GET,
        active_versions=context['active_versions'],
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    product = form.cleaned_data['product']
    version = form.cleaned_data['version']

    api = SuperSearchUnredacted()
    params = {
        'product': product,
        'version': version,
        '_results_number': 0,
        # This aggregates on crashes that do NOT contain these
        # key words. For example, if a crash has
        # {'exploitability': 'error: unable to analyze dump'}
        # then it won't get included.
        'exploitability': ['!error', '!interesting'],
        '_aggs.signature': 'exploitability',
        '_facets_size': settings.EXPLOITABILITY_BATCH_SIZE,
    }
    results = api.get(**params)

    base_signature_report_dict = {
        'product': product,
    }
    if version:
        base_signature_report_dict['version'] = version

    crashes = []
    categories = ('high', 'none', 'low', 'medium', 'null')
    for signature_facet in results['facets']['signature']:
        # this 'signature_facet' will look something like this:
        #
        #  {
        #      'count': 1234,
        #      'term': 'My | Signature',
        #      'facets': {
        #          'exploitability': [
        #              {'count': 1, 'term': 'high'},
        #              {'count': 23, 'term': 'medium'},
        #              {'count': 11, 'term': 'other'},
        #
        # And we only want to include those where:
        #
        #   low or medium or high are greater than 0
        #

        exploitability = signature_facet['facets']['exploitability']
        if not any(
            x['count']
            for x in exploitability
            if x['term'] in ('high', 'medium', 'low')
        ):
            continue
        crash = {
            'bugs': [],
            'signature': signature_facet['term'],
            'high_count': 0,
            'medium_count': 0,
            'low_count': 0,
            'none_count': 0,
            'url': (
                reverse('signature:signature_report') + '?' +
                urllib.urlencode(dict(
                    base_signature_report_dict,
                    signature=signature_facet['term']
                ))
            ),
        }
        for cluster in exploitability:
            if cluster['term'] in categories:
                crash['{}_count'.format(cluster['term'])] = (
                    cluster['count']
                )
        crash['med_or_high'] = (
            crash.get('high_count', 0) +
            crash.get('medium_count', 0)
        )
        crashes.append(crash)

    # Sort by the 'med_or_high' key first (descending),
    # and by the signature second (ascending).
    crashes.sort(key=lambda x: (-x['med_or_high'], x['signature']))

    # now, let's go back and fill in the bugs
    signatures = [x['signature'] for x in crashes]
    if signatures:
        api = models.Bugs()
        bugs = defaultdict(list)
        for b in api.get(signatures=signatures)['hits']:
            bugs[b['signature']].append(b['id'])

        for crash in crashes:
            crash['bugs'] = bugs.get(crash['signature'], [])

    context['crashes'] = crashes
    context['product'] = product
    context['version'] = version
    if context['product'] and context['version']:
        context['old_link_url'] = reverse(
            'crashstats:exploitable_crashes',
            args=(context['product'], context['version'])
        )
    else:
        context['old_link_url'] = reverse(
            'crashstats:exploitable_crashes',
            args=(context['product'],)
        )
    context['report'] = 'exploitable'
    return render(request, 'crashstats/exploitability_report.html', context)


@pass_default_context
def report_index(request, crash_id, default_context=None):
    if not crash_id:
        raise http.Http404('Crash id is missing')
    valid_crash_id = utils.find_crash_id(crash_id)
    if not valid_crash_id:
        return http.HttpResponseBadRequest('Invalid crash ID')

    # Sometimes, in Socorro we use a prefix on the crash ID. Usually it's
    # 'bp-' but this is configurable.
    # If you try to use this to reach the perma link for a crash, it should
    # redirect to the report index with the correct crash ID.
    if valid_crash_id != crash_id:
        return redirect(reverse(
            'crashstats:report_index',
            args=(valid_crash_id,)
        ))

    context = default_context or {}
    context['crash_id'] = crash_id

    api = models.UnredactedCrash()

    def handle_middleware_404(crash_id, error_code):
        if error_code == 404:
            # if crash was submitted today, send to pending screen
            crash_date = datetime.datetime.strptime(crash_id[-6:], '%y%m%d')
            crash_age = datetime.datetime.utcnow() - crash_date
            if crash_age < datetime.timedelta(days=1):
                tmpl = 'crashstats/report_index_pending.html'
            else:
                tmpl = 'crashstats/report_index_not_found.html'
            return render(request, tmpl, context)
        elif error_code == 408:
            return render(request,
                          'crashstats/report_index_pending.html', context)
        elif error_code == 410:
            return render(request,
                          'crashstats/report_index_too_old.html', context)

        # this is OK because this function is expected to be called within
        # an exception stack frame
        raise

    try:
        context['report'] = api.get(crash_id=crash_id)
    except models.BadStatusCodeError as e:
        return handle_middleware_404(crash_id, e.status)

    if 'json_dump' in context['report']:
        json_dump = context['report']['json_dump']
        if 'sensitive' in json_dump and \
           not request.user.has_perm('crashstats.view_pii'):
            del json_dump['sensitive']
        context['raw_stackwalker_output'] = json.dumps(
            json_dump,
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
        )
        utils.enhance_json_dump(json_dump, settings.VCS_MAPPINGS)
        parsed_dump = json_dump
    elif 'dump' in context['report']:
        context['raw_stackwalker_output'] = context['report']['dump']
        parsed_dump = utils.parse_dump(
            context['report']['dump'],
            settings.VCS_MAPPINGS
        )
    else:
        context['raw_stackwalker_output'] = 'No dump available'
        parsed_dump = {}

    # If the parsed_dump lacks a `parsed_dump.crash_info.crashing_thread`
    # we can't loop over the frames :(
    if parsed_dump.get('crash_info', {}).get('crashing_thread') is None:
        # the template does a big `{% if parsed_dump.threads %}`
        parsed_dump['threads'] = None
    context['parsed_dump'] = parsed_dump
    context['bug_product_map'] = settings.BUG_PRODUCT_MAP

    process_type = 'unknown'
    if context['report']['process_type'] is None:
        process_type = 'browser'
    elif context['report']['process_type'] == 'plugin':
        process_type = 'plugin'
    elif context['report']['process_type'] == 'content':
        process_type = 'content'
    context['process_type'] = process_type

    bugs_api = models.Bugs()
    hits = bugs_api.get(signatures=[context['report']['signature']])['hits']
    # bugs_api.get(signatures=...) will return all signatures associated
    # with the bugs found, but we only want those with matching signature
    context['bug_associations'] = [
        x for x in hits
        if x['signature'] == context['report']['signature']
    ]
    context['bug_associations'].sort(
        key=lambda x: x['id'],
        reverse=True
    )

    raw_api = models.RawCrash()
    try:
        context['raw'] = raw_api.get(crash_id=crash_id)
    except models.BadStatusCodeError as e:
        return handle_middleware_404(crash_id, e.status)

    context['raw_keys'] = []
    if request.user.has_perm('crashstats.view_pii'):
        # hold nothing back
        context['raw_keys'] = context['raw'].keys()
    else:
        context['raw_keys'] = [
            x for x in context['raw']
            if x in models.RawCrash.API_WHITELIST
        ]
    context['raw_keys'].sort(key=unicode.lower)

    if request.user.has_perm('crashstats.view_rawdump'):
        context['raw_dump_urls'] = [
            reverse('crashstats:raw_data', args=(crash_id, 'dmp')),
            reverse('crashstats:raw_data', args=(crash_id, 'json'))
        ]
        if context['raw'].get('additional_minidumps'):
            suffixes = [
                x.strip()
                for x in context['raw']['additional_minidumps'].split(',')
                if x.strip()
            ]
            for suffix in suffixes:
                name = 'upload_file_minidump_%s' % (suffix,)
                context['raw_dump_urls'].append(
                    reverse(
                        'crashstats:raw_data_named',
                        args=(crash_id, name, 'dmp')
                    )
                )

    # On the report_index template, we have a piece of JavaScript
    # that triggers an AJAX query to find out if there are correlations
    # for this particular product, version, signature, platform combo
    # under any report type. That AJAX query takes some time and it means
    # the "Correlations" tab initially starts hidden and if there are
    # correlations, the tab becomes visible.
    # If that AJAX query has been done before, let's find out early
    # and use that fact to immediately display the "Correlations" tab.
    if (
        context['report']['product'] and
        context['report']['version'] and
        context['report']['os_name'] and
        context['report']['signature']
    ):
        total_correlations_cache_key = make_correlations_count_cache_key(
            context['report']['product'],
            context['report']['version'],
            context['report']['os_name'],
            context['report']['signature'],
        )
        # Because it's hard to do something like `{% if foo is None %}` in
        # Jinja we instead make the default -1. That means it's not
        # confused with 0 it basically means "We don't know".
        context['total_correlations'] = cache.get(
            total_correlations_cache_key,
            -1
        )
    else:
        # Some crashes might potentially miss this. For example,
        # some crashes unfortunately don't have a platform (aka os_name)
        # so finding correlations on those will never work.
        context['total_correlations'] = 0

    # Add descriptions to all fields.
    all_fields = SuperSearchFields().get()
    descriptions = {}
    for field in all_fields.values():
        key = '{}.{}'.format(field['namespace'], field['in_database_name'])
        descriptions[key] = '{} Search: {}'.format(
            field.get('description', '').strip() or
            'No description for this field.',
            field['is_exposed'] and field['name'] or 'N/A',
        )

    context['fields_desc'] = descriptions
    context['empty_desc'] = 'No description for this field. Search: unknown'

    context['BUG_PRODUCT_MAP'] = settings.BUG_PRODUCT_MAP
    context['CRASH_ANALYSIS_URL'] = settings.CRASH_ANALYSIS_URL
    return render(request, 'crashstats/report_index.html', context)


@utils.json_view
def report_pending(request, crash_id):
    if not crash_id:
        raise http.Http404("Crash id is missing")

    data = {}

    url = reverse('crashstats:report_index', kwargs=dict(crash_id=crash_id))

    api = models.UnredactedCrash()

    try:
        data['report'] = api.get(crash_id=crash_id)
        status = 'ready'
        status_message = 'The report for %s is now available.' % crash_id
        url_redirect = "%s" % url
    except models.BadStatusCodeError as e:
        if str(e).startswith('5'):
            raise
        status = 'error'
        status_message = 'The report for %s is not available yet.' % crash_id
        url_redirect = ''

    data = {
        "status": status,
        "status_message": status_message,
        "url_redirect": url_redirect
    }
    return data


@pass_default_context
def report_list(request, partial=None, default_context=None):
    context = default_context or {}
    form = forms.ReportListForm(
        context['active_versions'],
        request.GET
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    context['current_page'] = page

    context['signature'] = form.cleaned_data['signature']
    context['product_versions'] = form.cleaned_data['version']

    end_date = form.cleaned_data['date'] or datetime.datetime.utcnow()

    if form.cleaned_data['range_unit']:
        range_unit = form.cleaned_data['range_unit']
    else:
        range_unit = settings.RANGE_UNITS[0]

    if form.cleaned_data['process_type']:
        process_type = form.cleaned_data['process_type']
    else:
        process_type = settings.PROCESS_TYPES[0]

    if form.cleaned_data['hang_type']:
        hang_type = form.cleaned_data['hang_type']
    else:
        hang_type = settings.HANG_TYPES[0]

    if form.cleaned_data['plugin_field']:
        plugin_field = form.cleaned_data['plugin_field']
    else:
        plugin_field = settings.PLUGIN_FIELDS[0]

    if form.cleaned_data['plugin_query_type']:
        plugin_query_type = form.cleaned_data['plugin_query_type']
        if plugin_query_type in settings.QUERY_TYPES_MAP:
            plugin_query_type = settings.QUERY_TYPES_MAP[plugin_query_type]
    else:
        plugin_query_type = settings.QUERY_TYPES[0]

    duration = get_timedelta_from_value_and_unit(
        int(form.cleaned_data['range_value']),
        range_unit
    )

    if request.user.has_perm('crashstats.run_long_queries'):
        # The user is an admin and is allowed to perform bigger queries
        max_query_range = settings.QUERY_RANGE_MAXIMUM_DAYS_ADMIN
    else:
        max_query_range = settings.QUERY_RANGE_MAXIMUM_DAYS

    # Check whether the user tries to run a big query, and limit it
    if duration.days > max_query_range:
        return http.HttpResponseBadRequest('range duration too long')

    context['current_day'] = duration.days

    start_date = end_date - duration
    context['start_date'] = start_date.strftime('%Y-%m-%d')
    context['end_date'] = end_date.strftime('%Y-%m-%d')

    if form.cleaned_data['product']:
        context['selected_products'] = form.cleaned_data['product']
        context['product'] = form.cleaned_data['product'][0]
    else:
        context['selected_products'] = None
        context['product'] = settings.DEFAULT_PRODUCT

    results_per_page = 250
    result_offset = results_per_page * (page - 1)

    ALL_REPORTS_COLUMNS = (
        # key, label, on by default?
        ('date_processed', 'Date', True),
        ('duplicate_of', 'Dup', True),
        ('product', 'Product', True),
        ('version', 'Version', True),
        ('build', 'Build', True),
        ('os_and_version', 'OS', True),
        ('cpu_name', 'Build Arch', True),
        ('reason', 'Reason', True),
        ('address', 'Address', True),
        ('uptime', 'Uptime', True),
        ('install_time', 'Install Time', True),
        ('user_comments', 'Comments', True),
    )
    # columns that should, by default, start in descending order
    DEFAULT_REVERSE_COLUMNS = (
        'date_processed',
    )

    _default_column_keys = [x[0] for x in ALL_REPORTS_COLUMNS if x[2]]
    raw_crash_fields = models.RawCrash.API_WHITELIST

    if request.user.has_perm('crashstats.view_pii'):
        # add any fields to ALL_REPORTS_COLUMNS raw_crash_fields that
        # signed in people are allowed to see.
        raw_crash_fields += ('URL',)

    RAW_CRASH_FIELDS = sorted(
        raw_crash_fields,
        key=lambda x: x.lower()
    )

    all_reports_columns_keys = [x[0] for x in ALL_REPORTS_COLUMNS]
    ALL_REPORTS_COLUMNS = tuple(
        list(ALL_REPORTS_COLUMNS) +
        [(x, '%s*' % x, False) for x in RAW_CRASH_FIELDS
         if x not in all_reports_columns_keys]
    )

    if partial == 'reports' or partial == 'correlations':
        # This is an optimization.
        # The primary use of the "Reports" tab is to load data on the
        # models.ReportList() model. However, the models.Correlations() model
        # is also going to need to do this to figure out all the OSs and
        # versions that it needs.
        # By calling the models.ReportList().get(...), independent of
        # sorting requirements for both partials, we can take advantage
        # of the fact that the ReportList() data gets cached.

        context['sort'] = request.GET.get('sort', 'date_processed')
        context['reverse'] = request.GET.get('reverse', 'true').lower()
        context['reverse'] = context['reverse'] != 'false'

        columns = request.GET.getlist('c')
        # these are the columns used to render the table in reports.html
        context['columns'] = []
        for key, label, default in ALL_REPORTS_COLUMNS:
            if (not columns and default) or key in columns:
                reverse_ = None
                if key == context['sort']:
                    reverse_ = not context['reverse']
                else:
                    if key in DEFAULT_REVERSE_COLUMNS:
                        reverse_ = True
                context['columns'].append({
                    'key': key,
                    'label': label,
                    'reverse': reverse_
                })
        context['columns_values_joined'] = ','.join(
            x['key'] for x in context['columns']
        )

        include_raw_crash = False
        for each in context['columns']:
            key = each['key']
            if key in raw_crash_fields and key not in _default_column_keys:
                include_raw_crash = True
                break

        context['include_raw_crash'] = include_raw_crash

        # some column keys have ids that aren't real fields,
        # so transform those before sending to the middleware
        sort_ = context['sort']
        if sort_ == 'os_and_version':
            sort_ = 'os_name'

        assert start_date and end_date
        api = models.ReportList()
        context['report_list'] = api.get(
            signature=context['signature'],
            products=context['selected_products'],
            versions=context['product_versions'],
            start_date=start_date,
            end_date=end_date,
            build_ids=form.cleaned_data['build_id'],
            reasons=form.cleaned_data['reason'],
            release_channels=form.cleaned_data['release_channels'],
            report_process=process_type,
            report_type=hang_type,
            plugin_in=plugin_field,
            plugin_search_mode=plugin_query_type,
            plugin_terms=form.cleaned_data['plugin_query'],
            include_raw_crash=include_raw_crash,
            result_number=results_per_page,
            result_offset=result_offset,
            sort=sort_,
            reverse=context['reverse'],
        )

    if partial == 'reports':

        current_query = request.GET.copy()
        if 'page' in current_query:
            del current_query['page']
        context['current_url'] = '%s?%s' % (reverse('crashstats:report_list'),
                                            current_query.urlencode())

        if not context['report_list']['hits']:
            return render(
                request,
                'crashstats/partials/no_data.html',
                context
            )

        context['report_list']['total_pages'] = int(math.ceil(
            context['report_list']['total'] / float(results_per_page)))

        context['report_list']['total_count'] = context['report_list']['total']

    if partial == 'correlations':
        counts = defaultdict(int)

        for report in context['report_list']['hits']:
            product = report['product']
            os_name = report['os_name']
            version = report['version']

            counts[(product, os_name, version)] += 1

            report['date_processed'] = utils.parse_isodate(
                report['date_processed']
            ).strftime('%b %d, %Y %H:%M')

            # re-format it to be human-friendly
            install_time = report.get('install_time')
            if install_time:
                if isinstance(install_time, basestring):
                    if install_time.isdigit():
                        # new-style as a timestamp
                        install_time = datetime.datetime.fromtimestamp(
                            float(install_time)
                        )
                    else:
                        # old style, middleware returned a formatted string
                        install_time = utils.parse_isodate(install_time)
                # put it back into the report
                report['install_time'] = install_time.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )

        # First gather a map of product->versions where the product
        # and versions are only those that are "active", which means
        # they have an sunset date that is >= now.
        release_versions = {}
        for product, versions in context['active_versions'].items():
            release_versions[product] = [x['version'] for x in versions]

        # Sort all found product/os/version combinations by number
        # of crashes and filter out those not in the releases
        # (mentioned above). Then limit number of combinations
        # by the MAX_CORRELATION_COMBOS_PER_SIGNATURE setting.
        context['correlation_combos'] = [
            {
                'product': k[0],
                'os': k[1],
                'version': k[2],
            }
            for k, v in sorted(
                counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            if k[2] in release_versions.get(k[0], [])
        ][:settings.MAX_CORRELATION_COMBOS_PER_SIGNATURE]

        correlations_api = models.CorrelationsSignatures()
        total_correlations = 0
        if context['correlation_combos']:
            for combo in context['correlation_combos']:
                # this should ideally be turned into 1 query
                for report_type in settings.CORRELATION_REPORT_TYPES:
                    correlations = correlations_api.get(
                        report_type=report_type,
                        product=context['product'],
                        version=combo['version'],
                        platforms=combo['os']
                    )
                    hits = correlations['hits'] if correlations else []
                    if context['signature'] in hits:
                        total_correlations += 1
        context['total_correlations'] = total_correlations

    versions = []
    for product_version in context['product_versions']:
        versions.append(product_version.split(':')[1])

    if partial == 'table':
        context['table'] = {}

        crashes_frequency_api = models.CrashesFrequency()
        params = {
            'signature': context['signature'],
            'products': [context['product']],
            'versions': versions,
            'from': start_date.date(),
            'to': end_date.date(),
        }
        builds = crashes_frequency_api.get(**params)['hits']

        for i, build in enumerate(builds):
            try:
                build_date = datetime.datetime.strptime(build['build_date'],
                                                        '%Y%m%d%H%M%S')
                buildid = build_date.strftime('%Y%m%d%H')
            except ValueError:
                # ValueError happens when build['build_date'] isn't really
                # a date
                buildid = build['build_date']
            except TypeError:
                # TypeError happens when build['build_date'] is None
                buildid = "(no build ID found)"
            context['table'][buildid] = build

    # signature URLs only if you're logged in
    if partial == 'sigurls':
        if context['selected_products']:
            products = [context['product']]
        else:
            products = 'ALL'
            assert not context['product_versions'], context['product_versions']
        if request.user.has_perm('crashstats.view_pii'):
            signatureurls_api = models.SignatureURLs()
            sigurls = signatureurls_api.get(
                signature=context['signature'],
                products=products,
                versions=context['product_versions'],
                start_date=start_date,
                end_date=end_date
            )
            context['signature_urls'] = sigurls['hits']
        else:
            context['signature_urls'] = None

    if partial == 'comments':
        context['comments'] = []
        comments_api = models.CommentsBySignature()

        context['comments'] = comments_api.get(
            signature=context['signature'],
            products=form.cleaned_data['product'],
            versions=context['product_versions'],
            start_date=start_date,
            end_date=end_date,
            build_ids=form.cleaned_data['build_id'],
            reasons=form.cleaned_data['reason'],
            release_channels=form.cleaned_data['release_channels'],
            report_process=form.cleaned_data['process_type'],
            report_type=form.cleaned_data['hang_type'],
            plugin_in=form.cleaned_data['plugin_field'],
            plugin_search_mode=form.cleaned_data['plugin_query_type'],
            plugin_terms=form.cleaned_data['plugin_query'],
            result_number=results_per_page,
            result_offset=result_offset
        )

        current_query = request.GET.copy()
        if 'page' in current_query:
            del current_query['page']
        context['current_url'] = '%s?%s' % (reverse('crashstats:report_list'),
                                            current_query.urlencode())

        if not context['comments']['hits']:
            return render(
                request,
                'crashstats/partials/no_data.html',
                context
            )

        context['comments']['total_pages'] = int(math.ceil(
            context['comments']['total'] / float(results_per_page)))

        context['comments']['total_count'] = context['comments']['total']

    if partial == 'bugzilla':
        bugs_api = models.Bugs()
        context['bug_associations'] = bugs_api.get(
            signatures=[context['signature']]
        )['hits']

        context['bug_associations'].sort(key=lambda x: x['id'], reverse=True)

        match_total = 0
        for bug in context['bug_associations']:
            # Only add up bugs where it matches the signature exactly.
            if bug['signature'] == context['signature']:
                match_total += 1

        context['bugsig_match_total'] = match_total

    if partial == 'graph':
        # if we have a version, expose the channel for the current
        # release for use in the adu graph
        if context['product_versions']:
            context['channel'] = get_build_type_for_product_versions(
                context['product_versions']
            )
        else:
            # if no version was provided fallback to nightly
            context['channel'] = 'nightly'

        # the ui is going to need access to all channels
        context['channels'] = ','.join(settings.CHANNELS)

        # set initial form data
        data = {
            'product_name': context['product'],
            'signature': context['signature'],
            'channel': context['channel'],
            'start_date': context['start_date'],
            'end_date': context['end_date']
        }
        context['form'] = forms.ADUBySignatureJSONForm(
            settings.CHANNELS,
            context['active_versions'],
            data,
            auto_id=True
        )

    if not partial:
        # prep it so it's nicer to work with in the template
        context['all_reports_columns'] = [
            {'value': x[0], 'label': x[1], 'default': x[2]}
            for x in ALL_REPORTS_COLUMNS
        ]
        super_search_params = get_super_search_style_params(
            signature=context['signature'],
            product=context['selected_products'],
            version=context['product_versions'],
            start_date=start_date,
            end_date=end_date,
        )
        context['super_search_query_string'] = urllib.urlencode(
            utils.sanitize_dict(super_search_params),
            True
        )

    if partial == 'graph':
        tmpl = 'crashstats/partials/graph.html'
    elif partial == 'reports':
        tmpl = 'crashstats/partials/reports.html'
    elif partial == 'comments':
        tmpl = 'crashstats/partials/comments.html'
    elif partial == 'sigurls':
        tmpl = 'crashstats/partials/sigurls.html'
    elif partial == 'bugzilla':
        tmpl = 'crashstats/partials/bugzilla.html'
    elif partial == 'table':
        tmpl = 'crashstats/partials/table.html'
    elif partial == 'correlations':
        tmpl = 'crashstats/partials/correlations.html'
    elif partial:
        raise NotImplementedError('Unknown template for %s' % partial)
    else:
        tmpl = 'crashstats/report_list.html'

    return render(request, tmpl, context)


@utils.json_view
@pass_default_context
def adu_by_signature_json(request, default_context=None):
    context = default_context

    form = forms.ADUBySignatureJSONForm(
        settings.CHANNELS,
        context['active_versions'],
        data=request.GET,
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    product = form.cleaned_data['product_name']
    signature = form.cleaned_data['signature']
    channel = form.cleaned_data['channel']
    start_date = form.cleaned_data['start_date']
    end_date = form.cleaned_data['end_date']

    api = models.AduBySignature()
    adu_by_sig_data = api.get(
        product_name=product,
        start_date=start_date,
        end_date=end_date,
        signature=signature,
        channel=channel
    )

    return adu_by_sig_data


def status_json(request):
    """This is deprecated and should not be used.
    Use the /api/Status/ endpoint instead.
    """
    if settings.DEBUG:
        raise Exception(
            'This view is deprecated and should not be accessed. '
            'The only reason it\'s kept is for legacy reasons.'
        )
    return redirect(reverse('api:model_wrapper', args=('Status',)))


def status_revision(request):
    return http.HttpResponse(
        models.Status().get()['socorro_revision'],
        content_type='text/plain'
    )


@pass_default_context
def crontabber_state(request, default_context=None):
    context = default_context or {}
    return render(request, 'crashstats/crontabber_state.html', context)


@pass_default_context
def login(request, default_context=None):
    context = default_context or {}
    return render(request, 'crashstats/login.html', context)


def quick_search(request):
    query = request.GET.get('query', '').strip()
    crash_id = utils.find_crash_id(query)

    if crash_id:
        url = reverse(
            'crashstats:report_index',
            kwargs=dict(crash_id=crash_id)
        )
    elif query:
        url = '%s?signature=%s' % (
            reverse('supersearch.search'),
            urlquote('~%s' % query)
        )
    else:
        url = reverse('supersearch.search')

    return redirect(url)


@utils.json_view
def buginfo(request, signatures=None):
    form = forms.BugInfoForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    bug_ids = form.cleaned_data['bug_ids']

    bzapi = models.BugzillaBugInfo()
    result = bzapi.get(bug_ids)
    return result


@utils.json_view
def plot_signature(request, product, versions, start_date, end_date,
                   signature):
    date_format = '%Y-%m-%d'
    try:
        start_date = datetime.datetime.strptime(start_date, date_format)
        end_date = datetime.datetime.strptime(end_date, date_format)
    except ValueError, msg:
        return http.HttpResponseBadRequest(str(msg))

    if not signature:
        return http.HttpResponseBadRequest('signature is required')

    api = models.SignatureTrend()
    sigtrend = api.get(
        product=product,
        version=versions,
        signature=signature,
        end_date=end_date,
        start_date=start_date,
    )

    graph_data = {
        'startDate': start_date,
        'signature': signature,
        'endDate': end_date,
        'counts': [],
        'percents': [],
    }

    for s in sigtrend['hits']:
        t = utils.unixtime(s['date'], millis=True)
        graph_data['counts'].append([t, s['count']])
        graph_data['percents'].append([t, (s['percent_of_total'])])

    return graph_data


@pass_default_context
def signature_summary(request, default_context=None):
    context = default_context or {}
    form = forms.SignatureSummaryForm(
        context['active_versions'],
        request.GET
    )

    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    range_value = form.cleaned_data['range_value'] or 1
    end_date = form.cleaned_data['date'] or datetime.datetime.utcnow()
    signature = form.cleaned_data['signature']
    version = form.cleaned_data['version']

    start_date = end_date - datetime.timedelta(days=range_value)

    report_types = {
        'architecture': 'architectures',
        'flash_version': 'flashVersions',
        'os': 'percentageByOs',
        'process_type': 'processTypes',
        'products': 'productVersions',
        'uptime': 'uptimeRange',
        'distinct_install': 'distinctInstall',
        'devices': 'devices',
        'graphics': 'graphics',
        'exploitability': 'exploitabilityScore',
    }
    api = models.SignatureSummary()

    result = {}
    context = {}

    results = api.get(
        report_types=report_types.keys(),
        signature=signature,
        start_date=start_date,
        end_date=end_date,
        versions=version,
    )
    for r, name in report_types.items():
        result[name] = results['reports'][r]
        context[name] = []

    # whether you can view the exploitability stuff depends on several
    # logical steps...
    can_view_exploitability = False
    if request.user.has_perm('crashstats.view_exploitability'):
        # definitely!
        can_view_exploitability = True
    elif request.user.has_perm('crashstats.view_flash_exploitability'):
        # then it better be only Flash versions
        flash_versions = [
            x['category'] for x in result['flashVersions']
        ]
        # This business logic is very specific.
        # For more information see
        # https://bugzilla.mozilla.org/show_bug.cgi?id=946429
        if flash_versions and '[blank]' not in flash_versions:
            can_view_exploitability = True

    if can_view_exploitability:
        for r in result['exploitabilityScore']:
            context['exploitabilityScore'].append({
                'report_date': r['report_date'],
                'null_count': r['null_count'],
                'low_count': r['low_count'],
                'medium_count': r['medium_count'],
                'high_count': r['high_count'],
            })
    else:
        result.pop('exploitabilityScore')
        context.pop('exploitabilityScore')

    context['can_view_exploitability'] = can_view_exploitability

    def format_float(number):
        return '%.2f' % float(number)

    for r in result['architectures']:
        context['architectures'].append({
            'architecture': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['percentageByOs']:
        context['percentageByOs'].append({
            'os': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['productVersions']:
        context['productVersions'].append({
            'product': r['product_name'],
            'version': r['version_string'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['uptimeRange']:
        context['uptimeRange'].append({
            'range': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['processTypes']:
        context['processTypes'].append({
            'processType': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['flashVersions']:
        context['flashVersions'].append({
            'flashVersion': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['distinctInstall']:
        context['distinctInstall'].append({
            'product': r['product_name'],
            'version': r['version_string'],
            'crashes': r['crashes'],
            'installations': r['installations']})
    for r in result['devices']:
        context['devices'].append({
            'cpu_abi': r['cpu_abi'],
            'manufacturer': r['manufacturer'],
            'model': r['model'],
            'version': r['version'],
            'report_count': r['report_count'],
            'percentage': r['percentage'],
        })
    for r in result['graphics']:
        if r['vendor_name']:
            vendor_name = '{0} ({1})'.format(
                r['vendor_name'],
                r['vendor_hex']
            )
        else:
            vendor_name = r['vendor_hex']
        if r['adapter_name']:
            adapter_name = '{0} ({1})'.format(
                r['adapter_name'],
                r['adapter_hex']
            )
        else:
            adapter_name = r['adapter_hex']
        context['graphics'].append({
            'vendor': vendor_name,
            'adapter': adapter_name,
            'report_count': r['report_count'],
            'percentage': r['percentage'],
        })
    return render(request, 'crashstats/signature_summary_tables.html', context)


@pass_default_context
@anonymous_csrf
def gccrashes(request, product, version=None, default_context=None):
    context = default_context or {}
    versions = get_all_nightlies_for_product(context, product)

    if version is None:
        # No version was passed get the latest nightly
        version = get_latest_nightly(context, product)

    current_products = context['active_versions'].keys()

    context['report'] = 'gccrashes'
    context['version'] = version
    context['versions'] = versions
    context['products'] = current_products
    context['selected_version'] = version
    context['selected_product'] = product

    start_date = None
    end_date = None
    date_today = datetime.datetime.utcnow()
    week_ago = date_today - datetime.timedelta(days=7)

    # Check whether dates were passed but, only use these if both
    # the start and end date was provided else, fallback to the defaults.
    if 'start_date' in request.GET and 'end_date' in request.GET:
        start_date = request.GET['start_date']
        end_date = request.GET['end_date']

    context['start_date'] = start_date if start_date else week_ago
    context['end_date'] = end_date if end_date else date_today

    nightly_versions = get_all_nightlies(context)

    data = {
        'product': product,
        'version': version,
        'start_date': context['start_date'],
        'end_date': context['end_date']
    }
    context['form'] = forms.GCCrashesForm(
        data,
        nightly_versions=nightly_versions,
        auto_id=True
    )

    return render(request, 'crashstats/gccrashes.html', context)


@utils.json_view
@pass_default_context
def gccrashes_json(request, default_context=None):

    nightly_versions = get_all_nightlies(default_context)

    form = forms.GCCrashesForm(request.GET, nightly_versions=nightly_versions)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    product = form.cleaned_data['product']
    version = form.cleaned_data['version']
    start_date = form.cleaned_data['start_date']
    end_date = form.cleaned_data['end_date']

    api = models.GCCrashes()
    result = api.get(
        product=product,
        version=version,
        from_date=start_date,
        to=end_date,
    )

    return result


@utils.json_view
@pass_default_context
def get_nightlies_for_product_json(request, default_context=None):
    return get_all_nightlies_for_product(
        default_context,
        request.GET.get('product')
    )


@permission_required('crashstats.view_rawdump')
def raw_data(request, crash_id, extension, name=None):
    api = models.RawCrash()
    if extension == 'json':
        format = 'meta'
        content_type = 'application/json'
    elif extension == 'dmp':
        format = 'raw'
        content_type = 'application/octet-stream'
    else:
        raise NotImplementedError(extension)

    data = api.get(crash_id=crash_id, format=format, name=name)
    response = http.HttpResponse(content_type=content_type)

    if extension == 'json':
        response.write(json.dumps(data))
    else:
        response.write(data)
    return response


@utils.json_view
@pass_default_context
def correlations_json(request, default_context=None):
    context = default_context or {}

    form = forms.CorrelationsJSONForm(
        context['active_versions'],
        models.Platforms().get(),
        request.GET
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    report_types = form.cleaned_data['correlation_report_types']
    product = form.cleaned_data['product']
    version = form.cleaned_data['version']
    # correlations does not differentiate betas since it works on raw data
    if version.endswith('b'):
        version = version.split('b')[0]
    platform = form.cleaned_data['platform']
    signature = form.cleaned_data['signature']

    api = models.Correlations()
    context = {}
    for report_type in report_types:
        # To keep things simple,
        # the actual middleware query only supports querying by 1 report
        # type at a time. At some point we ought to change that so it
        # takes in a list instead.
        # One big change at a time!
        context[report_type] = api.get(
            report_type=report_type,
            product=product,
            version=version,
            platform=platform,
            signature=signature
        )
    return context


@utils.json_view
@pass_default_context
def correlations_signatures_json(request, default_context=None):
    context = default_context or {}

    form = forms.CorrelationsSignaturesJSONForm(
        context['active_versions'],
        models.Platforms().get(),
        request.GET
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    report_types = form.cleaned_data['correlation_report_types']
    product = form.cleaned_data['product']
    version = form.cleaned_data['version']
    platforms = form.cleaned_data['platforms']

    api = models.CorrelationsSignatures()
    context = {}
    for report_type in report_types:
        result = api.get(
            report_type=report_type,
            product=product,
            version=version,
            platforms=platforms
        )
        # if the product and/or version is completely unrecognized, you
        # don't get an error or an empty list, you get NULL

        if result is None:
            result = {'hits': [], 'total': 0}
        context[report_type] = result
    return context


@utils.json_view
@pass_default_context
def correlations_count_json(request, default_context=None):
    context = default_context or {}
    form = forms.AnyCorrelationsJSONForm(
        context['active_versions'],
        models.Platforms().get(),
        request.GET
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(
            json.dumps({'error': str(form.errors)}),
            content_type='application/json; charset=UTF-8'
        )

    signature = form.cleaned_data['signature']
    product = form.cleaned_data['product']
    version = form.cleaned_data['version']
    platform = form.cleaned_data['platform']

    api = models.CorrelationsSignatures()
    count = 0
    errors = []
    for report_type in settings.CORRELATION_REPORT_TYPES:
        try:
            result = api.get(
                report_type=report_type,
                product=product,
                version=version,
                platforms=platform,
            )
            hits = result and result['hits'] or []
            if signature in hits:
                count += 1
        except models.BadStatusCodeError:
            errors.append(report_type)

    cache_key = make_correlations_count_cache_key(
        product,
        version,
        platform,
        signature
    )
    # Save in the cache this number so we can save time, next time
    # the report_index page is loaded.
    cache.set(cache_key, count, 60 * 60)

    return {'count': count, 'errors': errors}


def graphics_report(request):
    """Return a CSV output of all crashes for a specific date for a
    particular day and a particular product."""
    if (
        not request.user.is_active or
        not request.user.has_perm('crashstats.run_long_queries')
    ):
        return http.HttpResponseForbidden(
            "You must have the 'Run long queries' permission"
        )
    form = forms.GraphicsReportForm(
        request.GET,
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    api = models.GraphicsReport()
    data = api.get(
        product=form.cleaned_data['product'] or settings.DEFAULT_PRODUCT,
        date=form.cleaned_data['date']
    )
    assert 'hits' in data

    accept_gzip = 'gzip' in request.META.get('HTTP_ACCEPT_ENCODING', '')
    response = http.HttpResponse(content_type='text/csv')
    out = BytesIO()
    writer = utils.UnicodeWriter(out, delimiter='\t')
    writer.writerow(GRAPHICS_REPORT_HEADER)
    for row in data['hits']:
        # Each row is a dict, we want to turn it into a list of
        # exact order as the `header` tuple above.
        # However, because the csv writer module doesn't "understand"
        # python's None, we'll replace those with '' to make the
        # CSV not have the word 'None' where the data is None.
        writer.writerow([
            row[x] is not None and row[x] or ''
            for x in GRAPHICS_REPORT_HEADER
        ])

    payload = out.getvalue()
    if accept_gzip:
        zbuffer = BytesIO()
        zfile = gzip.GzipFile(mode='wb', compresslevel=6, fileobj=zbuffer)
        zfile.write(payload)
        zfile.close()
        compressed_payload = zbuffer.getvalue()
        response.write(compressed_payload)
        response['Content-Length'] = len(compressed_payload)
        response['Content-Encoding'] = 'gzip'
    else:
        response.write(payload)
        response['Content-Length'] = len(payload)
    return response


@pass_default_context
def about_throttling(request, default_context=None):
    """Return a simple page that explains about how throttling works."""
    context = default_context or {}
    return render(request, 'crashstats/about_throttling.html', context)

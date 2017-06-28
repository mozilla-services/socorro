import copy
import json
import datetime
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

from csp.decorators import csp_update

from socorro.lib import BadArgumentError
from socorro.external.crashstorage_base import CrashIDNotFound
from . import forms, models, utils
from .decorators import pass_default_context

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


def get_product_versions_for_crashes_per_day(facets, product):
    versions = facets['version']
    versions = sorted(versions, key=itemgetter('term'), reverse=True)
    return [
        {'product': product, 'version': group['term']}
        for group in versions
    ]


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
        active_versions = context['active_versions'][context['product']]
        for pv in active_versions:
            if pv['is_featured']:
                params['versions'].append(pv['version'])
        if not params['versions'] and active_versions:
            # There were no featured versions, but there were active
            # versions. Use the top X active versions instead.
            for pv in active_versions[:settings.NUMBER_OF_FEATURED_VERSIONS]:
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
    supersearch_params['platform'] = supersearch_params.pop('platforms')
    # in SuperSearch it's called 'Mac' not 'Mac OS X'
    if 'Mac OS X' in supersearch_params['platform']:
        supersearch_params['platform'].append('Mac')
        supersearch_params['platform'].remove('Mac OS X')

    if params['product'] == 'FennecAndroid':
        # FennecAndroid only has one platform and it's "Android"
        # so none of the options presented in the crashes_per_day.html
        # template are applicable.
        del supersearch_params['platform']

    try:
        graph_data, results, adi_by_version = _get_crashes_per_day_with_adu(
            supersearch_params,
            start_date,
            end_date,
            platforms,
            _date_range_type
        )
    except BadArgumentError as exception:
        return http.HttpResponseBadRequest(unicode(exception))

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

    return render(request, 'crashstats/crashes_per_day.html', context)


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
    context['report'] = 'exploitable'
    return render(request, 'crashstats/exploitability_report.html', context)


@csp_update(CONNECT_SRC='analysis-output.telemetry.mozilla.org')
@pass_default_context
def report_index(request, crash_id, default_context=None):
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

    refresh_cache = request.GET.get('refresh') == 'cache'

    raw_api = models.RawCrash()
    try:
        context['raw'] = raw_api.get(
            crash_id=crash_id,
            refresh_cache=refresh_cache,
        )
    except CrashIDNotFound:
        # If the raw crash can't be found, we can't do much.
        tmpl = 'crashstats/report_index_not_found.html'
        return render(request, tmpl, context, status=404)

    context['your_crash'] = (
        request.user.is_active and
        context['raw'].get('Email') == request.user.email
    )

    api = models.UnredactedCrash()
    try:
        context['report'] = api.get(
            crash_id=crash_id,
            refresh_cache=refresh_cache,
        )
    except CrashIDNotFound:
        # ...if we haven't already done so.
        cache_key = 'priority_job:{}'.format(crash_id)
        if not cache.get(cache_key):
            priority_api = models.Priorityjob()
            priority_api.post(crash_ids=[crash_id])
            cache.set(cache_key, True, 60)
        tmpl = 'crashstats/report_index_pending.html'
        return render(request, tmpl, context)

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
    crashing_thread = parsed_dump.get('crash_info', {}).get('crashing_thread')
    if crashing_thread is None:
        # the template does a big `{% if parsed_dump.threads %}`
        parsed_dump['threads'] = None
    else:
        context['crashing_thread'] = crashing_thread

    if context['report']['signature'].startswith('shutdownhang'):
        # For shutdownhang signatures, we want to use thread 0 as the
        # crashing thread, because that's the thread that actually contains
        # the usefull data about the what happened.
        context['crashing_thread'] = 0

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

    context['raw_keys'] = []
    if request.user.has_perm('crashstats.view_pii'):
        # hold nothing back
        context['raw_keys'] = context['raw'].keys()
    else:
        context['raw_keys'] = [
            x for x in context['raw']
            if x in models.RawCrash.API_WHITELIST()
        ]
    # Sort keys case-insensitively
    context['raw_keys'].sort(key=lambda s: s.lower())

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
        if (
            context['raw'].get('ContainsMemoryReport') and
            context['report'].get('memory_report') and
            not context['report'].get('memory_report_error')
        ):
            context['raw_dump_urls'].append(
                reverse(
                    'crashstats:raw_data_named',
                    args=(crash_id, 'memory_report', 'json.gz')
                )
            )

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

    def make_raw_crash_key(key):
        """In the report_index.html template we need to create a key
        that we can use to look up against the 'fields_desc' dict.
        Because you can't do something like this in jinja::

            {{ fields_desc.get(u'raw_crash.{}'.format(key), empty_desc) }}

        we do it here in the function instead.
        The trick is that the lookup key has to be a unicode object or
        else you get UnicodeEncodeErrors in the template rendering.
        """
        return u'raw_crash.{}'.format(key)

    context['make_raw_crash_key'] = make_raw_crash_key
    context['fields_desc'] = descriptions
    context['empty_desc'] = 'No description for this field. Search: unknown'

    context['BUG_PRODUCT_MAP'] = settings.BUG_PRODUCT_MAP

    # report.addons used to be a list of lists.
    # In https://bugzilla.mozilla.org/show_bug.cgi?id=1250132
    # we changed it from a list of lists to a list of strings, using
    # a ':' to split the name and version.
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=1250132#c7
    # Considering legacy, let's tackle both.
    # In late 2017, this code is going to be useless and can be removed.
    if (
        context['report'].get('addons') and
        isinstance(context['report']['addons'][0], (list, tuple))
    ):
        # This is the old legacy format. This crash hasn't been processed
        # the new way.
        context['report']['addons'] = [
            ':'.join(x) for x in context['report']['addons']
        ]

    return render(request, 'crashstats/report_index.html', context)


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


@permission_required('crashstats.view_rawdump')
def raw_data(request, crash_id, extension, name=None):
    api = models.RawCrash()
    if extension == 'json':
        format = 'meta'
        content_type = 'application/json'
    elif extension == 'dmp':
        format = 'raw'
        content_type = 'application/octet-stream'
    elif extension == 'json.gz' and name == 'memory_report':
        # Note, if the name is 'memory_report' it will fetch a raw
        # crash with name and the files in the memory_report bucket
        # are already gzipped.
        # This is important because it means we don't need to gzip
        # the HttpResponse below.
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

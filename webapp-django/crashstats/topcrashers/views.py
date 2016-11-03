import datetime
from collections import defaultdict

from django import http
from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import urlquote

from session_csrf import anonymous_csrf

from crashstats.crashstats import models
from crashstats.crashstats.decorators import (
    check_days_parameter,
    pass_default_context,
)
from crashstats.supersearch.models import SuperSearchUnredacted
from crashstats.supersearch.utils import get_date_boundaries


def datetime_to_build_id(date):
    """Return a build_id-like string from a datetime. """
    return date.strftime('%Y%m%d%H%M%S')


def get_topcrashers_results(**kwargs):
    """Return the results of a search. """
    results = []

    params = kwargs
    range_type = params.pop('_range_type')
    dates = get_date_boundaries(params)

    params['_aggs.signature'] = [
        'platform',
        'is_garbage_collecting',
        'hang_type',
        'process_type',
        'startup_crash',
        '_histogram.uptime',
        '_cardinality.install_time',
    ]
    params['_histogram_interval.uptime'] = 60

    # We don't care about no results, only facets.
    params['_results_number'] = 0

    if params.get('process_type') in ('any', 'all'):
        params['process_type'] = None

    if range_type == 'build':
        params['build_id'] = [
            '>=' + datetime_to_build_id(dates[0]),
            '<' + datetime_to_build_id(dates[1])
        ]

    api = SuperSearchUnredacted()
    search_results = api.get(**params)

    if search_results['total'] > 0:
        results = search_results['facets']['signature']

        platforms = models.Platforms().get_all()['hits']
        platform_codes = [
            x['code'] for x in platforms if x['code'] != 'unknown'
        ]

        for i, hit in enumerate(results):
            hit['signature'] = hit['term']
            hit['rank'] = i + 1
            hit['percent'] = 100.0 * hit['count'] / search_results['total']

            # Number of crash per platform.
            for platform in platform_codes:
                hit[platform + '_count'] = 0

            sig_platforms = hit['facets']['platform']
            for platform in sig_platforms:
                code = platform['term'][:3].lower()
                if code in platform_codes:
                    hit[code + '_count'] = platform['count']

            # Number of crashes happening during garbage collection.
            hit['is_gc_count'] = 0
            sig_gc = hit['facets']['is_garbage_collecting']
            for row in sig_gc:
                if row['term'].lower() == 't':
                    hit['is_gc_count'] = row['count']

            # Number of plugin crashes.
            hit['plugin_count'] = 0
            sig_process = hit['facets']['process_type']
            for row in sig_process:
                if row['term'].lower() == 'plugin':
                    hit['plugin_count'] = row['count']

            # Number of hang crashes.
            hit['hang_count'] = 0
            sig_hang = hit['facets']['hang_type']
            for row in sig_hang:
                # Hangs have weird values in the database: a value of 1 or -1
                # means it is a hang, a value of 0 or missing means it is not.
                if row['term'] in (1, -1):
                    hit['hang_count'] += row['count']

            # Number of crashes happening during startup. This is defined by
            # the client, as opposed to the next method which relies on
            # the uptime of the client.
            hit['startup_count'] = sum(
                row['count'] for row in hit['facets']['startup_crash']
                if row['term'] in ('T', '1')
            )

            # Is a startup crash if more than half of the crashes are happening
            # in the first minute after launch.
            hit['startup_crash'] = False
            sig_uptime = hit['facets']['histogram_uptime']
            for row in sig_uptime:
                # Aggregation buckets use the lowest value of the bucket as
                # term. So for everything between 0 and 60 excluded, the
                # term will be `0`.
                if row['term'] < 60:
                    ratio = 1.0 * row['count'] / hit['count']
                    hit['startup_crash'] = ratio > 0.5

            # Number of distinct installations.
            hit['installs_count'] = (
                hit['facets']['cardinality_install_time']['value']
            )

        # Run the same query but for the previous date range, so we can
        # compare the rankings and show rank changes.
        delta = (dates[1] - dates[0]) * 2
        params['date'] = [
            '>=' + (dates[1] - delta).isoformat(),
            '<' + dates[0].isoformat()
        ]
        params['_aggs.signature'] = [
            'platform',
        ]
        params['_facets_size'] *= 2

        if range_type == 'build':
            params['date'][1] = '<' + dates[1].isoformat()
            params['build_id'] = [
                '>=' + datetime_to_build_id(dates[1] - delta),
                '<' + datetime_to_build_id(dates[0])
            ]

        previous_range_results = api.get(**params)
        total = previous_range_results['total']

        compare_signatures = {}
        if total > 0 and 'signature' in previous_range_results['facets']:
            signatures = previous_range_results['facets']['signature']
            for i, hit in enumerate(signatures):
                compare_signatures[hit['term']] = {
                    'count': hit['count'],
                    'rank': i + 1,
                    'percent': 100.0 * hit['count'] / total
                }

        for hit in results:
            sig = compare_signatures.get(hit['term'])
            if sig:
                hit['diff'] = sig['percent'] - hit['percent']
                hit['rank_diff'] = sig['rank'] - hit['rank']
                hit['previous_percent'] = sig['percent']
            else:
                hit['diff'] = 'new'
                hit['rank_diff'] = 0
                hit['previous_percent'] = 0

    return search_results


@pass_default_context
@anonymous_csrf
@check_days_parameter([1, 3, 7, 14, 28], default=7)
def topcrashers(request, days=None, possible_days=None, default_context=None):
    context = default_context or {}

    product = request.GET.get('product')
    versions = request.GET.getlist('version')
    crash_type = request.GET.get('process_type')
    os_name = request.GET.get('platform')
    result_count = request.GET.get('_facets_size')
    tcbs_mode = request.GET.get('_tcbs_mode')
    range_type = request.GET.get('_range_type')

    range_type = 'build' if range_type == 'build' else 'report'

    if not tcbs_mode or tcbs_mode not in ('realtime', 'byday'):
        tcbs_mode = 'realtime'

    if product not in context['active_versions']:
        raise http.Http404('Unrecognized product')

    context['product'] = product

    if not versions:
        # :(
        # simulate what the nav.js does which is to take the latest version
        # for this product.
        for pv in context['active_versions'][product]:
            if pv['is_featured']:
                url = '%s&version=%s' % (
                    request.build_absolute_uri(), urlquote(pv['version'])
                )
                return redirect(url)

    # See if all versions support builds. If not, refuse to show the "by build"
    # range option in the UI.
    versions_have_builds = True
    for version in versions:
        for pv in context['active_versions'][product]:
            if pv['version'] == version and not pv['has_builds']:
                versions_have_builds = False
                break

    context['versions_have_builds'] = versions_have_builds

    # Used to pick a version in the dropdown menu.
    context['version'] = versions[0]

    if tcbs_mode == 'realtime':
        end_date = timezone.now().replace(microsecond=0)
    elif tcbs_mode == 'byday':
        end_date = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # settings.PROCESS_TYPES might contain tuple to indicate that some
    # are actual labels.
    process_types = []
    for option in settings.PROCESS_TYPES:
        if isinstance(option, (list, tuple)):
            process_types.append(option[0])
        else:
            process_types.append(option)
    if crash_type not in process_types:
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
    context['query'] = {
        'product': product,
        'versions': versions,
        'crash_type': crash_type,
        'os_name': os_name,
        'result_count': unicode(result_count),
        'mode': tcbs_mode,
        'range_type': range_type,
        'end_date': end_date,
        'start_date': end_date - datetime.timedelta(days=days),
    }

    api_results = get_topcrashers_results(
        product=product,
        version=versions,
        platform=os_name,
        process_type=crash_type,
        date=[
            '<' + end_date.isoformat(),
            '>=' + context['query']['start_date'].isoformat()
        ],
        _facets_size=result_count,
        _range_type=range_type,
    )

    if api_results['total'] > 0:
        tcbs = api_results['facets']['signature']
    else:
        tcbs = []

    count_of_included_crashes = 0
    signatures = []
    for crash in tcbs[:int(result_count)]:
        signatures.append(crash['signature'])
        count_of_included_crashes += crash['count']

    context['number_of_crashes'] = count_of_included_crashes
    context['total_percentage'] = api_results['total'] and (
        100.0 * count_of_included_crashes / api_results['total']
    )

    # Get augmented bugs data.
    bugs = defaultdict(list)
    if signatures:
        bugs_api = models.Bugs()
        for b in bugs_api.get(signatures=signatures)['hits']:
            bugs[b['signature']].append(b['id'])

    # Get augmented signature data.
    sig_date_data = {}
    if signatures:
        sig_api = models.SignatureFirstDate()
        # SignatureFirstDate().get_dates() is an optimized version
        # of SignatureFirstDate().get() that returns a dict of
        # signature --> dates.
        first_dates = sig_api.get_dates(signatures)
        for sig, dates in first_dates.items():
            sig_date_data[sig] = dates['first_date']

    for crash in tcbs:
        crash_counts = []
        # Due to the inconsistencies of OS usage and naming of
        # codes and props for operating systems the hacky bit below
        # is required. Socorro and the world will be a better place
        # once https://bugzilla.mozilla.org/show_bug.cgi?id=790642 lands.
        for operating_system in operating_systems:
            if operating_system['name'] == 'Unknown':
                # not applicable in this context
                continue
            os_code = operating_system['code'][0:3].lower()
            key = '%s_count' % os_code
            crash_counts.append([crash[key], operating_system['name']])

        crash['correlation_os'] = max(crash_counts)[1]
        sig = crash['signature']

        # Augment with bugs.
        if sig in bugs:
            if 'bugs' in crash:
                crash['bugs'].extend(bugs[sig])
            else:
                crash['bugs'] = bugs[sig]

        # Augment with first appearance dates.
        if sig in sig_date_data:
            crash['first_report'] = sig_date_data[sig]

        if 'bugs' in crash:
            crash['bugs'].sort(reverse=True)

    context['tcbs'] = tcbs
    context['days'] = days
    context['report'] = 'topcrasher'
    context['possible_days'] = possible_days
    context['total_crashing_signatures'] = len(signatures)
    context['total_number_of_crashes'] = api_results['total']
    context['process_type_values'] = []
    for option in settings.PROCESS_TYPES:
        if option == 'all':
            continue
        if isinstance(option, (list, tuple)):
            value, label = option
        else:
            value = option
            label = option.capitalize()
        context['process_type_values'].append((value, label))

    context['platform_values'] = settings.DISPLAY_OS_NAMES

    return render(request, 'topcrashers/topcrashers.html', context)

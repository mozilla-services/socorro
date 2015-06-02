import json
import datetime
import logging
import math
import isodate
import urllib
from collections import defaultdict
from operator import itemgetter

from django import http
from django.contrib.auth.models import Permission
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.core.cache import cache
from django.utils.http import urlquote

from session_csrf import anonymous_csrf

from . import forms, models, utils
from .decorators import check_days_parameter, pass_default_context
from crashstats.supersearch.models import SuperSearchUnredacted


# To prevent running in to a known Python bug
# (http://bugs.python.org/issue7980)
# we, here at "import time" (as opposed to run time) make use of time.strptime
# at least once
datetime.datetime.strptime('2013-07-15 10:00:00', '%Y-%m-%d %H:%M:%S')


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


def has_builds(product, versions):
    contains_builds = False
    prod_versions = []

    values_separator = '+'
    combinator = ':'

    # Ensure we have versions before proceeding. If there are
    # no verions, simply return the default of False.
    if versions:
        if isinstance(versions, list):
            for version in versions:
                prod_versions.append(product + combinator + version)

            versions = values_separator.join(prod_versions)
        else:
            versions = product + combinator + versions

        api = models.CurrentProducts()
        products = api.get(versions=versions)

        for product in products['hits']:
            if product['has_builds']:
                contains_builds = True
                break

    return contains_builds


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
            t = utils.unixtime(day, millis=True)
            graph_data['ratio%s' % count].append([t, ratio])

    return graph_data


def build_data_object_for_crash_reports(response_items):

    crash_reports = []

    for count, product_version in enumerate(sorted(response_items,
                                                   reverse=True)):
        prod_ver = {}
        prod_ver['product'] = product_version.split(':')[0]
        prod_ver['version'] = product_version.split(':')[1]
        crash_reports.append(prod_ver)

    return crash_reports


def get_all_nightlies(context):
    nightlies_only = settings.NIGHTLY_RELEASE_TYPES

    return [
        x for x in context['currentversions']
        if x['release'].lower() in [rel.lower() for rel in nightlies_only]
    ]


def get_all_nightlies_for_product(context, product):
    nightlies_only = settings.NIGHTLY_RELEASE_TYPES

    versions = []
    for release in context['currentversions']:
        rel_product = release['product']
        rel_release = release['release'].lower()
        if rel_product == product:
            if rel_release in [x.lower() for x in nightlies_only]:
                versions.append(release['version'])

    return versions


def get_latest_nightly(context, product):
    version = None
    for release in context['currentversions']:
        if release['product'] == product:
            rel = release['release']
            if rel.lower() == 'nightly' and release['featured']:
                version = release['version']
                break

    if version is None:
        # We did not find a featured Nightly, let's simply use the latest
        for release in context['currentversions']:
            if release['product'] == product:
                if release['release'].lower() == 'nightly':
                    version = release['version']
                    break

    return version


def get_channel_for_release(version):
    api = models.CurrentProducts()
    version_info = api.get(
        versions=version
    )

    return version_info['hits'][0]['build_type']


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


@pass_default_context
@check_days_parameter([3, 7, 14], default=7)
def home(request, product, versions=None,
         days=None, possible_days=None,
         default_context=None):
    context = default_context or {}
    contains_builds = False
    product = context['product']

    if versions is None:
        versions = []
        for release in default_context['currentversions']:
            if release['product'] == product and release['featured']:
                versions.append(release['version'])
        contains_builds = has_builds(product, versions)
    else:
        versions = versions.split(';')
        contains_builds = has_builds(product, versions)

    context['versions'] = versions
    if len(versions) == 1:
        context['version'] = versions[0]

    context['has_builds'] = contains_builds
    context['days'] = days
    context['possible_days'] = possible_days
    default_date_range_type = request.session.get('date_range_type', 'report')
    context['default_date_range_type'] = default_date_range_type

    return render(request, 'crashstats/home.html', context)


@utils.json_view
@pass_default_context
def frontpage_json(request, default_context=None):
    date_range_types = ['report', 'build']
    form = forms.FrontpageJSONForm(
        default_context['currentversions'],
        data=request.GET,
        date_range_types=date_range_types,
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    product = form.cleaned_data['product']
    versions = form.cleaned_data['versions']
    days = form.cleaned_data['duration']
    assert isinstance(days, int) and days > 0, days

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days + 1)

    if not versions:
        versions = []
        for release in default_context['currentversions']:
            if release['product'] == product and release['featured']:
                current_end_date = (
                    datetime.datetime.strptime(release['end_date'], '%Y-%m-%d')
                )
                if end_date.date() <= current_end_date.date():
                    versions.append(release['version'])

    default = request.session.get('date_range_type', 'report')
    date_range_type = form.cleaned_data['date_range_type'] or default
    assert date_range_type in date_range_types
    request.session['date_range_type'] = date_range_type

    api = models.CrashesPerAdu()
    crashes = api.get(
        product=product,
        versions=versions,
        from_date=start_date.date(),
        to_date=end_date.date(),
        date_range_type=date_range_type
    )

    data = {}
    data = build_data_object_for_adu_graphs(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        crashes['hits']
    )

    # Because we need to always display the links at the bottom of
    # the frontpage, even when there is no data to plot, get the
    # list of prod/versions from the selected list and not from
    # the returned crashes object.
    data['product_versions'] = [
        {'product': product, 'version': x}
        for x in sorted(versions, reverse=True)
    ]

    data['duration'] = days
    data['date_range_type'] = date_range_type

    return data


@pass_default_context
def products_list(request, default_context=None):
    context = default_context or {}
    context['products'] = context['currentproducts']['products']
    return render(request, 'crashstats/products_list.html', context)


@pass_default_context
def explosive(request, product=None, versions=None, default_context=None):
    context = default_context or {}

    # TODO: allow query other periods
    days = 5

    start = datetime.datetime.utcnow() - datetime.timedelta(days)
    start = start.date()

    context['explosives'] = models.ExplosiveCrashes().get(start_date=start)
    context['explosives'] = context['explosives']['hits']

    context['tomorrow'] = {}

    for expl in context['explosives']:
        t = expl['date']
        d = datetime.datetime.strptime(t, '%Y-%m-%d')
        d += datetime.timedelta(1)
        context['tomorrow'][t] = d.strftime('%Y-%m-%d')

    return render(request, 'crashstats/explosive_crashes.html', context)


@pass_default_context
@utils.json_view
def explosive_data(request, signature, date, default_context=None):
    explosive_date = datetime.datetime.strptime(date, '%Y-%m-%d')

    # This is today as the mware does the same thing as range()
    # it doesn't include the last day.
    now = datetime.datetime.utcnow().date() + datetime.timedelta(1)

    # if we are couple days ahead, we only want to draw the days surrounding
    # the explosive crash.
    days_ahead = min(max((now - explosive_date.date()).days, 0), 3)

    end = explosive_date + datetime.timedelta(days_ahead)
    start = (explosive_date -
             datetime.timedelta(settings.EXPLOSIVE_REPORT_DAYS - days_ahead))

    start = start.strftime('%Y-%m-%d')
    end = end.strftime('%Y-%m-%d')
    hits = models.CrashesCountByDay().get(signature=signature,
                                          start_date=start,
                                          end_date=end)['hits']
    hits = sorted(hits.items())

    return {'counts': hits}


@pass_default_context
@anonymous_csrf
@check_days_parameter([3, 7], default=7)
def topcrasher_ranks_bybug(request, days=None, possible_days=None,
                           default_context=None):
    context = default_context or {}

    if request.GET.get('bug_number'):
        try:
            bug_number = int(request.GET.get('bug_number'))
        except ValueError:
            return http.HttpResponseBadRequest('invalid bug number')

        # bug IDs are stored as 32-bit int in Postgres
        if len(bin(bug_number)[2:]) > 32:
            return http.HttpResponseBadRequest('invalid bug number')

        sig_by_bugs_api = models.SignaturesByBugs()
        signatures = sig_by_bugs_api.get(bug_ids=bug_number)['hits']
        context['signatures'] = signatures
        context['bug_number'] = bug_number

        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days)

        top_crashes = defaultdict(dict)

        for signature in signatures:
            signature_summary_api = models.SignatureSummary()
            result = signature_summary_api.get(
                report_types=['products'],
                signature=signature['signature'],
                start_date=start_date,
                end_date=end_date,
            )
            releases = result['reports']['products']

            active = []
            for release in releases:
                for current in context['currentversions']:
                    if (
                        release['product_name'] == current['product']
                        and release['version_string'] == current['version']
                    ):
                        current_end_date = (
                            datetime.datetime.strptime(current['end_date'],
                                                       '%Y-%m-%d')
                        )
                        if end_date.date() <= current_end_date.date():
                            active.append(current)

            signame = signature['signature']
            top_crashes[signame] = defaultdict(dict)

            for release in active:
                product = release['product']
                version = release['version']

                tcbs_api = models.TCBS()
                tcbs = tcbs_api.get(
                    product=product,
                    version=version,
                    end_date=end_date.date(),
                    duration=days * 24,
                    limit=100
                )['crashes']

                for crash in tcbs:
                    if crash['signature'] == signame:
                        top_crashes[signame][product][version] = crash

        context['top_crashes'] = top_crashes

    return render(request, 'crashstats/topcrasher_ranks_bybug.html', context)


@pass_default_context
@anonymous_csrf
@check_days_parameter([1, 3, 7, 14, 28], default=7)
def topcrasher(request, product=None, versions=None, date_range_type=None,
               crash_type=None, os_name=None, result_count='50', days=None,
               possible_days=None, default_context=None):
    context = default_context or {}

    if product not in context['releases']:
        raise http.Http404('Unrecognized product')

    if date_range_type is None:
        date_range_type = request.session.get('date_range_type', 'report')

    if not versions:
        # :(
        # simulate what the nav.js does which is to take the latest version
        # for this product.
        for release in context['currentversions']:
            if release['product'] == product and release['featured']:
                url = reverse('crashstats:topcrasher',
                              kwargs=dict(product=product,
                                          versions=release['version']))
                return redirect(url)
    else:
        versions = versions.split(';')

    if len(versions) == 1:
        context['version'] = versions[0]

    release_versions = [x['version'] for x in context['releases'][product]]
    if context['version'] not in release_versions:
        raise http.Http404('Unrecognized version')

    context['has_builds'] = has_builds(product, context['version'])

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
    request.session['date_range_type'] = date_range_type

    if request.GET.get('format') == 'csv':
        return _render_topcrasher_csv(request, context, product)

    return render(request, 'crashstats/topcrasher.html', context)


def _render_topcrasher_csv(request, context, product):
    response = http.HttpResponse(content_type='text/csv')
    filedate = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    response['Content-Disposition'] = ('attachment; filename="%s_%s_%s.csv"' %
                                       (product, context['version'], filedate))
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

    context['products'] = context['currentproducts']['products']

    form_selection = request.GET.get('form_selection')

    platforms_api = models.Platforms()
    platforms = platforms_api.get()

    if form_selection == 'by_os':
        form_class = forms.DailyFormByOS
    else:
        form_selection = 'by_version'
        form_class = forms.DailyFormByVersion

    date_range_types = ['report', 'build']
    hang_types = ['any', 'crash', 'hang-p']

    form = form_class(
        context['currentversions'],
        platforms,
        data=request.GET,
        date_range_types=date_range_types,
        hang_types=hang_types,
    )
    if form.is_valid():
        params = form.cleaned_data
        params['product'] = params.pop('p')
        params['versions'] = params.pop('v')
        try:
            params['os_names'] = params.pop('os')
        except KeyError:
            params['os_names'] = None
    else:
        return http.HttpResponseBadRequest(str(form.errors))

    if len(params['versions']) > 0:
        context['version'] = params['versions'][0]

    context['form_selection'] = form_selection
    context['product'] = params['product']

    if not params['versions']:
        # need to pick the default featured ones
        params['versions'] = [
            version['version']
            for version in context['currentversions']
            if version['product'] == params['product'] and version['featured']
        ]

    context['available_versions'] = []
    now = datetime.datetime.utcnow().date()
    for version in context['currentversions']:
        start_date = isodate.parse_date(version['start_date'])
        end_date = isodate.parse_date(version['end_date'])
        if (
            params['product'] == version['product'] and
            start_date <= now and
            end_date >= now
        ):
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

    default = request.session.get('date_range_type', 'report')
    context['date_range_type'] = params.get('date_range_type') or default

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
        form_selection=form_selection,
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
        if form_selection == 'by_version':
            data_table['dates'][date] = sorted(data_table['dates'][date],
                                               key=itemgetter('version'),
                                               reverse=True)
        else:
            data_table['dates'][date] = sorted(data_table['dates'][date],
                                               key=itemgetter('os'),
                                               reverse=True)

    if request.GET.get('format') == 'csv':
        return _render_daily_csv(
            request,
            data_table,
            params['product'],
            params['versions'],
            platforms,
            context['os_names'],
            form_selection
        )
    context['data_table'] = data_table
    context['graph_data'] = json.dumps(cadu)
    context['report'] = 'daily'

    return render(request, 'crashstats/daily.html', context)


def _render_daily_csv(request, data, product, versions, platforms, os_names,
                      form_selection):
    response = http.HttpResponse('text/csv', content_type='text/csv')
    title = 'ADI_' + product + '_' + '_'.join(versions) + '_' + form_selection
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
    if form_selection == 'by_version':
        for version in versions:
            for __, label in labels:
                head_row.append('%s %s %s' % (product, version, label))
    elif form_selection == 'by_os':
        for os_name in os_names:
            for version in versions:
                for __, label in labels:
                    head_row.append(
                        '%s %s on %s %s' %
                        (product, version, os_name, label)
                    )
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

         Or, if form_selection=='by_os' it would look like this:
           [{'os': 'Linux',
             'adu': 4500,
             'crash_hadu': 43.0,
             'date': u'2012-10-13',
             'product': u'WaterWolf',
             'report_count': 1935,
             'throttle': 1.0,
             'version': u'4.0a2'},
            {'os': 'Windows',
             'adu': 4500,
             'crash_hadu': 43.0,
             'date': u'2012-10-13',
             'product': u'WaterWolf',
             'report_count': 1935,
             'throttle': 1.0,
             'version': u'4.0a2'},
             ]
        """
        row = [date]
        info_by_version = dict((x['version'], x) for x in crash_info)

        if form_selection == 'by_version':
            # Turn each of them into a dict where the keys is the version
            for version in versions:
                if version in info_by_version:
                    blob = info_by_version[version]
                    append_row_blob(blob, labels)
                else:
                    for __ in labels:
                        row.append('-')
        elif form_selection == 'by_os':
            info_by_os = dict((x['os'], x) for x in crash_info)
            for os_name in os_names:
                blob = info_by_os[os_name]
                append_row_blob(blob, labels)
        else:
            raise NotImplementedError(form_selection)  # pragma: no cover

        assert len(row) == len(head_row), (len(row), len(head_row))
        writer.writerow(row)

    # add the totals
    totals_labels = (
        ('crashes', 'Crashes'),
        ('adu', 'ADI'),
        ('throttle', 'Throttle'),
        ('ratio', 'Ratio'),
    )
    row = ['Total']

    for version in versions:
        if form_selection == 'by_os':
            for platform in platforms:
                product_version_platform = '%s:%s:%s' % (product, version,
                                                         platform['code'])
                try:
                    blob = data['totals'][product_version_platform]
                except KeyError:
                    continue
                append_row_blob(blob, totals_labels)
        else:
            product_version = '%s:%s' % (product, version)
            try:
                blob = data['totals'][product_version]
            except KeyError:
                continue
            append_row_blob(blob, totals_labels)
    writer.writerow(row)
    return response


@pass_default_context
@check_days_parameter([3, 7, 14, 28], 7)
def topchangers(request, product=None, versions=None,
                days=None, possible_days=None,
                default_context=None):
    context = default_context or {}

    if not versions:
        versions = []
        # select all current versions, if none are chosen
        for release in context['currentversions']:
            if release['product'] == product and release['featured']:
                versions.append(release['version'])
    else:
        versions = versions.split(';')

    context['days'] = days
    context['possible_days'] = possible_days
    context['versions'] = versions
    if len(versions) == 1:
        context['version'] = versions[0]

    context['product_versions'] = []
    for version in versions:
        context['product_versions'].append('%s:%s' % (product, version))

    end_date = datetime.datetime.utcnow()

    # FIXME hardcoded crash_type
    crash_type = 'browser'

    changers = defaultdict(list)
    api = models.TCBS()
    for v in versions:
        tcbs = api.get(
            product=product,
            version=v,
            crash_type=crash_type,
            end_date=end_date.date(),
            date_range_type='report',
            duration=days * 24,
            limit='300'
        )

        for crash in tcbs['crashes']:
            if crash['changeInRank'] != 'new' and crash['signature']:
                change = int(crash['changeInRank'])
                changers[change].append(crash)

    context['topchangers'] = changers
    context['report'] = 'topchangers'

    return render(request, 'crashstats/topchangers.html', context)


@pass_default_context
@permission_required('crashstats.view_exploitability')
def exploitable_crashes(
    request,
    product=None,
    versions=None,
    default_context=None
):
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
    return render(request, 'crashstats/exploitability.html', context)


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

    if 'InstallTime' in context['raw']:
        try:
            install_time = datetime.datetime.fromtimestamp(
                int(context['raw']['InstallTime'])
            )
            context['install_time'] = (
                install_time.strftime('%Y-%m-%d %H:%M:%S')
            )
        except ValueError:
            # that means the `InstallTime` value was not valid.
            # that's just as good or bad as it not being in the raw crash
            logging.debug(
                'Raw crash contains invalid `InstallTime`: %r',
                context['raw']['InstallTime']
            )

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

    correlations_api = models.CorrelationsSignatures()
    total_correlations = 0
    if 'os_name' in context['report']:
        platform = context['report']['os_name']
        for report_type in settings.CORRELATION_REPORT_TYPES:
            try:
                correlations = correlations_api.get(
                    report_type=report_type,
                    product=context['report']['product'],
                    version=context['report']['version'],
                    platforms=platform)
                hits = correlations['hits'] if correlations else []
                if context['report']['signature'] in hits:
                    total_correlations += 1
            except models.BadStatusCodeError:
                # correlations failure should not block view
                # bug 1005224 will move this to an asynchronous client
                # request instead.
                pass

    context['total_correlations'] = total_correlations
    context['BUG_PRODUCT_MAP'] = settings.BUG_PRODUCT_MAP

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
        models.ProductsVersions().get(),
        models.CurrentVersions().get(),
        models.Platforms().get(),
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
            os=form.cleaned_data['platform'],
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
        os_count = defaultdict(int)
        version_count = defaultdict(int)

        for report in context['report_list']['hits']:
            os_name = report['os_name']
            version = report['version']

            # report_list does not contain beta identifier, but the correlation
            # form needs it for validation
            if report['release_channel'].lower() == 'beta':
                version = version + 'b'

            os_count[os_name] += 1
            version_count[version] += 1

            report['date_processed'] = isodate.parse_datetime(
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
                        install_time = isodate.parse_datetime(
                            install_time
                        )
                # put it back into the report
                report['install_time'] = install_time.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )

        if os_count:
            correlation_os = max(os_count.iterkeys(),
                                 key=lambda k: os_count[k])
        else:
            correlation_os = None
        context['correlation_os'] = correlation_os

        if version_count:
            correlation_version = max(version_count.iterkeys(),
                                      key=lambda k: version_count[k])
        else:
            correlation_version = None
        if correlation_version is None:
            correlation_version = ''
        context['correlation_version'] = correlation_version

        correlations_api = models.CorrelationsSignatures()
        total_correlations = 0
        if correlation_version and correlation_os:
            for report_type in settings.CORRELATION_REPORT_TYPES:
                correlations = correlations_api.get(
                    report_type=report_type,
                    product=context['product'],
                    version=correlation_version,
                    platforms=correlation_os
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
            os=form.cleaned_data['platform'],
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
            context['channel'] = get_channel_for_release(
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
            models.ProductsVersions().get(),
            data,
            auto_id=True
        )

    if not partial:
        # prep it so it's nicer to work with in the template
        context['all_reports_columns'] = [
            {'value': x[0], 'label': x[1], 'default': x[2]}
            for x in ALL_REPORTS_COLUMNS
        ]

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

    form = forms.ADUBySignatureJSONForm(
        settings.CHANNELS,
        models.ProductsVersions().get(),
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


@pass_default_context
def status(request, default_context=None):
    response = models.Status().get()
    stats = response['hits']

    # transform some of the data to be plotted, store it seperately
    plot_data = {}
    attributes = [
        'avg_process_sec',
        'avg_wait_sec',
        'waiting_job_count',
        'processors_count',
        'date_created'
    ]
    for a in attributes:
        plucked = list(reversed([x.get(a) for x in stats]))
        if a is 'date_created':
            plucked = map(lambda x: utils.parse_isodate(x, "%H:%M"), plucked)
        plot_data[a] = [list(x) for x in enumerate(plucked)]

    # format the dates in place for display in the table
    attributes = ['date_created',
                  'date_recently_completed',
                  'date_oldest_job_queued']
    for stat in stats:
        for attribute in attributes:
            stat[attribute] = utils.parse_isodate(stat[attribute])

    if stats:
        first_stat = stats[0]
    else:
        first_stat = None

    context = default_context or {}
    context.update({
        'data': stats,
        'stat': first_stat,
        'plot_data': plot_data,
        'socorro_revision': response['socorro_revision'],
        'breakpad_revision': response['breakpad_revision'],
        'schema_revision': response['schema_revision'],
    })
    return render(request, 'crashstats/status.html', context)


def status_json(request):
    response = http.HttpResponse(
        models.Status().get(decode_json=False),
        content_type='application/json; charset=UTF-8'
    )
    response['Access-Control-Allow-Origin'] = '*'
    return response


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
@login_required
def your_crashes(request, default_context=None):
    """Shows a logged in user a list of his or her recent crash reports. """
    context = default_context or {}

    one_month_ago = (
        datetime.datetime.utcnow() - datetime.timedelta(weeks=4)
    ).isoformat()

    api = SuperSearchUnredacted()
    results = api.get(
        email=request.user.email,
        date='>%s' % one_month_ago,
        _columns=['date', 'uuid'],
    )

    context['crashes_list'] = [
        dict(zip(('crash_id', 'date'), (x['uuid'], x['date'])))
        for x in results['hits']
    ]

    return render(request, 'crashstats/your_crashes.html', context)


@pass_default_context
def login(request, default_context=None):
    context = default_context or {}
    return render(request, 'crashstats/login.html', context)


@pass_default_context
@login_required
def permissions(request, default_context=None):
    context = default_context or {}
    context['permissions'] = (
        Permission.objects.filter(content_type__model='')
        .order_by('name')
    )
    return render(request, 'crashstats/permissions.html', context)


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

    bugs = form.cleaned_data['bug_ids']
    fields = form.cleaned_data['include_fields']

    bzapi = models.BugzillaBugInfo()
    result = bzapi.get(bugs, fields)
    # store all of these in a cache
    for bug in result['bugs']:
        if 'id' in bug:
            cache_key = 'buginfo:%s' % bug['id']
            cache.set(cache_key, bug, 60 * 60)  # one hour
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


@utils.json_view
def signature_summary(request):

    form = forms.SignatureSummaryForm(
        models.ProductsVersions().get(),
        models.CurrentVersions().get(),
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
    signature_summary = {}

    results = api.get(
        report_types=report_types.keys(),
        signature=signature,
        start_date=start_date,
        end_date=end_date,
        versions=version,
    )
    for r, name in report_types.items():
        result[name] = results['reports'][r]
        signature_summary[name] = []

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
            signature_summary['exploitabilityScore'].append({
                'report_date': r['report_date'],
                'null_count': r['null_count'],
                'low_count': r['low_count'],
                'medium_count': r['medium_count'],
                'high_count': r['high_count'],
            })
    else:
        result.pop('exploitabilityScore')
        signature_summary.pop('exploitabilityScore')

    # because in python we use pep8 under_scored style in js we use camelCase
    signature_summary['canViewExploitability'] = can_view_exploitability

    def format_float(number):
        return '%.2f' % float(number)

    for r in result['architectures']:
        signature_summary['architectures'].append({
            'architecture': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['percentageByOs']:
        signature_summary['percentageByOs'].append({
            'os': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['productVersions']:
        signature_summary['productVersions'].append({
            'product': r['product_name'],
            'version': r['version_string'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['uptimeRange']:
        signature_summary['uptimeRange'].append({
            'range': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['processTypes']:
        signature_summary['processTypes'].append({
            'processType': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['flashVersions']:
        signature_summary['flashVersions'].append({
            'flashVersion': r['category'],
            'percentage': format_float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['distinctInstall']:
        signature_summary['distinctInstall'].append({
            'product': r['product_name'],
            'version': r['version_string'],
            'crashes': r['crashes'],
            'installations': r['installations']})
    for r in result['devices']:
        signature_summary['devices'].append({
            'cpu_abi': r['cpu_abi'],
            'manufacturer': r['manufacturer'],
            'model': r['model'],
            'version': r['version'],
            'report_count': r['report_count'],
            'percentage': r['percentage'],
        })
    for r in result['graphics']:
        vendor_name = r['vendor_name'] or r['vendor_hex']
        adapter_name = r['adapter_name'] or r['adapter_hex']
        signature_summary['graphics'].append({
            'vendor': vendor_name,
            'adapter': adapter_name,
            'report_count': r['report_count'],
            'percentage': r['percentage'],
        })

    return signature_summary


@pass_default_context
@anonymous_csrf
def gccrashes(request, product, version=None, default_context=None):
    context = default_context or {}
    versions = get_all_nightlies_for_product(context, product)

    if version is None:
        # No version was passed get the latest nightly
        version = get_latest_nightly(context, product)

    current_products = context['currentproducts']['products']

    context['report'] = 'gccrashes'
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


@pass_default_context
def crash_trends(request, product, versions=None, default_context=None):
    context = default_context or {}
    context['product'] = product
    context['report'] = 'crash_trends'

    version = get_latest_nightly(context, product)

    context['version'] = version
    context['end_date'] = datetime.datetime.utcnow()
    context['start_date'] = context['end_date'] - datetime.timedelta(days=7)

    context['products'] = context['currentproducts']

    url = reverse('crashstats:crashtrends_json')
    params = {
        'product': product,
        'version': version,
        'start_date': context['start_date'].strftime('%Y-%m-%d'),
        'end_date': context['end_date'].strftime('%Y-%m-%d')
    }
    url += '?' + urllib.urlencode(params)
    context['data_url'] = url

    return render(request, 'crashstats/crash_trends.html', context)


@utils.json_view
@pass_default_context
def get_nightlies_for_product_json(request, default_context=None):
    return get_all_nightlies_for_product(
        default_context,
        request.GET.get('product')
    )


@utils.json_view
@pass_default_context
def crashtrends_json(request, default_context=None):
    nightly_versions = get_all_nightlies(default_context)

    form = forms.CrashTrendsForm(nightly_versions, request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    product = form.cleaned_data['product']
    version = form.cleaned_data['version']
    start_date = form.cleaned_data['start_date']
    end_date = form.cleaned_data['end_date']

    api = models.CrashTrends()
    response = api.get(
        product=product,
        version=version,
        start_date=start_date.date(),
        end_date=end_date.date()
    )

    formatted = {}
    for report in response['crashtrends']:
        report_date = report['report_date']
        if report_date not in formatted:
            formatted[report_date] = [0, 0, 0, 0, 0, 0, 0, 0, 0]
            if report['days_out'] >= 8:
                formatted[report_date][8] += report['report_count']
            else:
                days_out = int(report['days_out'])
                formatted[report_date][days_out] += report['report_count']

    json_response = {
        'crashtrends': formatted,
        'total': len(formatted)
    }

    return json_response


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
def correlations_json(request):

    form = forms.CorrelationsJSONForm(
        models.ProductsVersions().get(),
        models.CurrentVersions().get(),
        models.Platforms().get(),
        request.GET
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    report_type = form.cleaned_data['correlation_report_type']
    product = form.cleaned_data['product']
    version = form.cleaned_data['version']
    # correlations does not differentiate betas since it works on raw data
    if version.endswith('b'):
        version = version.split('b')[0]
    platform = form.cleaned_data['platform']
    signature = form.cleaned_data['signature']

    api = models.Correlations()
    return api.get(report_type=report_type, product=product, version=version,
                   platform=platform, signature=signature)


@utils.json_view
def correlations_signatures_json(request):

    form = forms.CorrelationsSignaturesJSONForm(
        models.ProductsVersions().get(),
        models.CurrentVersions().get(),
        models.Platforms().get(),
        request.GET
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    report_type = form.cleaned_data['correlation_report_type']
    product = form.cleaned_data['product']
    version = form.cleaned_data['version']
    platforms = form.cleaned_data['platforms']

    api = models.CorrelationsSignatures()
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
    return result

import os
import json
import datetime
import logging
import math
import isodate
import urllib
from collections import defaultdict
from operator import itemgetter

from django import http
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.contrib.auth.decorators import login_required

from session_csrf import anonymous_csrf

from . import forms, models, utils
from .decorators import check_days_parameter, pass_default_context


# To prevent running in to a known Python bug
# (http://bugs.python.org/issue7980)
# we, here at "import time" (as opposed to run time) make use of time.strptime
# at least once
datetime.datetime.strptime('2013-07-15 10:00:00', '%Y-%m-%d %H:%M:%S')


def robots_txt(request):
    return http.HttpResponse(
        'User-agent: *\n'
        '%s: /' % ('Allow' if settings.ENGAGE_ROBOTS else 'Disallow'),
        mimetype='text/plain',
    )


def favicon_ico(request):
    """return the favicon with the content type forced so we don't have to
    rely on `mimetypes` to guess it non-deterministically per OS.

    The reason for doing /favicon.ico in django instead of setting up
    an Apache rewrite rule is to reduce complexity. Having it here means
    it's predictable and means fewer things to go wrong outside just getting
    this up and running.
    """
    filename = os.path.join(settings.STATIC_ROOT, 'img', 'favicon.ico')
    return http.HttpResponse(open(filename).read(), mimetype='image/x-icon')


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

    if not versions:
        versions = []
        for release in default_context['currentversions']:
            if release['product'] == product and release['featured']:
                versions.append(release['version'])

    default = request.session.get('date_range_type', 'report')
    date_range_type = form.cleaned_data['date_range_type'] or default
    assert date_range_type in date_range_types
    request.session['date_range_type'] = date_range_type

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days + 1)

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
    context['products'] = models.CurrentProducts().get()['products']
    return render(request, 'crashstats/products_list.html', context)


@pass_default_context
def explosive(request, product=None, versions=None, default_context=None):
    context = default_context or {}

    # TODO: allow query other periods
    days = 5

    start = datetime.datetime.utcnow() - datetime.timedelta(days)
    start = start.strftime('%Y-%m-%d')

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
@check_days_parameter([1, 3, 7, 14, 28], default=7)
def topcrasher(request, product=None, versions=None, date_range_type=None,
               crash_type=None, os_name=None, days=None, possible_days=None,
               default_context=None):
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
                url = reverse('crashstats.topcrasher',
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
    if os_name not in (os['name'] for os in operating_systems):
        os_name = None

    context['os_name'] = os_name

    api = models.TCBS()
    tcbs = api.get(
        product=product,
        version=context['version'],
        crash_type=crash_type,
        end_date=end_date,
        date_range_type=date_range_type,
        duration=(days * 24),
        limit='300',
        os=os_name
    )
    signatures = [c['signature'] for c in tcbs['crashes']]

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
        for os in operating_systems:
            os_code = os['code'][0:3].lower()
            key = '%s_count' % os_short_name_binding.get(os_code, os_code)
            crash_counts.append([crash[key], os['name']])

        crash['correlation_os'] = max(crash_counts)[1]
        sig = crash['signature']
        if sig in bugs:
            if 'bugs' in crash:
                crash['bugs'].extend(bugs[sig])
            else:
                crash['bugs'] = bugs[sig]

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
    response = http.HttpResponse(mimetype='text/csv', content_type='text/csv')
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

    context['products'] = models.CurrentProducts().get()['products']

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

    end_date = params.get('date_end') or datetime.datetime.utcnow().date()
    start_date = (params.get('date_start') or
                  end_date - datetime.timedelta(weeks=2))

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
    response = http.HttpResponse(mimetype='text/csv', content_type='text/csv')
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
def builds(request, product=None, versions=None, default_context=None):
    context = default_context or {}

    # the model DailyBuilds only takes 1 version if possible.
    # however, the way our default_context decorator works we have to call it
    # versions (plural) even though we here don't support that
    if versions is not None:
        assert isinstance(versions, basestring)
        context['version'] = versions

    context['report'] = 'builds'
    api = models.DailyBuilds()
    middleware_results = api.get(product=product, version=versions)
    builds = defaultdict(list)
    for build in middleware_results:
        if build['build_type'] != 'Nightly':
            continue
        key = '%s%s' % (build['date'], build['version'])
        build['date'] = datetime.datetime.strptime(
            build['date'],
            '%Y-%m-%d'
        )
        builds[key].append(build)

    # lastly convert it to a list of tuples
    all_builds = []
    # sort by the key but then ignore it...
    for __, individual_builds in sorted(builds.items(), reverse=True):
        # ...by using the first item to get the date and version
        first_build = individual_builds[0]
        all_builds.append((
            first_build['date'],
            first_build['version'],
            individual_builds
        ))

    context['all_builds'] = all_builds
    return render(request, 'crashstats/builds.html', context)


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
            end_date=end_date,
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
@login_required
def exploitable_crashes(request, default_context=None):
    context = default_context or {}

    page = max(1, int(request.GET.get('page', 1)))

    context['current_page'] = page

    results_per_page = settings.EXPLOITABILITY_BATCH_SIZE

    exploitable_crashes = models.CrashesByExploitability()
    exploitable = exploitable_crashes.get(
        page=page,
        batch=results_per_page
    )
    context['crashes'] = exploitable['hits']
    context['pages'] = int(math.ceil(
        1.0 * exploitable['total'] / results_per_page
    ))

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
            'crashstats.report_index',
            args=(valid_crash_id,)
        ))

    context = default_context or {}
    context['crash_id'] = crash_id

    api = models.ProcessedCrash()

    try:
        context['report'] = api.get(crash_id=crash_id)
    except models.BadStatusCodeError as e:
        if str(e).startswith('404'):
            # if crash was submitted today, send to pending screen
            crash_date = datetime.datetime.strptime(crash_id[-6:], '%y%m%d')
            crash_age = datetime.datetime.utcnow() - crash_date
            if crash_age < datetime.timedelta(days=1):
                tmpl = 'crashstats/report_index_pending.html'
            else:
                tmpl = 'crashstats/report_index_not_found.html'
            return render(request, tmpl, context)
        elif str(e).startswith('408'):
            return render(request,
                          'crashstats/report_index_pending.html', context)
        elif str(e).startswith('410'):
            return render(request,
                          'crashstats/report_index_too_old.html', context)
        else:
            raise

    context['bug_product_map'] = settings.BUG_PRODUCT_MAP

    process_type = 'unknown'
    if context['report']['process_type'] is None:
        process_type = 'browser'
    elif context['report']['process_type'] == 'plugin':
        process_type = 'plugin'
    elif context['report']['process_type'] == 'content':
        process_type = 'content'
    context['process_type'] = process_type

    context['product'] = context['report']['product']
    context['version'] = context['report']['version']

    parsed_dump = utils.parse_dump(
        context['report']['dump'],
        settings.VCS_MAPPINGS
    )
    # parsed_dump['threads'] is all threads.
    # We're going to show
    # `parsed_dump['threads'][parsed_dump['crashed_thread']]`
    # first and then all other threads
    parsed_dump['remaining_threads'] = dict(
        (k, v) for (k, v) in
        parsed_dump['threads'].items()
        if k != parsed_dump['crashed_thread']
    )
    context['parsed_dump'] = parsed_dump

    bugs_api = models.Bugs()
    hits = bugs_api.get(signatures=[context['report']['signature']])['hits']
    # bugs_api.get(signatures=...) will return all signatures associated
    # with the bugs found, but we only want those with matching signature
    context['bug_associations'] = [
        x for x in hits
        if x['signature'] == context['report']['signature']
    ]

    raw_api = models.RawCrash()
    context['raw'] = raw_api.get(crash_id=crash_id)

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

    if 'HangID' in context['raw']:
        context['hang_id'] = context['raw']['HangID']
        crash_pair_api = models.CrashPairsByCrashId()
        context['crash_pairs'] = crash_pair_api.get(
            uuid=context['report']['uuid'],
            hang_id=context['hang_id']
        )

    context['raw_dump_urls'] = [
        reverse('crashstats.raw_data', args=(crash_id, 'dmp')),
        reverse('crashstats.raw_data', args=(crash_id, 'json'))
    ]

    correlations_api = models.CorrelationsSignatures()
    total_correlations = 0
    if 'os_name' in context['report']:
        platform = context['report']['os_name']
        for report_type in settings.CORRELATION_REPORT_TYPES:
            correlations = correlations_api.get(report_type=report_type,
                                                product=context['product'],
                                                version=context['version'],
                                                platforms=platform)
            hits = correlations['hits'] if correlations else []
            if context['report']['signature'] in hits:
                total_correlations += 1

    context['total_correlations'] = total_correlations
    return render(request, 'crashstats/report_index.html', context)


@utils.json_view
def report_pending(request, crash_id):
    if not crash_id:
        raise http.Http404("Crash id is missing")

    data = {}

    url = reverse('crashstats.report_index', kwargs=dict(crash_id=crash_id))

    api = models.ProcessedCrash()

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

    if partial == 'reports':
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
            result_number=results_per_page,
            result_offset=result_offset
        )
        current_query = request.GET.copy()
        if 'page' in current_query:
            del current_query['page']
        context['current_url'] = '%s?%s' % (reverse('crashstats.report_list'),
                                            current_query.urlencode())

        if not context['report_list']['hits']:
            return render(
                request,
                'crashstats/partials/no_data.html',
                context
            )

        context['signature'] = context['report_list']['hits'][0]['signature']

        context['report_list']['total_pages'] = int(math.ceil(
            context['report_list']['total'] / float(results_per_page)))

        context['report_list']['total_count'] = context['report_list']['total']

    if partial == 'correlations':
        os_count = defaultdict(int)
        version_count = defaultdict(int)

        api = models.ReportList()
        report_list = api.get(
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
            result_number=results_per_page,
            result_offset=result_offset
        )

        for report in report_list['hits']:
            os_name = report['os_name']
            version = report['version']

            os_count[os_name] += 1
            version_count[version] += 1

            report['date_processed'] = isodate.parse_datetime(
                report['date_processed']
            ).strftime('%b %d, %Y %H:%M')

            report['install_time'] = isodate.parse_datetime(
                report['install_time']
            ).strftime('%Y-%m-%d %H:%M:%S')

        correlation_os = max(os_count.iterkeys(), key=lambda k: os_count[k])
        context['correlation_os'] = correlation_os

        correlation_version = max(version_count.iterkeys(),
                                  key=lambda k: version_count[k])
        if correlation_version is None:
            correlation_version = ''
        context['correlation_version'] = correlation_version

        correlations_api = models.CorrelationsSignatures()
        total_correlations = 0
        for report_type in settings.CORRELATION_REPORT_TYPES:
            correlations = correlations_api.get(report_type=report_type,
                                                product=context['product'],
                                                version=correlation_version,
                                                platforms=correlation_os)
            hits = correlations['hits'] if correlations else []
            if context['signature'] in hits:
                total_correlations += 1
        context['total_correlations'] = total_correlations

    versions = []
    for product_version in context['product_versions']:
        versions.append(product_version.split(':')[1])

    if partial == 'table' or partial == 'graph':
        context['table'] = {}
        if partial == 'graph':
            context['counts'] = {
                'Win': [],
                'Mac': [],
                'Lin': [],
                'XAXIS_TICKS': [],
            }
        crashes_frequency_api = models.CrashesFrequency()
        builds = crashes_frequency_api.get(
            signature=context['signature'],
            products=[context['product']],
            versions=versions
        )['hits']

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
            if partial == 'graph':
                context['counts']['Win'].append([i, build['count_windows']])
                context['counts']['Mac'].append([i, build['count_mac']])
                context['counts']['Lin'].append([i, build['count_linux']])
                context['counts']['XAXIS_TICKS'].append([i, buildid])

    # signature URLs only if you're logged in
    if partial == 'sigurls':
        if request.user.is_active:
            signatureurls_api = models.SignatureURLs()
            sigurls = signatureurls_api.get(
                signature=context['signature'],
                products=[context['product']],
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

    if partial == 'bugzilla':
        bugs_api = models.Bugs()
        context['bug_associations'] = bugs_api.get(
            signatures=[context['signature']]
        )['hits']

        match_total = 0
        for bug in context['bug_associations']:
            # Only add up bugs where it matches the signature exactly.
            if bug['signature'] == context['signature']:
                match_total += 1

        context['bugsig_match_total'] = match_total

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


@pass_default_context
def crontabber_state(request, default_context=None):
    response = models.CrontabberState().get()
    last_updated = response['last_updated']

    last_updated = (
        isodate.parse_datetime(last_updated)
        .replace(tzinfo=utc)
    )
    context = default_context or {}
    context['last_updated'] = last_updated
    return render(request, 'crashstats/crontabber_state.html', context)


@utils.json_view
def crontabber_state_json(request):
    response = models.CrontabberState().get()
    return {'state': response['state']}


@pass_default_context
def login(request, default_context=None):
    context = default_context or {}
    return render(request, 'crashstats/login.html', context)


@pass_default_context
def query(request, default_context=None):
    context = default_context or {}
    products = models.ProductsVersions().get()
    versions = models.CurrentVersions().get()
    platforms = models.Platforms().get()

    form = forms.QueryForm(products, versions, platforms, request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    if form.cleaned_data['query_type']:
        query_type = form.cleaned_data['query_type']
        if (query_type in settings.QUERY_TYPES_MAP):
            query_type = settings.QUERY_TYPES_MAP[query_type]
    else:
        query_type = settings.QUERY_TYPES[0]

    if query_type == 'simple':
        # If the query looks like a crash id and the form was the simple one,
        # go to report/index directly, without running a search.
        crash_id = utils.find_crash_id(form.cleaned_data['query'])
        if crash_id:
            url = reverse('crashstats.report_index',
                          kwargs=dict(crash_id=crash_id))
            return redirect(url)
        # The 'simple' value is a special case used only with the form on top
        # of our pages. It should be turned into 'contains' before doing
        # anything else as 'simple' as a query type makes no sense for the
        # middleware.
        query_type = 'contains'

    results_per_page = 100

    if form.cleaned_data['version']:
        # We need to extract just the version number for use with the
        # navigation version select drop-down.
        selected_version = form.cleaned_data['version'][0].split(':')[1]
        context['version'] = selected_version

    if form.cleaned_data['product']:
        selected_products = form.cleaned_data['product']
    else:
        selected_products = [settings.DEFAULT_PRODUCT]

    context['product'] = selected_products[0]

    if not form.cleaned_data['date']:
        date = datetime.datetime.utcnow()
        # This is an optimization for elasticsearch.
        # If the user supplies a value for 'date', we just use that but
        # if no value is sent, then the default one is less precise,
        # which means users will often use the same value for date
        # (assuming they don't change that value).
        # In the backend, we end up with more common date filters
        # thus improving performance.
        date = date.replace(minute=0, second=0, microsecond=0)
    else:
        date = form.cleaned_data['date']

    try:
        context['current_page'] = int(request.GET.get('page', 1))
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    previous_page = context['current_page'] - 1
    context['results_offset'] = results_per_page * previous_page

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']
    context['current_url'] = '%s?%s' % (reverse('crashstats.query'),
                                        current_query.urlencode())

    context['products'] = products

    if form.cleaned_data['range_unit']:
        range_unit = form.cleaned_data['range_unit']
    else:
        range_unit = settings.RANGE_UNITS[0]

    # 'all' is here for backwards compatibility, it's an alias of 'any'
    process_type = form.cleaned_data['process_type']
    if not process_type or process_type == 'all':
        process_type = settings.PROCESS_TYPES[0]

    hang_type = form.cleaned_data['hang_type']
    if not hang_type or hang_type == 'all':
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

    current_products = defaultdict(list)
    now = datetime.datetime.utcnow().date()
    for product in products:
        for release in products[product]:
            start_date = isodate.parse_date(release['start_date'])
            end_date = isodate.parse_date(release['end_date'])

            if now >= start_date and now <= end_date:
                current_products[product].append(release)

    context['products_json'] = json.dumps(current_products)
    context['platforms'] = platforms

    params = {
        'signature': form.cleaned_data['signature'],
        'query': form.cleaned_data['query'],
        'products': selected_products,
        'versions': form.cleaned_data['version'],
        'platforms': form.cleaned_data['platform'],
        'end_date': date,
        'date_range_unit': range_unit,
        'date_range_value': form.cleaned_data['range_value'],
        'query_type': query_type,
        'reason': form.cleaned_data['reason'],
        'release_channels': form.cleaned_data['release_channels'],
        'build_id': form.cleaned_data['build_id'],
        'process_type': process_type,
        'hang_type': hang_type,
        'plugin_field': plugin_field,
        'plugin_query_type': plugin_query_type,
        'plugin_query': form.cleaned_data['plugin_query']
    }
    if params['build_id']:
        params['build_id'] = [unicode(x) for x in params['build_id']]

    params['platforms_names'] = [
        p['name'] for p in platforms
        if p['code'] in params['platforms']
    ]

    context['params'] = params
    context['params_json'] = json.dumps({'versions': params['versions'],
                                         'products': params['products']})

    context['query'] = {
        'total': 0,
        'total_count': 0,
        'total_pages': 0
    }

    if (request.GET.get('do_query') or
            request.GET.get('date') or
            request.GET.get('query')):
        api = models.Search()

        date_delta = get_timedelta_from_value_and_unit(
            int(params['date_range_value']),
            params['date_range_unit']
        )

        if request.user.is_authenticated():
            # The user is an admin and is allowed to perform bigger queries
            max_query_range = settings.QUERY_RANGE_MAXIMUM_DAYS_ADMIN
            error_type = 'exceeded_maximum_date_range_admin'
        else:
            max_query_range = settings.QUERY_RANGE_MAXIMUM_DAYS
            error_type = 'exceeded_maximum_date_range'

        # Check whether the user tries to run a big query, and limit it
        if date_delta.days > max_query_range:
            # Display an error
            context['error'] = {
                'type': error_type,
                'data': {
                    'maximum': max_query_range,
                    'default': settings.QUERY_RANGE_DEFAULT_DAYS
                }
            }
            # And change the date range to its default value
            params['date_range_unit'] = 'days'
            params['date_range_value'] = settings.QUERY_RANGE_DEFAULT_DAYS
            date_delta = datetime.timedelta(days=params['date_range_value'])

        start_date = params['end_date'] - date_delta

        force_api_impl = request.GET.get(
            '_force_api_impl',
            settings.SEARCH_MIDDLEWARE_IMPL
        )

        search_results = api.get(
            terms=params['query'],
            products=params['products'],
            versions=params['versions'],
            os=params['platforms'],
            start_date=start_date.isoformat(),
            end_date=params['end_date'].isoformat(),
            search_mode=params['query_type'],
            reasons=params['reason'],
            release_channels=params['release_channels'],
            build_ids=params['build_id'],
            report_process=params['process_type'],
            report_type=params['hang_type'],
            plugin_in=params['plugin_field'],
            plugin_search_mode=params['plugin_query_type'],
            plugin_terms=params['plugin_query'],
            result_number=results_per_page,
            result_offset=context['results_offset'],
            _force_api_impl=force_api_impl
        )

        search_results['total_pages'] = int(math.ceil(
            search_results['total'] / float(results_per_page)))
        search_results['total_count'] = search_results['total']

        # Bugs for each signature
        signatures = [h['signature'] for h in search_results['hits']]

        if signatures:
            bugs = defaultdict(list)
            bugs_api = models.Bugs()
            for b in bugs_api.get(signatures=signatures)['hits']:
                bugs[b['signature']].append(b['id'])

            for hit in search_results['hits']:
                sig = hit['signature']
                if sig in bugs:
                    if 'bugs' in hit:
                        hit['bugs'].extend(bugs[sig])
                    else:
                        hit['bugs'] = bugs[sig]

        context['query'] = search_results

        # Building the query_string for links to report/list
        query_params = {
            'product': params['products'],
            'version': params['versions'],
            'platform': params['platforms'],
            'query_type': params['query_type'],
            'date': params['end_date'].strftime('%Y-%m-%d %H:%M:%S'),
            'range_value': params['date_range_value'],
            'range_unit': params['date_range_unit'],
            'reason': params['reason'],
            'release_channels': params['release_channels'],
            'build_id': params['build_id'],
            'hang_type': params['hang_type'],
            'process_type': params['process_type']
        }
        if params['hang_type'] == 'plugin':
            query_params += {
                'plugin_field': params['plugin_field'],
                'plugin_query_type': params['plugin_query_type'],
                'plugin_query': params['plugin_query']
            }
        context['report_list_query_string'] = (
            urllib.urlencode(utils.sanitize_dict(query_params), True))

    return render(request, 'crashstats/query.html', context)


@utils.json_view
def buginfo(request, signatures=None):
    form = forms.BugInfoForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    bugs = form.cleaned_data['bug_ids']
    fields = form.cleaned_data['include_fields']

    bzapi = models.BugzillaBugInfo()
    return bzapi.get(bugs, fields)


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
        'graphics': 'graphics'
    }

    # Only authenticated users get this report.
    if request.user.is_authenticated():
        report_types['exploitability'] = 'exploitabilityScore'

    api = models.SignatureSummary()

    result = {}
    signature_summary = {}
    for r in report_types:
        name = report_types[r]
        result[name] = api.get(
            report_type=r,
            signature=signature,
            start_date=start_date,
            end_date=end_date,
            versions=version,
        )
        signature_summary[name] = []

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

    # Only authenticated users get this report.
    if request.user.is_authenticated():
        for r in result['exploitabilityScore']:
            signature_summary['exploitabilityScore'].append({
                'report_date': r['report_date'],
                'null_count': r['null_count'],
                'low_count': r['low_count'],
                'medium_count': r['medium_count'],
                'high_count': r['high_count'],
            })

    return signature_summary


@pass_default_context
def crash_trends(request, product, versions=None, default_context=None):
    context = default_context or {}
    context['product'] = product
    context['report'] = 'crash_trends'

    for release in context['currentversions']:
        if release['product'] == product:
            # For crash trends we only want the latest, featured Nightly
            if release['release'] == 'Nightly' and release['featured']:
                version = release['version']

    context['version'] = version
    context['end_date'] = datetime.datetime.utcnow()
    context['start_date'] = context['end_date'] - datetime.timedelta(days=7)

    api = models.CurrentProducts()
    current_products = api.get()

    context['products'] = current_products

    url = reverse('crashstats.crashtrends_json')
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
def crashtrends_versions_json(request, default_context=None):
    product = request.GET.get('product')

    versions = []
    for release in default_context['currentversions']:
        rel_product = release['product']
        rel_release = release['release']
        if rel_product == product:
            if rel_release == 'Nightly' or rel_release == 'Aurora':
                versions.append(release['version'])

    return versions


@utils.json_view
@pass_default_context
def crashtrends_json(request, default_context=None):
    nightlies_only = settings.NIGHTLY_RELEASE_TYPES
    # For the crash trends report we should only collect products
    # which has nightly builds and as such, only nightly versions
    # for each product. (Aurora forms part of this)
    nightly_versions = [
        x for x in default_context['currentversions']
        if x['release'] in nightlies_only
    ]

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


def raw_data(request, crash_id, extension):
    if not request.user.is_active:
        return http.HttpResponseForbidden("Must be logged in")

    api = models.RawCrash()
    if extension == 'json':
        format = 'meta'
        content_type = 'application/json'
    elif extension == 'dmp':
        format = 'raw'
        content_type = 'application/octet-stream'
    else:
        raise NotImplementedError(extension)

    data = api.get(crash_id=crash_id, format=format)
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

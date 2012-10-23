import json
import datetime
import functools
import math
import isodate
import urllib

from collections import defaultdict
from operator import itemgetter
from django import http
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.syndication.views import Feed

from session_csrf import anonymous_csrf

from . import models
from . import forms
from . import utils
from .decorators import check_days_parameter


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
        products = api.get(versions)

        for product in products['hits']:
            if product['has_builds']:
                contains_builds = True
                break

    return contains_builds


def build_data_object_for_adu_graphs(start_date,
                                     end_date,
                                     response_items,
                                     report_type='by_version'):
    count = len(response_items)
    graph_data = {
        'startDate': start_date,
        'endDate': end_date,
        'count': count
    }

    for count, product_version in enumerate(sorted(response_items,
                                                   reverse=True),
                                            start=1):

        graph_data['ratio%s' % count] = []

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


# Returns the product display names of all products in the database
def get_product_names():
    products = []
    products_model = models.CurrentProducts()
    response = products_model.get()

    for product in response['hits']:
        products.append(product['product_name'])

    return products


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


def set_base_data(view):

    def _basedata(product=None, versions=None):
        """
        from @product and @versions transfer to
        a dict. If there's any left-over, raise a 404 error
        """
        data = {}
        api = models.CurrentVersions()
        data['currentversions'] = api.get()
        if versions is None:
            versions = []
        else:
            versions = versions.split(';')

        for release in data['currentversions']:
            if product == release['product']:
                data['product'] = product
                if release['version'] in versions:
                    versions.remove(release['version'])
                    if 'versions' not in data:
                        data['versions'] = []
                    data['versions'].append(release['version'])

        if product is None:
            # thus a view that doesn't have a product in the URL
            # e.g. like /query
            if not data.get('product'):
                data['product'] = settings.DEFAULT_PRODUCT
        elif product != data.get('product'):
            raise http.Http404("Not a recognized product")

        if product and versions:
            raise http.Http404("Not a recognized version for that product")

        data['releases'] = utils.build_releases(data['currentversions'])

        return data

    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        product = kwargs.get('product', None)
        versions = kwargs.get('versions', None)
        for key, value in _basedata(product, versions).items():
            setattr(request, key, value)
        return view(request, *args, **kwargs)

    return inner


@set_base_data
@check_days_parameter([3, 7, 14], default=7)
def home(request, product, versions=None):
    data = {}
    contains_builds = False
    days = request.days
    product = request.product

    if versions is None:
        versions = []
        for release in request.currentversions:
            if release['product'] == product and release['featured']:
                versions.append(release['version'])
        contains_builds = has_builds(product, versions)
    else:
        versions = versions.split(';')
        contains_builds = has_builds(product, versions)

    data['versions'] = versions
    if len(versions) == 1:
        data['version'] = versions[0]

    data['has_builds'] = contains_builds
    data['days'] = days

    return render(request, 'crashstats/home.html', data)


@utils.json_view
@set_base_data
def frontpage_json(request):
    product = request.GET.get('product')
    version = request.GET.get('version')
    days = request.GET.get('duration')
    if days is None:
        days = 7
    else:
        days = int(days)

    params = {
        'product': product,
        'version': version,
        'duration': days
    }

    if 'date_range_type' not in request.GET:
        params['date_range_type'] = 'report'
    else:
        params['date_range_type'] = request.GET.get('date_range_type')

    if version is None:
        versions = []
        for release in request.currentversions:
            if release['product'] == product and release['featured']:
                versions.append(release['version'])
    else:
        versions = version.split(';')

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days + 1)

    api = models.CrashesPerAdu()
    response = api.get(
        product=product,
        versions=versions,
        start_date=start_date.date(),
        end_date=end_date.date(),
        date_range_type=params['date_range_type']
    )

    cadu = {}
    cadu = build_data_object_for_adu_graphs(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        response['hits']
    )
    cadu['product_versions'] = build_data_object_for_crash_reports(
        response['hits']
    )

    cadu['duration'] = days
    cadu['date_range_type'] = params['date_range_type']

    return cadu


@set_base_data
def products_list(request):
    data = {}

    api = models.CurrentProducts()
    products = api.get()

    data['products'] = products['hits']

    return render(request, 'crashstats/products_list.html', data)


@set_base_data
@anonymous_csrf
@check_days_parameter([1, 3, 7, 14, 28], default=7)
def topcrasher(request, product=None, versions=None, date_range_type='report',
               crash_type=None, os_name=None):
    data = {}

    if not versions:
        # :(
        # simulate what the nav.js does which is to take the latest version
        # for this product.
        for release in request.currentversions:
            if release['product'] == product and release['featured']:
                url = reverse('crashstats.topcrasher',
                              kwargs=dict(product=product,
                                          versions=release['version']))
                return redirect(url)
    else:
        versions = versions.split(';')

    if len(versions) == 1:
        data['version'] = versions[0]

    data['has_builds'] = has_builds(product, data['version'])

    days = request.days
    end_date = datetime.datetime.utcnow()

    if crash_type not in ['all', 'browser', 'plugin', 'content']:
        crash_type = 'browser'

    data['crash_type'] = crash_type

    if os_name not in settings.OPERATING_SYSTEMS:
        os_name = None

    data['os_name'] = os_name

    api = models.TCBS()
    tcbs = api.get(
        product,
        data['version'],
        crash_type,
        end_date,
        date_range_type,
        duration=(days * 24),
        limit='300'
    )
    signatures = [c['signature'] for c in tcbs['crashes']]

    bugs = defaultdict(list)
    api = models.Bugs()
    for b in api.get(signatures)['hits']:
        bugs[b['signature']].append(b['id'])

    for crash in tcbs['crashes']:
        sig = crash['signature']
        if sig in bugs:
            if 'bugs' in crash:
                crash['bugs'].extend(bugs[sig])
            else:
                crash['bugs'] = bugs[sig]

    data['tcbs'] = tcbs
    data['report'] = 'topcrasher'
    data['days'] = days
    data['total_crashing_signatures'] = len(signatures)
    data['date_range_type'] = date_range_type

    if request.GET.get('format') == 'csv':
        return _render_topcrasher_csv(request, data, product)

    return render(request, 'crashstats/topcrasher.html', data)


def _render_topcrasher_csv(request, data, product):
    response = http.HttpResponse(mimetype='text/csv', content_type='text/csv')
    file_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    response['Content-Disposition'] = (
        'attachment; filename="%s_%s_%s.csv"'
        % (product, data['version'], file_date)
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
                     'Version Count',
                     'Versions'])
    for crash in data['tcbs']['crashes']:

        writer.writerow([crash['currentRank'],
                         crash['changeInRank'],
                         crash['percentOfTotal'],
                         crash['previousPercentOfTotal'],
                         crash['signature'],
                         crash['count'],
                         crash['win_count'],
                         crash['mac_count'],
                         crash['linux_count'],
                         crash['versions_count'],
                         crash['versions']])

    return response


@set_base_data
def daily(request):
    data = {}

    # legacy fix
    if 'v[]' in request.GET or 'os[]' in request.GET:
        new_url = (request.build_absolute_uri()
                   .replace('v[]', 'v')
                   .replace('os[]', 'os'))
        return redirect(new_url, permanent=True)

    data['products'] = get_product_names()

    form_selection = request.GET.get('form_selection')

    platforms_api = models.Platforms()
    platforms = platforms_api.get()

    if form_selection == 'by_os':
        form_class = forms.DailyFormByOS
    else:
        form_selection = 'by_version'
        form_class = forms.DailyFormByVersion

    form = form_class(
        request.currentversions,
        platforms,
        data=request.GET,
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

    data['form_selection'] = form_selection

    data['product'] = params['product']

    if not params['versions']:
        # need to pick the default featured ones
        params['versions'] = [
            x['version']
            for x in request.currentversions
            if x['product'] == params['product'] and x['featured']
        ]
    data['versions'] = params['versions']

    if not params.get('os_names'):
        params['os_names'] = [x['name'] for x in platforms]

    data['os_names'] = params.get('os_names')

    end_date = params.get('end_date') or datetime.datetime.utcnow().date()
    start_date = (params.get('start_date') or
                  end_date - datetime.timedelta(weeks=2))

    data['start_date'] = start_date.strftime('%Y-%m-%d')
    data['end_date'] = end_date.strftime('%Y-%m-%d')

    data['duration'] = abs((start_date - end_date).days)
    data['dates'] = utils.daterange(start_date, end_date)

    data['hang_type'] = params.get('hang_type') or 'any'

    data['date_range_type'] = params.get('date_range_type') or 'report'

    api = models.CrashesPerAdu()
    crashes = api.get(
        product=params['product'],
        versions=params['versions'],
        from_date=start_date,
        to_date=end_date,
        date_range_type=params['date_range_type'],
        os=params['os_names'],
        form_selection=form_selection
    )

    cadu = {}
    cadu = build_data_object_for_adu_graphs(
        data['start_date'],
        data['end_date'],
        crashes['hits']
    )
    cadu['product_versions'] = build_data_object_for_crash_reports(
        crashes['hits'])

    data_table = {
        'totals': {},
        'dates': {}
    }
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
            if date not in data_table['dates']:
                data_table['dates'][date] = []
            data_table['dates'][date].append(crash_info)
            data_table['totals'][
                product_version]['crashes'] += crash_info['report_count']
            data_table['totals'][product_version]['adu'] += crash_info['adu']
            if 'throttle' in crash_info:
                data_table['totals'][
                    product_version]['throttle'] = crash_info['throttle']
            data_table['totals'][
                product_version]['ratio'] += crash_info['crash_hadu']

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
            form_selection
        )
    data['data_table'] = data_table

    data['graph_data'] = json.dumps(cadu)
    data['report'] = 'daily'

    return render(request, 'crashstats/daily.html', data)


def _render_daily_csv(request, data, product, versions, form_selection):
    response = http.HttpResponse(mimetype='text/csv', content_type='text/csv')
    title = 'ADU_' + product + '_' + '_'.join(versions) + '_' + form_selection
    response['Content-Disposition'] = (
        'attachment; filename="%s.csv"' % title
    )
    writer = utils.UnicodeWriter(response)
    head_row = ['Date']
    labels = (
        ('report_count', 'Crashes'),
        ('adu', 'ADU'),
        ('throttle', 'Throttle'),
        ('crash_hadu', 'Ratio'),
    )
    for version in versions:
        for __, label in labels:
            head_row.append('%s %s %s' % (product, version, label))
    writer.writerow(head_row)

    # reverse so that recent dates appear first
    for date in sorted(data['dates'].keys(), reverse=True):
        info = data['dates'][date]
        # `info` is a dict that looks something like this:
        #   {'adu': 4500,
        #    'crash_hadu': 43.0,
        #    'date': u'2012-10-13',
        #    'product': u'WaterWolf',
        #    'report_count': 1935,
        #    'throttle': 1.0,
        #    'version': u'4.0a2'},
        # Turn each of them into a dict where the keys is the version
        info_by_version = dict((x['version'], x) for x in info)
        row = [date]
        for version in versions:
            if version in info_by_version:
                blob = info_by_version[version]
                for key, __ in labels:
                    value = blob[key]
                    if key == 'throttle':
                        value = '%.1f%%' % (100.0 * value)
                    elif key == 'crash_hadu':
                        value = '%.1f%%' % value
                    else:
                        value = str(value)
                    row.append(value)
            else:
                for __ in labels:
                    row.append('-')
        assert len(row) == len(head_row)
        writer.writerow(row)

    # add the totals
    totals_labels = (
        ('crashes', 'Crashes'),
        ('adu', 'ADU'),
        ('throttle', 'Throttle'),
        ('ratio', 'Ratio'),
    )
    row = ['Total']
    for version in versions:
        blob = data['totals']['%s:%s' % (product, version)]
        for key, __ in totals_labels:
            value = blob[key]
            if key == 'throttle':
                value = '%.1f%%' % (100.0 * value)
            elif key == 'ratio':
                value = '%.1f%%' % value
            else:
                value = str(value)
            row.append(value)
    writer.writerow(row)
    return response


@set_base_data
def builds(request, product=None, versions=None):
    data = {}

    # the model DailyBuilds only takes 1 version if possible.
    # however, the way our set_base_data decorator works we have to call it
    # versions (plural) even though we here don't support that
    if versions is not None:
        assert isinstance(versions, basestring)

        request.version = versions  # so it's available in the template

    data['report'] = 'builds'
    api = models.DailyBuilds()
    middleware_results = api.get(product, version=versions)
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

    data['all_builds'] = all_builds
    return render(request, 'crashstats/builds.html', data)


@set_base_data
@check_days_parameter([3, 7, 14, 28], 7)
def hangreport(request, product=None, versions=None, listsize=100):
    data = {}
    try:
        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    days = request.days
    end_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')

    # FIXME refactor into common function
    if not versions:
        # simulate what the nav.js does which is to take the latest version
        # for this product.
        for release in request.currentversions:
            if release['product'] == product and release['featured']:
                url = reverse('crashstats.hangreport',
                              kwargs=dict(product=product,
                                          versions=release['version']))
                return redirect(url)
    else:
        versions = versions.split(';')[0]

    data['version'] = versions

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']
    data['current_url'] = '%s?%s' % (reverse('crashstats.hangreport',
                                     args=[product, versions]),
                                     current_query.urlencode())

    api = models.HangReport()
    data['hangreport'] = api.get(product, versions, end_date, days,
                                 listsize, page)

    data['hangreport']['total_pages'] = data['hangreport']['totalPages']
    data['hangreport']['total_count'] = data['hangreport']['totalCount']

    data['report'] = 'hangreport'
    if page > data['hangreport']['totalPages'] > 0:
        # naughty parameter, go to the last page
        if isinstance(versions, (list, tuple)):
            versions = ';'.join(versions)
        url = reverse('crashstats.hangreport',
                      args=[product, versions])
        url += ('?days=%s&page=%s'
                % (days, data['hangreport']['totalPages']))
        return redirect(url)

    data['current_page'] = page
    data['days'] = days
    return render(request, 'crashstats/hangreport.html', data)


@set_base_data
@check_days_parameter([3, 7, 14, 28], 7)
def topchangers(request, product=None, versions=None):
    data = {}

    days = request.days

    if not versions:
        # :(
        # simulate what the nav.js does which is to take the latest version
        # for this product.
        for release in request.currentversions:
            if release['product'] == product and release['featured']:
                url = reverse('crashstats.topchangers',
                              kwargs=dict(product=product,
                                          versions=release['version']))
                return redirect(url)
    else:
        versions = versions.split(';')

    data['days'] = days
    data['versions'] = versions
    if len(versions) == 1:
        data['version'] = versions[0]

    end_date = datetime.datetime.utcnow()

    # FIXME hardcoded crash_type
    crash_type = 'browser'

    changers = defaultdict(list)
    api = models.TCBS()
    for v in versions:
        tcbs = api.get(product, v, crash_type, end_date,
                       'report', duration=days * 24, limit='300')

        for crash in tcbs['crashes']:
            if crash['changeInRank'] != 'new':
                change = int(crash['changeInRank'])
                if change <= 0:
                    continue
                changers[change].append(crash)

    data['topchangers'] = changers

    data['report'] = 'topchangers'
    return render(request, 'crashstats/topchangers.html', data)


@set_base_data
def report_index(request, crash_id):
    data = {
        'crash_id': crash_id
    }

    api = models.ProcessedCrash()

    try:
        data['report'] = api.get(crash_id)
    except models.BadStatusCodeError as e:
        if str(e).startswith('404'):
            return render(request,
                          'crashstats/report_index_not_found.html', data)
        elif str(e).startswith('408'):
            return render(request,
                          'crashstats/report_index_pending.html', data)
        elif str(e).startswith('410'):
            return render(request, 'crashstats/report_index_too_old.html')

    data['bug_product_map'] = settings.BUG_PRODUCT_MAP

    process_type = 'unknown'
    if data['report']['process_type'] is None:
        process_type = 'browser'
    elif data['report']['process_type'] == 'plugin':
        process_type = 'plugin'
    elif data['report']['process_type'] == 'content':
        process_type = 'content'
    data['process_type'] = process_type

    data['product'] = data['report']['product']
    data['version'] = data['report']['version']

    data['parsed_dump'] = utils.parse_dump(data['report']['dump'],
                                           settings.VCS_MAPPINGS)

    bugs_api = models.Bugs()
    data['bug_associations'] = bugs_api.get(
        [data['report']['signature']]
    )['hits']

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=14)

    comments_api = models.CommentsBySignature()
    data['comments'] = comments_api.get(data['report']['signature'],
                                        start_date, end_date)

    raw_api = models.RawCrash()
    data['raw'] = raw_api.get(crash_id)

    if 'HangID' in data['raw']:
        data['hang_id'] = data['raw']['HangID']

        crash_pair_api = models.CrashPairsByCrashId()
        data['crash_pairs'] = crash_pair_api.get(
            data['report']['uuid'],
            data['hang_id']
        )

    data['raw_dump_urls'] = [
        reverse('crashstats.raw_data', args=(crash_id, 'dump')),
        reverse('crashstats.raw_data', args=(crash_id, 'json'))
    ]

    return render(request, 'crashstats/report_index.html', data)


@utils.json_view
def report_pending(request, crash_id):
    data = {}

    url = reverse('crashstats.report_index', kwargs=dict(crash_id=crash_id))

    api = models.ProcessedCrash()

    try:
        data['report'] = api.get(crash_id)
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


@set_base_data
def report_list(request):
    data = {}
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
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    data['current_page'] = page

    signature = form.cleaned_data['signature']
    product_version = form.cleaned_data['version']
    end_date = form.cleaned_data['date']
    duration = get_timedelta_from_value_and_unit(
        int(form.cleaned_data['range_value']),
        form.cleaned_data['range_unit']
    )
    data['current_day'] = duration.days

    start_date = end_date - duration
    data['start_date'] = start_date.strftime('%Y-%m-%d')
    data['end_date'] = end_date.strftime('%Y-%m-%d')

    results_per_page = 250
    result_offset = results_per_page * (page - 1)

    api = models.ReportList()
    data['report_list'] = api.get(
        signature=signature,
        products=form.cleaned_data['product'],
        versions=product_version,
        os=form.cleaned_data['platform'],
        start_date=start_date,
        end_date=end_date,
        build_ids=form.cleaned_data['build_id'],
        reasons=form.cleaned_data['reason'],
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
    data['current_url'] = '%s?%s' % (reverse('crashstats.report_list'),
                                     current_query.urlencode())

    if not data['report_list']['hits']:
        data['signature'] = signature
        return render(request, 'crashstats/report_list_no_data.html', data)

    data['product'] = data['report_list']['hits'][0]['product']
    data['version'] = data['report_list']['hits'][0]['version']
    data['signature'] = data['report_list']['hits'][0]['signature']

    data['report_list']['total_pages'] = int(math.ceil(
        data['report_list']['total'] / float(results_per_page)))

    data['report_list']['total_count'] = data['report_list']['total']

    data['comments'] = []
    data['table'] = {}
    data['crashes'] = []

    for report in data['report_list']['hits']:
        buildid = report['build']
        os_name = report['os_name']

        report['date_processed'] = isodate.parse_datetime(
            report['date_processed']
        ).strftime('%b %d, %Y %H:%M')

        report['install_time'] = isodate.parse_datetime(
            report['install_time']
        ).strftime('%Y-%m-%d %H:%M:%S')

        data['hits'] = report

        if buildid not in data['table']:
            data['table'][buildid] = {}
        if 'total' not in data['table'][buildid]:
            data['table'][buildid]['total'] = 1
        else:
            data['table'][buildid]['total'] += 1

        if os_name not in data['table'][buildid]:
            data['table'][buildid][os_name] = 1
        else:
            data['table'][buildid][os_name] += 1

    # signature URLs only if you're logged in
    data['signature_urls'] = None
    if request.user.is_active:
        signatureurls_api = models.SignatureURLs()
        sigurls = signatureurls_api.get(
            data['signature'],
            [data['product']],
            [data['version']],
            start_date,
            end_date
        )
        data['signature_urls'] = sigurls['hits']

    comments_api = models.CommentsBySignature()
    data['comments'] = comments_api.get(data['signature'],
                                        start_date, end_date)

    bugs_api = models.Bugs()
    data['bug_associations'] = bugs_api.get(
        [data['signature']]
    )['hits']

    return render(request, 'crashstats/report_list.html', data)


@set_base_data
def status(request):
    response = models.Status().get()
    stats = response['hits']

    def parse(ds, format_string="%b %d %Y %H:%M:%S"):
        '''parses iso8601 date string and returns a truncated
        string representation suitable for display on the status page

        '''
        if not ds:
            return ""
        return isodate.parse_datetime(ds).strftime(format_string)

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
            plucked = map(lambda x: parse(x, "%H:%M"), plucked)
        plot_data[a] = [list(x) for x in enumerate(plucked)]

    # format the dates in place for display in the table
    attributes = ['date_created',
                  'date_recently_completed',
                  'date_oldest_job_queued']
    for stat in stats:
        for attribute in attributes:
            stat[attribute] = parse(stat[attribute])

    data = {
        'data': stats,
        'stat': stats[0],
        'plot_data': plot_data,
        'socorro_revision': response['socorro_revision'],
        'breakpad_revision': response['breakpad_revision']
    }
    return render(request, 'crashstats/status.html', data)


@set_base_data
def query(request):
    form = forms.QueryForm(
        models.ProductsVersions().get(),
        models.CurrentVersions().get(),
        models.Platforms().get(),
        request.GET
    )
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    # If the query looks like an ooid and the form was the simple one, go to
    # report/index directly, without running a search.
    query_type = form.cleaned_data['query_type']
    if query_type == 'simple':
        ooid = utils.has_ooid(form.cleaned_data['query'])
        if ooid:
            url = reverse('crashstats.report_index',
                          kwargs=dict(crash_id=ooid))
            return redirect(url)
        # The 'simple' value is a special case used only with the form on top
        # of our pages. It should be turned into 'contains' before doing
        # anything else as 'simple' as a query type makes no sense for the
        # middleware.
        query_type = 'contains'

    results_per_page = 100
    data = {}

    try:
        data['current_page'] = int(request.GET.get('page', 1))
    except ValueError:
        return http.HttpResponseBadRequest('Invalid page')

    data['results_offset'] = results_per_page * (data['current_page'] - 1)

    current_query = request.GET.copy()
    if 'page' in current_query:
        del current_query['page']
    data['current_url'] = '%s?%s' % (reverse('crashstats.query'),
                                     current_query.urlencode())

    products = models.ProductsVersions().get()
    data['products'] = products
    data['products_json'] = json.dumps(products)

    platforms = models.Platforms().get()
    data['platforms'] = platforms

    params = {
        'signature': form.cleaned_data['signature'],
        'query': form.cleaned_data['query'],
        'products': form.cleaned_data['product'],
        'versions': form.cleaned_data['version'],
        'platforms': form.cleaned_data['platform'],
        'end_date': form.cleaned_data['date'],
        'date_range_unit': form.cleaned_data['range_unit'],
        'date_range_value': form.cleaned_data['range_value'],
        'query_type': query_type,
        'reason': form.cleaned_data['reason'],
        'build_id': form.cleaned_data['build_id'],
        'process_type': form.cleaned_data['process_type'],
        'hang_type': form.cleaned_data['hang_type'],
        'plugin_field': form.cleaned_data['plugin_field'],
        'plugin_query_type': form.cleaned_data['plugin_query_type'],
        'plugin_query': form.cleaned_data['plugin_query']
    }

    data['params'] = params
    data['params_json'] = json.dumps(
        {
            'versions': params['versions'],
            'products': params['products']
        }
    )

    data['query'] = {
        'total': 0,
        'total_count': 0,
        'total_pages': 0
    }

    if (
        request.GET.get('product') or
        request.GET.get('versions') or
        request.GET.get('end_date') or
        request.GET.get('query')):
        api = models.Search()

        date_delta = get_timedelta_from_value_and_unit(
            int(params['date_range_value']),
            params['date_range_unit']
        )
        start_date = params['end_date'] - date_delta

        if 'ALL:ALL' in params['versions']:
            params['versions'].remove('ALL:ALL')

        search_results = api.get(
            terms=params['query'],
            products=params['products'],
            versions=params['versions'],
            os=params['platforms'],
            start_date=start_date.isoformat(),
            end_date=params['end_date'].isoformat(),
            search_mode=params['query_type'],
            reasons=params['reason'],
            build_ids=params['build_id'],
            report_process=params['process_type'],
            report_type=params['hang_type'],
            plugin_in=params['plugin_field'],
            plugin_search_mode=params['plugin_query_type'],
            plugin_terms=params['plugin_query'],
            result_number=results_per_page,
            result_offset=data['results_offset']
        )

        search_results['total_pages'] = int(math.ceil(
            search_results['total'] / float(results_per_page)))
        search_results['total_count'] = search_results['total']

        # Bugs for each signature
        signatures = [h['signature'] for h in search_results['hits']]

        if signatures:
            bugs = defaultdict(list)
            bugs_api = models.Bugs()
            for b in bugs_api.get(signatures)['hits']:
                bugs[b['signature']].append(b['id'])

            for hit in search_results['hits']:
                sig = hit['signature']
                if sig in bugs:
                    if 'bugs' in hit:
                        hit['bugs'].extend(bugs[sig])
                    else:
                        hit['bugs'] = bugs[sig]

        data['query'] = search_results

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
        data['report_list_query_string'] = (
            urllib.urlencode(utils.sanitize_dict(query_params), True))

    return render(request, 'crashstats/query.html', data)


@utils.json_view
def buginfo(request, signatures=None):
    form = forms.BugInfoForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    bugs = form.cleaned_data['bug_ids']
    fields = form.cleaned_data['include_fields']

    bzapi = models.BugzillaBugInfo()
    return bzapi.get(bugs, fields)


@set_base_data
@utils.json_view
def plot_signature(request, product, versions, start_date, end_date,
                   signature):
    date_format = '%Y-%m-%d'
    try:
        start_date = datetime.datetime.strptime(start_date, date_format)
        end_date = datetime.datetime.strptime(end_date, date_format)
    except ValueError, msg:
        return http.HttpResponseBadRequest(str(msg))

    diff = end_date - start_date
    duration = diff.days * 24.0 + diff.seconds / 3600.0

    api = models.SignatureTrend()
    sigtrend = api.get(product, versions, signature, end_date, duration)

    graph_data = {
        'startDate': sigtrend['start_date'],
        'signature': sigtrend['signature'],
        'endDate': sigtrend['end_date'],
        'counts': [],
        'percents': [],
    }

    for s in sigtrend['signatureHistory']:
        t = utils.unixtime(s['date'], millis=True)
        graph_data['counts'].append([t, s['count']])
        graph_data['percents'].append([t, (s['percentOfTotal'] * 100)])

    return graph_data


@utils.json_view
def signature_summary(request):

    range_value = int(request.GET.get('range_value'))
    # FIXME only support "days"
    signature = request.GET.get('signature')

    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=range_value)

    report_types = {
        'architecture': 'architectures',
        'flash_version': 'flashVersions',
        'os': 'percentageByOs',
        'process_type': 'processTypes',
        'products': 'productVersions',
        'uptime': 'uptimeRange'
    }

    api = models.SignatureSummary()

    result = {}
    signature_summary = {}
    for r in report_types:
        name = report_types[r]
        result[name] = api.get(r, signature, start_date, end_date)
        signature_summary[name] = []

    # FIXME fix JS so it takes above format..
    for r in result['architectures']:
        signature_summary['architectures'].append({
            'architecture': r['category'],
            'percentage': '%.2f' % (float(r['percentage']) * 100),
            'numberOfCrashes': r['report_count']})
    for r in result['percentageByOs']:
        signature_summary['percentageByOs'].append({
            'os': r['category'],
            'percentage': '%.2f' % (float(r['percentage']) * 100),
            'numberOfCrashes': r['report_count']})
    for r in result['productVersions']:
        signature_summary['productVersions'].append({
            'product': r['product_name'],
            'version': r['version_string'],
            'percentage': '%.2f' % float(r['percentage']),
            'numberOfCrashes': r['report_count']})
    for r in result['uptimeRange']:
        signature_summary['uptimeRange'].append({
            'range': r['category'],
            'percentage': '%.2f' % (float(r['percentage']) * 100),
            'numberOfCrashes': r['report_count']})
    for r in result['processTypes']:
        signature_summary['processTypes'].append({
            'processType': r['category'],
            'percentage': '%.2f' % (float(r['percentage']) * 100),
            'numberOfCrashes': r['report_count']})
    for r in result['flashVersions']:
        signature_summary['flashVersions'].append({
            'flashVersion': r['category'],
            'percentage': '%.2f' % (float(r['percentage']) * 100),
            'numberOfCrashes': r['report_count']})

    return signature_summary


@set_base_data
def crash_trends(request, product, versions=None):
    data = {}

    data['product'] = product

    for release in request.currentversions:
        if release['product'] == product:
            # For crash trends we only want the latest, featured Nightly
            if release['release'] == 'Nightly' and release['featured']:
                version = release['version']

    data['end_date'] = datetime.datetime.utcnow()
    data['start_date'] = data['end_date'] - datetime.timedelta(days=7)

    api = models.CurrentProducts()
    current_products = api.get()

    products = []
    for prod in current_products['hits']:
        products.append(prod['product_name'])

    data['products'] = current_products

    url = '/crash_trends/json_data?'
    params = {
        'product': product,
        'version': version,
        'start_date': data['start_date'].strftime('%Y-%m-%d'),
        'end_date': data['end_date'].strftime('%Y-%m-%d')
    }
    url += urllib.urlencode(params)
    data['data_url'] = url

    return render(request, 'crashstats/crash_trends.html', data)


@utils.json_view
@set_base_data
def crashtrends_versions_json(request):
    product = request.GET.get('product')

    versions = []
    sorted(request.currentversions, reverse=True)
    for release in request.currentversions:
        rel_product = release['product']
        rel_release = release['release']
        if rel_product == product:
            if rel_release == 'Nightly' or rel_release == 'Aurora':
                versions.append(release['version'])

    return versions


@utils.json_view
def crashtrends_json(request):
    product = request.GET.get('product')
    version = request.GET.get('version')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    api = models.CrashTrends()
    response = api.get(
        product=product,
        version=version,
        start_date=start_date,
        end_date=end_date
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


class BuildsRss(Feed):
    def link(self, data):
        return data['request'].path

    def get_object(self, request, product, versions=None):
        return {'product': product, 'versions': versions, 'request': request}

    def title(self, data):
        return "Crash Stats for Mozilla Nightly Builds for " + data['product']

    def items(self, data):
        api = models.DailyBuilds()
        all_builds = api.get(data['product'], version=data['versions'])
        nightly_builds = []
        for build in all_builds:
            if build['build_type'] == 'Nightly':
                nightly_builds.append(build)
        return nightly_builds

    def item_title(self, item):
        return (
            '%s  %s - %s - Build ID# %s' %
            (item['product'],
             item['version'],
             item['platform'],
             item['buildid'])
        )

    def item_link(self, item):
        return ('%s?build_id=%s&do_query=1' %
                (reverse('crashstats.query'), item['buildid']))

    def item_description(self, item):
        return self.item_title(item)

    def item_pubdate(self, item):
        return datetime.datetime.strptime(item['date'], '%Y-%m-%d')


def raw_data(request, crash_id, extension):
    if not request.user.is_active:
        return http.HttpResponseForbidden("Must be logged in")

    api = models.RawCrash()
    if extension == 'json':
        format = 'meta'
        content_type = 'application/json'
    elif extension == 'dump':
        format = 'raw_crash'
        content_type = 'application/octet-stream'
    else:
        raise NotImplementedError(extension)

    data = api.get(crash_id, format)
    response = http.HttpResponse(content_type=content_type)

    if extension == 'json':
        response.write(json.dumps(data))
    else:
        response.write(data)
    return response

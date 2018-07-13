import gzip
import json
import datetime
import os
import urllib
from collections import defaultdict
from io import BytesIO

from django import http
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import urlquote
from django.utils import timezone

from csp.decorators import csp_update

from socorro.external.crashstorage_base import CrashIDNotFound
from . import forms, models, utils
from .decorators import pass_default_context

from crashstats.supersearch.models import (
    SuperSearchFields,
    SuperSearchUnredacted,
    SuperSearch,
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
    else:
        context['raw_stackwalker_output'] = 'No dump available'
        parsed_dump = {}

    context['crashing_thread'] = parsed_dump.get('crash_info', {}).get('crashing_thread')
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


def dockerflow_version(requst):
    path = os.path.join(settings.SOCORRO_ROOT, 'version.json')
    if os.path.exists(path):
        with open(path, 'r') as fp:
            data = fp.read()
    else:
        data = '{}'
    return http.HttpResponse(data, content_type='application/json')


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

    batch_size = 1000
    product = form.cleaned_data['product'] or settings.DEFAULT_PRODUCT
    date = form.cleaned_data['date']
    params = {
        'product': product,
        'date': [
            '>={}'.format(date.strftime('%Y-%m-%d')),
            '<{}'.format(
                (date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            )
        ],
        '_columns': (
            'signature',
            'uuid',
            'date',
            'product',
            'version',
            'build_id',
            'platform',
            'platform_version',
            'cpu_name',
            'cpu_info',
            'address',
            'uptime',
            'topmost_filenames',
            'reason',
            'app_notes',
            'release_channel',
        ),
        '_results_number': batch_size,
        '_results_offset': 0,
    }
    api = SuperSearch()
    # Do the first query. That'll give us the total and the first page's
    # worth of crashes.
    data = api.get(**params)
    assert 'hits' in data

    accept_gzip = 'gzip' in request.META.get('HTTP_ACCEPT_ENCODING', '')
    response = http.HttpResponse(content_type='text/csv')
    out = BytesIO()
    writer = utils.UnicodeWriter(out, delimiter='\t')
    writer.writerow(GRAPHICS_REPORT_HEADER)
    pages = data['total'] // batch_size
    # if there is a remainder, add one more page
    if data['total'] % batch_size:
        pages += 1
    alias = {
        'crash_id': 'uuid',
        'os_name': 'platform',
        'os_version': 'platform_version',
        'date_processed': 'date',
        'build': 'build_id',
        'uptime_seconds': 'uptime',
    }
    # Make sure that we don't have an alias for a header we don't need
    alias_excess = set(alias.keys()) - set(GRAPHICS_REPORT_HEADER)
    if alias_excess:
        raise ValueError(
            'Not all keys in the map of aliases are in '
            'the header ({!r})'.format(alias_excess)
        )

    def get_value(row, key):
        """Return the appropriate output from the row of data, one key
        at a time. The output is what's used in writing the CSV file.

        The reason for doing these "hacks" is to match what used to be
        done with the SELECT statement in SQL in the ancient, but now
        replaced, report.
        """
        value = row.get(alias.get(key, key))
        if key == 'cpu_info':
            value = '{cpu_name} | {cpu_info}'.format(
                cpu_name=row.get('cpu_name', ''),
                cpu_info=row.get('cpu_info', ''),
            )
        if value is None:
            return ''
        if key == 'date_processed':
            value = timezone.make_aware(datetime.datetime.strptime(
                value.split('.')[0],
                '%Y-%m-%dT%H:%M:%S'
            ))
            value = value.strftime('%Y%m%d%H%M')
        if key == 'uptime_seconds' and value == 0:
            value = ''
        return value

    for page in range(pages):
        if page > 0:
            params['_results_offset'] = batch_size * page
            data = api.get(**params)

        for row in data['hits']:
            # Each row is a dict, we want to turn it into a list of
            # exact order as the `header` tuple above.
            # However, because the csv writer module doesn't "understand"
            # python's None, we'll replace those with '' to make the
            # CSV not have the word 'None' where the data is None.
            writer.writerow([
                get_value(row, x)
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


@pass_default_context
def new_report_index(request, crash_id, default_context=None):
    context = default_context or {}
    return render(request, 'crashstats/new_report_index.html', context)

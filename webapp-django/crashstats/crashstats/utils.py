import csv
import codecs
import datetime
import isodate
import functools
import json
import re
from past.builtins import basestring
from collections import OrderedDict

from six.moves import cStringIO
from six import text_type

from django import http
from django.conf import settings
from django.utils import timezone

from . import models
import crashstats.supersearch.models as supersearch_models


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)


def parse_isodate(ds):
    """
    return a datetime object from a date string
    """
    if isinstance(ds, text_type):
        # isodate struggles to convert unicode strings with
        # its parse_datetime() if the input string is unicode.
        ds = ds.encode('ascii')
    return isodate.parse_datetime(ds)


def daterange(start_date, end_date, format='%Y-%m-%d'):
    for n in range((end_date - start_date).days):
        yield (start_date + datetime.timedelta(n)).strftime(format)


def json_view(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        request._json_view = True
        response = f(request, *args, **kw)

        if isinstance(response, http.HttpResponse):
            return response
        else:

            indent = 0
            request_data = (
                request.method == 'GET' and request.GET or request.POST
            )
            if request_data.get('pretty') == 'print':
                indent = 2
            if isinstance(response, tuple) and isinstance(response[1], int):
                response, status = response
            else:
                status = 200
            if isinstance(response, tuple) and isinstance(response[1], dict):
                response, headers = response
            else:
                headers = {}
            http_response = http.HttpResponse(
                _json_clean(json.dumps(
                    response,
                    cls=DateTimeEncoder,
                    indent=indent
                )),
                status=status,
                content_type='application/json; charset=UTF-8'
            )
            for key, value in headers.items():
                http_response[key] = value
            return http_response
    return wrapper


def _json_clean(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashe\
    # s-escaped
    return value.replace("</", "<\\/")


def enhance_frame(frame, vcs_mappings):
    """
    Add some additional info to a stack frame--signature
    and source links from vcs_mappings.
    """
    if 'function' in frame:
        # Remove spaces before all stars, ampersands, and commas
        function = re.sub(' (?=[\*&,])', '', frame['function'])
        # Ensure a space after commas
        function = re.sub(',(?! )', ', ', function)
        frame['function'] = function
        signature = function
    elif 'file' in frame and 'line' in frame:
        signature = '%s#%d' % (frame['file'], frame['line'])
    elif 'module' in frame and 'module_offset' in frame:
        signature = '%s@%s' % (frame['module'], frame['module_offset'])
    else:
        signature = '@%s' % frame['offset']
    frame['signature'] = signature
    frame['short_signature'] = re.sub('\(.*\)', '', signature)

    if 'file' in frame:
        vcsinfo = frame['file'].split(':')
        if len(vcsinfo) == 4:
            vcstype, root, vcs_source_file, revision = vcsinfo
            if '/' in root:
                # The root is something like 'hg.mozilla.org/mozilla-central'
                server, repo = root.split('/', 1)
            else:
                # E.g. 'gecko-generated-sources' or something without a '/'
                repo = server = root

            if vcs_source_file.count('/') > 1 and len(vcs_source_file.split('/')[0]) == 128:
                # In this case, the 'vcs_source_file' will be something like
                # '{SHA-512 hex}/ipc/ipdl/PCompositorBridgeChild.cpp'
                # So drop the sha part for the sake of the 'file' because
                # we don't want to display a 128 character hex code in the
                # hyperlink text.
                vcs_source_file_display = '/'.join(vcs_source_file.split('/')[1:])
            else:
                # Leave it as is if it's not unweildly long.
                vcs_source_file_display = vcs_source_file

            if vcstype in vcs_mappings:
                if server in vcs_mappings[vcstype]:
                    link = vcs_mappings[vcstype][server]
                    frame['file'] = vcs_source_file_display
                    frame['source_link'] = link % {
                        'repo': repo,
                        'file': vcs_source_file,
                        'revision': revision,
                        'line': frame['line']}
            else:
                path_parts = vcs_source_file.split('/')
                frame['file'] = path_parts.pop()


def enhance_json_dump(dump, vcs_mappings):
    """
    Add some information to the stackwalker's json_dump output
    for display. Mostly applying vcs_mappings to stack frames.
    """
    for i, thread in enumerate(dump.get('threads', [])):
        if 'thread' not in thread:
            thread['thread'] = i
        for frame in thread['frames']:
            enhance_frame(frame, vcs_mappings)
    return dump


def parse_version(version):
    """Parses a version string into a comparable tuple

    >>> parse_version('59.0')
    (59, 0, 0, 'zz')
    >>> parse_version('59.0.2')
    (59, 0, 2, 'zz')
    >>> parse_version('59.0b1')
    (59, 0, 0, 'b1')
    >>> parse_version('59.0a1')
    (59, 0, 0, 'a1')

    This is a good key for sorting:

    >>> versions = ['59.0', '59.0b2', '59.0.2', '59.0a1']
    >>> sorted(versions, key=parse_version, reverse=1)
    ['59.0.2', '59.0', '59.0b2', '59.0a1']

    :arg version: version string like "59.0b1" or "59.0.2"

    :returns: tuple for comparing

    """
    try:
        if 'a' in version:
            version, ending = version.split('a')
            ending = ['a' + ending]
        elif 'b' in version:
            version, ending = version.split('b')
            ending = ['b' + ending]
        elif 'esr' in version:
            version = version.replace('esr', '')
            # Add zz, then esr so that esr is bigger than release versions.
            ending = ['zz', 'esr']
        else:
            ending = ['zz']

        version = [int(part) for part in version.split('.')]
        while len(version) < 3:
            version.append(0)
        version.extend(ending)
        return tuple(version)
    except (ValueError, IndexError):
        # If we hit an error, it's probably junk data so return an tuple with a
        # -1 in it which put it at the bottom of the pack
        return (-1)


def get_recent_versions_for_product(product):
    """Returns recent versions for specified product

    This looks at the crash reports submitted for this product in the last week
    and returns the versions of those crash reports.

    If SuperSearch returns an error, this returns an empty list.

    NOTE(willkg): This data can be noisy in cases where crash reports return
    junk versions. We might want to add a "minimum to matter" number.

    :arg product: the product to query for

    :returns: list of versions sorted in reverse order or ``[]``

    """
    api = supersearch_models.SuperSearchUnredacted()
    now = timezone.now()

    # Find versions for specified product in crash reports reported in
    # the last week
    params = {
        'product': product,
        '_results_number': 0,
        '_facets': 'version',
        '_facets_size': 100,
        'date': [
            '>=' + (now - datetime.timedelta(days=7)).isoformat(),
            '<' + now.isoformat()
        ]
    }

    ret = api.get(**params)
    if 'facets' not in ret or 'version' not in ret['facets']:
        return []

    versions = [
        item['term'] for item in ret['facets']['version']
    ]
    versions.sort(
        key=lambda version: parse_version(version),
        reverse=1
    )

    # Map of major version (int) -> list of versions (str)
    major_to_versions = {}
    for version in versions:
        try:
            major = int(version.split('.', 1)[0])
            major_to_versions.setdefault(major, []).append(version)
        except ValueError:
            # If the first thing in the major version isn't an int, then skip
            # it
            continue

    return [
        {
            'product': product,
            'version': major_to_versions[major_key][0],
            'is_featured': True,
            'has_builds': False
        }
        for major_key in sorted(major_to_versions.keys(), reverse=True)
    ]


def build_default_context(product=None, versions=None):
    """
    from ``product`` and ``versions`` transfer to
    a dict. If there's any left-over, raise a 404 error
    """
    context = {}

    # Build product information
    api = models.Products()
    # NOTE(willkg): using an OrderedDict here since Products returns products
    # sorted by sort order and we don't want to lose that ordering
    all_products = OrderedDict()
    for item in api.get()['hits']:
        if item['sort'] == -1:
            # A sort of -1 means this item is inactive and we shouldn't show it
            # in product lists
            continue
        all_products[item['product_name']] = item
    context['products'] = all_products

    # Build product version information
    api = models.ProductVersions()
    active_versions = OrderedDict()

    # Turn the list of all product versions into a dict, one per product.
    for pv in api.get(active=True)['hits']:
        if pv['product'] not in active_versions:
            active_versions[pv['product']] = []
        active_versions[pv['product']].append(pv)
    context['active_versions'] = active_versions

    if product:
        if product not in context['products']:
            raise http.Http404('Not a recognized product')

        if product not in active_versions:
            # This is a product that doesn't have version information in
            # product_versions, so we pull it from supersearch
            active_versions[product] = get_recent_versions_for_product(product)

        context['product'] = product
    else:
        context['product'] = settings.DEFAULT_PRODUCT

    if versions is None:
        versions = []
    elif isinstance(versions, basestring):
        versions = versions.split(';')

    if versions:
        assert isinstance(versions, list)
        context['version'] = versions[0]

        # Also, check that that's a valid version for this product
        pv_versions = [
            x['version'] for x in active_versions[context['product']]
        ]
        for version in versions:
            if version not in pv_versions:
                raise http.Http404("Not a recognized version for that product")

    return context


_crash_id_regex = re.compile(
    r'^(%s)?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
    r'[0-9a-f]{4}-[0-9a-f]{6}[0-9]{6})$' % (settings.CRASH_ID_PREFIX,)
)


def find_crash_id(input_str):
    """Return the valid Crash ID part of a string"""
    for match in _crash_id_regex.findall(input_str):
        try:
            datetime.datetime.strptime(match[1][-6:], '%y%m%d')
            return match[1]
        except ValueError:
            pass  # will return None


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([text_type(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def add_CORS_header(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        response = f(request, *args, **kw)
        response['Access-Control-Allow-Origin'] = '*'
        return response
    return wrapper


def ratelimit_rate(group, request):
    """return None if we don't want to set any rate limit.
    Otherwise return a number according to
    https://django-ratelimit.readthedocs.org/en/latest/rates.html#rates-chapter
    """
    if group in ('crashstats.api.views.model_wrapper', 'crashstats.api.views.crash_verify'):
        if request.user.is_active:
            return settings.API_RATE_LIMIT_AUTHENTICATED
        else:
            return settings.API_RATE_LIMIT
    elif group.startswith('crashstats.supersearch.views.search'):
        # this applies to both the web view and ajax views
        if request.user.is_active:
            return settings.RATELIMIT_SUPERSEARCH_AUTHENTICATED
        else:
            return settings.RATELIMIT_SUPERSEARCH
    raise NotImplementedError(group)

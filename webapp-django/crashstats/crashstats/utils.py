import csv
import codecs
import cStringIO
import datetime
import isodate
import functools
import json
import time
import re
from collections import OrderedDict

from django import http
from django.conf import settings

from . import models


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)


def unixtime(value, millis=False, format='%Y-%m-%d'):
    d = datetime.datetime.strptime(value, format)
    epoch_seconds = time.mktime(d.timetuple())
    if millis:
        return epoch_seconds * 1000 + d.microsecond / 1000
    else:
        return epoch_seconds


def parse_isodate(ds):
    """
    return a datetime object from a date string
    """
    if isinstance(ds, unicode):
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
            server, repo = root.split('/', 1)

            if vcstype in vcs_mappings:
                if server in vcs_mappings[vcstype]:
                    link = vcs_mappings[vcstype][server]
                    frame['file'] = vcs_source_file
                    frame['source_link'] = link % {
                        'repo': repo,
                        'file': vcs_source_file,
                        'revision': revision,
                        'line': frame['line']}
            else:
                path_parts = vcs_source_file.split('/')
                frame['file'] = path_parts.pop()


def parse_dump(dump, vcs_mappings):

    parsed_dump = {
        'status': 'OK',
        'modules': [],
        'threads': [],
        'crash_info': {
            'crashing_thread': None,
        },
        'system_info': {}
    }

    for line in dump.split('\n'):
        entry = line.split('|')
        if entry[0] == 'OS':
            parsed_dump['system_info']['os'] = entry[1]
            parsed_dump['system_info']['os_ver'] = entry[2]
        elif entry[0] == 'CPU':
            parsed_dump['system_info']['cpu_arch'] = entry[1]
            parsed_dump['system_info']['cpu_info'] = entry[2]
            parsed_dump['system_info']['cpu_count'] = int(entry[3])
        elif entry[0] == 'Crash':
            parsed_dump['crash_info']['type'] = entry[1]
            parsed_dump['crash_info']['crash_address'] = entry[2]
            parsed_dump['crash_info']['crashing_thread'] = int(entry[3])
        elif entry[0] == 'Module':
            if entry[7] == '1':
                parsed_dump['main_module'] = len(parsed_dump['modules'])
            parsed_dump['modules'].append({
                'filename': entry[1],
                'version': entry[2],
                'debug_file': entry[3],
                'debug_id': entry[4],
                'base_addr': entry[5],
                'end_addr': entry[6]
            })
        elif entry[0].isdigit():
            thread_num, frame_num, module_name, function, \
                source_file, source_line, instruction = entry

            thread_num = int(thread_num)
            frame_num = int(frame_num)

            frame = {
                'frame': frame_num,
            }
            if module_name:
                frame['module'] = module_name
                if not function:
                    frame['module_offset'] = instruction
            else:
                frame['offset'] = instruction
            if function:
                frame['function'] = function
                if not source_line:
                    frame['function_offset'] = instruction
            if source_file:
                frame['file'] = source_file
            if source_line:
                frame['line'] = int(source_line)

            enhance_frame(frame, vcs_mappings)

            if parsed_dump['crash_info']['crashing_thread'] is None:
                parsed_dump['crash_info']['crashing_thread'] = thread_num

            if thread_num >= len(parsed_dump['threads']):
                # `parsed_dump['threads']` is a list and we haven't stuff
                # this many items in it yet so, up til and including
                # `thread_num` we stuff in an initial empty one
                for x in range(len(parsed_dump['threads']), thread_num + 1):
                    # This puts in the possible padding too if thread_num
                    # is higher than the next index
                    if x >= len(parsed_dump['threads']):
                        parsed_dump['threads'].append({
                            'thread': x,
                            'frames': []
                        })
            parsed_dump['threads'][thread_num]['frames'].append(frame)

    parsed_dump['thread_count'] = len(parsed_dump['threads'])
    for thread in parsed_dump['threads']:
        thread['frame_count'] = len(thread['frames'])
    return parsed_dump


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


def build_default_context(product=None, versions=None):
    """
    from ``product`` and ``versions`` transfer to
    a dict. If there's any left-over, raise a 404 error
    """
    context = {}
    api = models.ProductVersions()
    active_versions = OrderedDict()  # so that products are in order
    # Turn the list of all product versions into a dict, one per product.
    for pv in api.get(active=True)['hits']:
        if pv['product'] not in active_versions:
            active_versions[pv['product']] = []
        active_versions[pv['product']].append(pv)
    context['active_versions'] = active_versions

    if versions is None:
        versions = []
    elif isinstance(versions, basestring):
        versions = versions.split(';')

    if product:
        if product not in context['active_versions']:
            raise http.Http404('Not a recognized product')
        context['product'] = product
    else:
        context['product'] = settings.DEFAULT_PRODUCT

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


def sanitize_dict(dict_):
    """Return a copy of the passed dict, without null or empty values."""
    return dict((k, v) for (k, v) in dict_.items() if v not in (None, '', []))


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([unicode(s).encode("utf-8") for s in row])
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
    if group == 'crashstats.api.views.model_wrapper':
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

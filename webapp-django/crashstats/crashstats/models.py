"""
Remember! Every new model you introduce here automatically gets exposed
in the public API in the `api` app.
"""
import datetime
import hashlib
import os
import urlparse
import json
import logging
import requests
import stat
import time
import urllib
import re

from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import iri_to_uri
from django.utils.hashcompat import md5_constructor
from django.template.defaultfilters import slugify
from django_statsd.clients import statsd

from crashstats import scrubber
from crashstats.api.cleaner import Cleaner


class BadStatusCodeError(Exception):  # XXX poor name
    pass


class RequiredParameterError(Exception):
    pass


def _clean_path(path):
    """return a cleaned up version of the path appropriate for saving
    as a file directory.
    """
    path = iri_to_uri(path)
    path = path.replace(' ', '_')
    path = '/'.join(slugify(x) for x in path.split('/'))
    if path.startswith('/'):
        path = path[1:]
    return path


def _clean_query(query, max_length=30):
    cleaned = _clean_path(query.replace('&', '/'))
    # if we allow the query part become too long,
    # we might run the rist of getting a OSError number 63
    # which is "File name too long"
    if len(cleaned) > max_length:
        # it's huge! hash it
        cleaned = hashlib.md5(cleaned).hexdigest()
    return cleaned


class SocorroCommon(object):

    # by default, we don't need username and password
    username = password = None
    # http_host
    http_host = None

    # default cache expiration time if applicable
    cache_seconds = 60 * 60

    # how many seconds to sleep when getting a ConnectionError
    retry_sleeptime = 3

    # how many times to re-attempt on ConnectionError after some sleep
    retries = 10

    def fetch(self, url, headers=None, method='get', data=None,
              expect_json=True, dont_cache=False,
              retries=None,
              retry_sleeptime=None):

        if retries is None:
            retries = self.retries
        if retry_sleeptime is None:
            retry_sleeptime = self.retry_sleeptime

        if url.startswith('/'):
            url = self._complete_url(url)

        if not headers:
            if self.http_host:
                headers = {'Host': self.http_host}
            else:
                headers = {}

        if self.username and self.password:
            auth = self.username, self.password
        else:
            auth = ()

        cache_key = None
        cache_file = None

        if settings.CACHE_MIDDLEWARE and not dont_cache and self.cache_seconds:
            cache_key = md5_constructor(iri_to_uri(url)).hexdigest()
            result = cache.get(cache_key)
            if result is not None:
                logging.debug("CACHE HIT %s" % url)
                return result

            # not in the memcache/locmem but is it in cache files?

            if settings.CACHE_MIDDLEWARE_FILES:
                root = settings.CACHE_MIDDLEWARE_FILES
                if isinstance(root, bool):
                    cache_file = os.path.join(settings.ROOT, 'models-cache')
                else:
                    cache_file = root
                split = urlparse.urlparse(url)
                cache_file = os.path.join(cache_file,
                                          split.netloc,
                                          _clean_path(split.path))
                if split.query:
                    cache_file = os.path.join(cache_file,
                                              _clean_query(split.query))
                if expect_json:
                    cache_file = os.path.join(cache_file,
                                              '%s.json' % cache_key)
                else:
                    cache_file = os.path.join(cache_file,
                                              '%s.dump' % cache_key)

                if os.path.isfile(cache_file):
                    # but is it fresh enough?
                    age = time.time() - os.stat(cache_file)[stat.ST_MTIME]
                    if age > self.cache_seconds:
                        logging.debug("CACHE FILE TOO OLD")
                        os.remove(cache_file)
                    else:
                        logging.debug("CACHE FILE HIT %s" % url)
                        if expect_json:
                            return json.load(open(cache_file))
                        else:
                            return open(cache_file).read()

        if method == 'post':
            request_method = requests.post
            logging.info("POSTING TO %s" % url)
        elif method == 'get':
            request_method = requests.get
            logging.info("FETCHING %s" % url)
        elif method == 'put':
            request_method = requests.put
            logging.info("PUTTING TO %s" % url)
        elif method == 'delete':
            request_method = requests.delete
            logging.info("DELETING ON %s" % url)
        else:
            raise ValueError(method)

        try:
            resp = request_method(
                url=url,
                auth=auth,
                headers=headers,
                data=data
            )
        except requests.ConnectionError:
            if not retries:
                raise
            # https://bugzilla.mozilla.org/show_bug.cgi?id=916886
            time.sleep(retry_sleeptime)
            return self.fetch(
                url,
                headers=headers,
                method=method,
                data=data,
                expect_json=expect_json,
                dont_cache=dont_cache,
                retry_sleeptime=retry_sleeptime,
                retries=retries - 1
            )

        self._process_response(method, url, resp.status_code)

        if not resp.status_code == 200:
            raise BadStatusCodeError('%s: on: %s' % (resp.status_code, url))

        result = resp.content
        if expect_json:
            result = json.loads(result)

        if cache_key:
            cache.set(cache_key, result, self.cache_seconds)
            if cache_file:
                if not os.path.isdir(os.path.dirname(cache_file)):
                    os.makedirs(os.path.dirname(cache_file))
                if expect_json:
                    json.dump(result, open(cache_file, 'w'), indent=2)
                else:
                    open(cache_file, 'w').write(result)

        return result

    def _complete_url(self, url):
        if url.startswith('/'):
            if not getattr(self, 'base_url', None):
                raise NotImplementedError("No base_url defined in context")
            url = '%s%s' % (self.base_url, url)
        return url

    def _process_response(self, method, url, status_code):
        path = urlparse.urlparse(url).path
        path_info = urllib.quote(path.encode('utf-8'))

        # Removes uuids from path_info
        if "uuid/" in url:
            uuid = path_info.rsplit("/uuid/")
            if len(uuid) == 2:
                path_info = uuid[0] + '/uuid' + uuid[1][uuid[1].find('/'):]

        # Replaces dates for XXXX-XX-XX
        replaces = re.findall(r'(\d{4}-\d{2}-\d{2})', path_info)
        for date in replaces:
            date = path_info[path_info.find(date):].rsplit("/")[0]
            path_info = path_info.replace(date, "XXXX-XX-XX")

        metric = u"middleware.{0}.{1}.{2}".format(
            method.upper(),
            path_info.lstrip('/').replace('.', '-'),
            status_code
        )
        metric = metric.encode('utf-8')
        statsd.incr(metric)


class SocorroMiddleware(SocorroCommon):

    base_url = settings.MWARE_BASE_URL
    http_host = settings.MWARE_HTTP_HOST
    username = settings.MWARE_USERNAME
    password = settings.MWARE_PASSWORD

    default_date_format = '%Y-%m-%d'
    default_datetime_format = '%Y-%m-%dT%H:%M:%S'

#    def fetch(self, url, *args, **kwargs):
#        url = self._complete_url(url)
#        return super(SocorroMiddleware, self).fetch(url, *args, **kwargs)

    def post(self, url, payload):
        return self._post(url, payload)

    def put(self, url, payload):
        return self._post(url, payload, method='put')

    def delete(self, url, payload):
        return self._post(url, payload, method='delete')

    def _post(self, url, payload, method='post'):
        url = self._complete_url(url)
        headers = {'Host': self.http_host}
        # set dont_cache=True here because the request depends on the payload
        return self.fetch(url, headers=headers, method=method, data=payload,
                          dont_cache=True)

    def get(self, expect_json=True, **kwargs):
        """
        This is the generic `get` method that will take
        `self.required_params` and `self.possible_params` and construct
        a URL using only a known prefix.
        ALl classes that don't need to do any particular hacks, just need
        to define a `URL_PREFIX` and (`required_params` and/or
        `possible_params`)
        """
        url = self.URL_PREFIX
        assert url.startswith('/'), 'URL_PREFIX must start with a /'
        assert url.endswith('/'), 'URL_PREFIX must end with a /'
        params = {}

        required_params = self.flatten_params(
            getattr(self, 'required_params', [])
        )
        possible_params = self.flatten_params(
            getattr(self, 'possible_params', [])
        )

        defaults = getattr(self, 'defaults', {})
        aliases = getattr(self, 'aliases', {})

        for key, value in defaults.items():
            kwargs[key] = kwargs.get(key) or value

        for param in required_params + possible_params:
            if param in required_params and not kwargs.get(param):
                raise RequiredParameterError(param)
            value = kwargs.get(param)
            if not value:
                continue
            if param in ('signature', 'reasons', 'terms'):  # XXX factor out
                value = self.encode_special_chars(value)
            if isinstance(value, (list, tuple)):
                value = '+'.join(unicode(x) for x in value)

            params[param] = value
            url += aliases.get(param, param) + '/%(' + param + ')s/'

        self.urlencode_params(params)
        return self.fetch(url % params,
                          expect_json=expect_json)

    def urlencode_params(self, params):
        """in-place replacement URL encoding parameter values.
        For example, if params == {'foo': 'bar1 bar2'}
        it changes it to == {'foo': 'bar1%20bar2'}
        """
        def quote(value):
            # the special chars %0A (newline char) and %00 (null byte)
            # break the middleware
            # we want to simply remove them from all URLs
            return (
                urllib.quote(value, '')  # Slashes are not safe in our URLs
                      .replace('%0A', '')
                      .replace('%00', '')
            )

        for key, value in params.iteritems():
            if isinstance(value, datetime.datetime):
                value = value.strftime(self.default_datetime_format)
            if isinstance(value, datetime.date):
                value = value.strftime(self.default_date_format)
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if isinstance(value, basestring):
                params[key] = quote(value)
            if isinstance(value, (list, tuple)):
                params[key] = [
                    quote(v)
                    for v in value
                    if isinstance(v, basestring)
                ]

    def build_middleware_url(
        self,
        url_base,
        parameters=None,
        params_aliases=None,
        params_separator='/',
        key_value_separator='/',
        values_separator='+',
        url_params_separator='/'
    ):
        """Return a complete URL to call a middleware service.

        Keyword args:
        url_base - base of the URL to call, before parameters
        parameters - dict of the parameters to add to the URL
        params_aliases - dict to alias some keys before building the URL
        params_separator - separator used between each key/value pair
        key_value_separator - separator used between a key and its value
        values_separator - separator used to join lists in parameters
        url_params_separator - separator used between url_base and parameters

        """
        if not parameters:
            return url_base

        self.urlencode_params(parameters)

        url_params = []
        for param, value in parameters.iteritems():
            try:
                # For empty strings and lists
                valid = len(value) > 0
            except TypeError:
                # value was neither a string nor a list, it's valid by default
                valid = True

            if value is not None and valid:
                if params_aliases:
                    param = params_aliases.get(param, param)
                if isinstance(value, (list, tuple)):
                    value = values_separator.join(value)
                else:
                    value = str(value)
                url_params.append(key_value_separator.join((param, value)))

        url_params = params_separator.join(url_params)
        return url_params_separator.join((url_base, url_params))

    def encode_special_chars(self, input_):
        """Return the passed string with url-encoded slashes and pluses.

        We do that for two reasons: first, Apache won't by default accept
        encoded slashes in URLs. Second, '+' is a special character in the
        middleware, used as a list separator.

        This function should be called only on parameters that are allowed to
        contain slashes or pluses, which means basically only signature fields.
        """
        def clean(string):
            return string.replace('/', '%2F').replace('+', '%2B')
        if isinstance(input_, (tuple, list)):
            return [clean(x) for x in input_]
        else:
            return clean(input_)

    @staticmethod
    def flatten_params(params):
        names = []
        for param in params:
            if isinstance(param, basestring):
                names.append(param)
            elif isinstance(param, dict):
                names.append(param['name'])
            else:
                assert isinstance(param, (list, tuple))
                names.append(param[0])
        return names

    @classmethod
    def get_annotated_params(cls):
        """return an iterator. One dict for each parameter that the
        class takes.
        Each dict must have the following keys:
            * name
            * type
            * required
        """
        for required, items in ((True, getattr(cls, 'required_params', [])),
                                (False, getattr(cls, 'possible_params', []))):
            for item in items:
                if isinstance(item, basestring):
                    type_ = basestring
                    name = item
                elif isinstance(item, dict):
                    type_ = item['type']
                    name = item['name']
                else:
                    assert isinstance(item, tuple)
                    name = item[0]
                    type_ = item[1]

                yield {
                    'name': name,
                    'required': required,
                    'type': type_,
                }


class CurrentVersions(SocorroMiddleware):

    API_WHITELIST = (
        'end_date',
        'featured',
        'id',
        'product',
        'release',
        'start_date',
        'throttle',
        'version',
    )

    def get(self):
        products = CurrentProducts().get()['products']
        releases = CurrentProducts().get()['hits']
        currentversions = []

        for product_name in products:
            for release in releases[product_name]:
                currentversions.append(release)

        return currentversions


class CurrentProducts(SocorroMiddleware):

    URL_PREFIX = '/products/'

    possible_params = (
        'versions',
    )

    API_WHITELIST = {
        'hits': {
            Cleaner.ANY: (
                'end_date',
                'featured',
                'id',
                'product',
                'release',
                'start_date',
                'throttle',
                'version',
            )
        }
    }


class ReleasesFeatured(SocorroMiddleware):

    URL_PREFIX = '/releases/featured/'

    possible_params = (
        'products',
    )

    def put(self, **data):
        """@data here is expected to be something like
        {'Firefox': ['19.0', '20.0', '21.0'],
         ...
        """
        payload = {}
        for key, value in data.items():
            if isinstance(value, list):
                value = ','.join(value)
            payload[key] = value
        return super(ReleasesFeatured, self).put(self.URL_PREFIX, payload)


class ProductsVersions(CurrentVersions):

    API_WHITELIST = {
        Cleaner.ANY: (
            'product',
            'throttle',
            'version',
            'start_date',
            'end_date',
            'featured',
            'release',
        )
    }

    def get(self):
        versions = super(ProductsVersions, self).get()
        products = {}
        for version in versions:
            product = version['product']
            if product not in products:
                products[product] = []
            products[product].append(version)
        return products


class Platforms(SocorroMiddleware):

    API_WHITELIST = (
        'code',
        'name',
    )

    def get(self):
        # For dev only, this should be moved to a middleware service
        # using the database as soon as possible.
        platforms = [
            {
                'code': 'win',
                'name': 'Windows',
                'display': True,
            },
            {
                'code': 'win32',
                'name': 'Windows',
            },
            {
                'code': 'win',
                'name': 'Windows NT',
            },
            {
                'code': 'mac',
                'name': 'Mac OS X',
                'display': True,
            },
            {
                'code': 'lin',
                'name': 'Linux',
                'display': True,
            },
            {
                'code': 'linux-i686',
                'name': 'Linux'
            }
        ]
        return platforms


class CrashesPerAdu(SocorroMiddleware):
    # Fetch records for active daily users.

    URL_PREFIX = '/crashes/daily/'

    required_params = (
        'product',
        ('versions', list),
    )

    possible_params = (
        ('from_date', datetime.date),
        ('to_date', datetime.date),
        'date_range_type',
        'os',
        'report_type',
        'separated_by',  # used for a hack in get()
    )

    API_WHITELIST = {
        'hits': {
            Cleaner.ANY: {
                Cleaner.ANY: (
                    'adu',
                    'date',
                    'crash_hadu',
                    'product',
                    'report_count',
                    'version',
                )
            }
        }
    }

    def get(self, **kwargs):
        # hack a bit before moving on to the sensible stuff
        if 'os' in kwargs:
            # Operating systems can be specified for by version as
            # well but, we only want to separate the results by OS
            # if the selected, report type was by_os.
            if ('form_selection' in kwargs and
                    kwargs.get('form_selection') == 'by_os'):
                kwargs['separated_by'] = 'os'

        return super(CrashesPerAdu, self).get(**kwargs)


class TCBS(SocorroMiddleware):

    URL_PREFIX = '/crashes/signatures/'

    required_params = (
        'product',
        'version',
    )
    possible_params = (
        'crash_type',
        ('end_date', datetime.date),
        'date_range_type',
        ('duration', int),
        ('limit', int),
        'os',
    )
    defaults = {
        'limit': 300,
    }

    API_WHITELIST = {
        'crashes': (
            'changeInPercentOfTotal',
            'changeInRank',
            'content_count',
            'count',
            'currentRank',
            'first_report',
            'first_report_exact',
            'hang_count',
            'linux_count',
            'mac_count',
            'percentOfTotal',
            'plugin_count',
            'previousPercentOfTotal',
            'previousRank',
            'signature',
            'startup_percent',
            'versions',
            'versions_count',
            'win_count',
        )
    }


class ReportList(SocorroMiddleware):

    URL_PREFIX = '/report/list/'

    required_params = (
        'signature',
    )

    possible_params = (
        ('products', list),
        ('versions', list),
        ('os', list),
        ('start_date', datetime.datetime),
        ('end_date', datetime.datetime),
        'build_ids',
        'reasons',
        'release_channels',
        'report_process',
        'report_type',
        'plugin_in',
        'plugin_search_mode',
        'plugin_terms',
        'result_number',
        'result_offset'
    )

    aliases = {
        'start_date': 'from',
        'end_date': 'to',
    }

    API_WHITELIST = {
        'hits': (
            'product',
            'os_name',
            'uuid',
            'hangid',
            'last_crash',
            'date_processed',
            'cpu_name',
            'uptime',
            'process_type',
            'cpu_info',
            'reason',
            'version',
            'os_version',
            'build',
            'install_age',
            'signature',
            'install_time',
            'duplicate_of',
            'address',
            'user_comments',
        )
    }

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL),
        ('user_comments', scrubber.URL),
    )


class ProcessedCrash(SocorroMiddleware):
    URL_PREFIX = '/crash_data/datatype/processed/'

    required_params = (
        'crash_id',
    )
    aliases = {
        'crash_id': 'uuid',
    }

    API_WHITELIST = (
        'ReleaseChannel',
        'addons_checked',
        'address',
        'build',
        'client_crash_date',
        'completeddatetime',
        'cpu_name',
        'date_processed',
        'distributor_version',
        'dump',
        'flash_version',
        'hangid',
        'id',
        'last_crash',
        'os_name',
        'os_version',
        'process_type',
        'product',
        'reason',
        'release_channel',
        'signature',
        'success',
        'truncated',
        'uptime',
        'user_comments',
        'uuid',
        'version',
        'install_age',
        'startedDateTime',
        'java_stack_trace',
        'crashedThread',
        'cpu_info',
        'pluginVersion',
        'hang_type',
        'distributor',
        'topmost_filenames',
        'additional_minidumps',
        'processor_notes',
        'app_notes',
        'crash_time',
        'Winsock_LSP',
        'productid',
        'pluginFilename',
        'pluginName',
        'addons',
    )

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL),
        ('user_comments', scrubber.URL),
    )


class RawCrash(SocorroMiddleware):

    URL_PREFIX = '/crash_data/'

    required_params = (
        'crash_id',
    )
    possible_params = (
        'format',
    )

    defaults = {
        'format': 'meta',
    }

    aliases = {
        'crash_id': 'uuid',
        'format': 'datatype',
    }

    API_WHITELIST = (
        'InstallTime',
        'AdapterVendorID',
        'Theme',
        'Version',
        'id',
        'Vendor',
        'EMCheckCompatibility',
        'Throttleable',
        #'URL',
        'version',
        'AdapterDeviceID',
        'ReleaseChannel',
        'submitted_timestamp',
        'buildid',
        'timestamp',
        'Notes',
        'CrashTime',
        'FramePoisonBase',
        'FramePoisonSize',
        'StartupTime',
        'Add-ons',
        'BuildID',
        'SecondsSinceLastCrash',
        'ProductName',
        'legacy_processing',
        'ProductID',
        'Winsock_LSP',
        'TotalVirtualMemory',
        'SystemMemoryUsePercentage',
        'AvailableVirtualMemory',
        'AvailablePageFile',
        'AvailablePhysicalMemory',
        'PluginFilename',
        'ProcessType',
        'PluginCpuUsage',
        'NumberOfProcessors',
        'PluginHang',
        'additional_minidumps',
        'CpuUsageFlashProcess1',
        'CpuUsageFlashProcess2',
        'PluginName',
        'PluginVersion',
        'IsGarbageCollecting',
        'Accessibility',
        'OOMAllocationSize',
        'PluginHangUIDuration',
        'Comments',
        'bug836263-size',
        'PluginUserComment',
        'AdapterRendererIDs',
        'Min_ARM_Version',
        'FlashVersion',
        'Android_Version',
        'Android_Hardware',
        'Android_Brand',
        'Android_Device',
        'Android_Board',
        'Android_Model',
        'Android_Manufacturer',
        'Android_CPU_ABI',
        'Android_CPU_ABI2',
        'throttle_rate',
    )

    def get(self, **kwargs):
        format = kwargs.get('format', 'meta')
        if format == 'raw_crash':
            format = kwargs['format'] = 'raw'
        kwargs['expect_json'] = format != 'raw'
        return super(RawCrash, self).get(**kwargs)


class CommentsBySignature(SocorroMiddleware):

    URL_PREFIX = '/crashes/comments/'

    required_params = (
        'signature',
    )

    possible_params = (
        'products',
        'versions',
        'os',
        'start_date',
        'end_date',
        'build_ids',
        'reasons',
        'report_process',
        'report_type',
        'plugin_in',
        'plugin_search_mode',
        'plugin_terms',
        'result_number',
        'result_offset'
    )

    aliases = {
        'start_date': 'from',
        'end_date': 'to'
    }

    API_WHITELIST = {
        'hits': (
            'user_comments',
            'date_processed',
            'uuid',
        ),
        # deliberately not including:
        #    email
    }

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL, 'EMAILREMOVED'),
        ('user_comments', scrubber.URL, 'URLREMOVED'),
    )


class CrashPairsByCrashId(SocorroMiddleware):

    URL_PREFIX = '/crashes/paireduuid/'

    required_params = (
        'uuid',
        'hang_id',
    )

    # because it just returns something like
    #  {"hits": ["uuid1", "uuid2", ...]}
    API_WHITELIST = None


class ExplosiveCrashes(SocorroMiddleware):
    """Queries explosive crash signatures.

    If not arguments are given, the signatures for that day only will be
    given. If a start date is specified, it will be from that day till
    today. If an end date is specified, it will be between the start
    date and the end date but does not include the end date.
    """

    URL_PREFIX = '/suspicious/'

    possible_params = (
        ('start_date', datetime.date),
        ('end_date', datetime.date)
    )

    # output should be {signature: date}
    # will never contain PII
    API_WHITELIST = None


class CrashesByExploitability(SocorroMiddleware):

    URL_PREFIX = '/crashes/exploitability/'

    required_params = (
        ('batch', int),
    )

    possible_params = (
        'start_date',
        'end_date',
        ('page', int),
    )


class Search(SocorroMiddleware):

    URL_PREFIX = '/search/signatures/'

    possible_params = (
        'terms',
        ('products', list),
        ('versions', list),
        ('os', list),
        ('start_date', datetime.datetime),
        ('end_date', datetime.datetime),
        'search_mode',
        'build_ids',
        'reasons',
        'release_channels',
        'report_process',
        'report_type',
        'plugin_in',
        'plugin_search_mode',
        'plugin_terms',
        'result_number',
        'result_offset',
        '_force_api_impl'
    )

    aliases = {
        'terms': 'for',
        'start_date': 'from',
        'end_date': 'to'
    }

    API_WHITELIST = {
        'hits': (
            'count',
            'is_linux',
            'is_mac',
            'is_windows',
            'numcontent',
            'numhang',
            'numplugin',
            'signature',
        )
    }


class Bugs(SocorroMiddleware):

    required_params = (
        'signatures',
    )

    API_WHITELIST = {
        'hits': (
            'id',
            'signature',
        )
    }

    def get(self, **kwargs):
        url = '/bugs/'
        if not kwargs.get('signatures'):
            raise ValueError("'signatures' can not be empty")
        payload = {'signatures': kwargs['signatures']}
        return self.post(url, payload)


class SignatureTrend(SocorroMiddleware):

    URL_PREFIX = '/crashes/signature_history/'

    required_params = (
        'product',
        'version',
        'signature',
        ('end_date', datetime.date),
        ('start_date', datetime.date),
    )

    API_WHITELIST = {
        'hits': (
            'date',
            'count',
            'percent_of_total',
        )
    }


class SignatureSummary(SocorroMiddleware):

    URL_PREFIX = '/signaturesummary/'

    required_params = (
        'report_type',
        'signature',
        ('start_date', datetime.date),
        ('end_date', datetime.date),
    )

    possible_params = (
        ('versions', list),
    )

    API_WHITELIST = (
        'category',
        'percentage',
        'product_name',
        'version_string',
    )


class Status(SocorroMiddleware):

    possible_params = (
        'duration',
    )

    def get(self, decode_json=True, **kwargs):
        duration = kwargs.get('duration') or 12
        return self.fetch(
            '/server_status/duration/%s' % duration,
            expect_json=decode_json
        )

    API_WHITELIST = None


class CrontabberState(SocorroMiddleware):

    URL_PREFIX = '/crontabber_state/'

    cache_seconds = 60 * 5  # 5 minutes

    # will never contain PII
    API_WHITELIST = None


class DailyBuilds(SocorroMiddleware):

    URL_PREFIX = '/products/builds/'

    required_params = (
        'product',
    )
    possible_params = (
        'version',
    )

    API_WHITELIST = (
        'beta_number',
        'build_type',
        'buildid',
        'date',
        'platform',
        'product',
        'repository',
        'version',
    )


class CrashTrends(SocorroMiddleware):

    URL_PREFIX = '/crashtrends/'

    required_params = (
        'product',
        'version',
        ('start_date', datetime.date),
        ('end_date', datetime.date),
    )

    API_WHITELIST = {
        'crashtrends': (
            'build_date',
            'version_string',
            'product_version',
            'days_out',
            'report_count',
            'report_date',
            'product_name',
            'product_version_id',
        ),
    }


class BugzillaAPI(SocorroCommon):
    base_url = settings.BZAPI_BASE_URL
    username = password = None

#    def get(self, *args, **kwargs):
#        raise NotImplementedError("You're supposed to override this")


class BugzillaBugInfo(BugzillaAPI):

    def get(self, bugs, fields):
        if isinstance(bugs, basestring):
            bugs = [bugs]
        if isinstance(fields, basestring):
            fields = [fields]
        params = {
            'bugs': ','.join(bugs),
            'fields': ','.join(fields),
        }
        headers = {'Accept': 'application/json',
                   'Content-Type': 'application/json'}
        url = ('/bug?id=%(bugs)s&include_fields=%(fields)s' % params)
        return self.fetch(url, headers)


class SignatureURLs(SocorroMiddleware):

    URL_PREFIX = '/signatureurls/'

    required_params = (
        ('products', list),
        'signature',
        ('start_date', datetime.datetime),
        ('end_date', datetime.datetime),
    )

    possible_params = (
        ('versions', list),
    )

    API_WHITELIST = {
        'hits': (
            'crash_count',
            # deliberately leaving out 'url',
            # is that correct?
        )
    }


class Correlations(SocorroMiddleware):

    URL_PREFIX = '/correlations/'

    required_params = (
        'report_type',
        'product',
        'version',
        'signature',
        'platform',
    )

    API_WHITELIST = (
        'count',
        'load',
        'reason',
    )


class CorrelationsSignatures(SocorroMiddleware):

    URL_PREFIX = '/correlations/signatures/'

    required_params = (
        'report_type',
        'product',
        'version',
    )
    possible_params = (
        ('platforms', list),
    )

    API_WHITELIST = (
        'hits',
        'total',
    )


class Field(SocorroMiddleware):

    URL_PREFIX = '/field/'

    required_params = (
        'name',
    )


class CrashesFrequency(SocorroMiddleware):

    URL_PREFIX = '/crashes/frequency/'

    required_params = (
        'signature',
    )

    possible_params = (
        ('products', list),
        ('from', datetime.datetime),
        ('to', datetime.datetime),
        ('versions', list),
        ('os', list),
        ('reasons', list),
        ('release_channels', list),
        ('build_ids', list),
        ('build_from', list),
        ('build_to', list),
        'report_process',
        'report_type',
        ('plugin_in', list),
        'plugin_search_mode',
        ('plugin_terms', list),
    )

    API_WHITELIST = (
        'hits',
        'total',
    )


class SkipList(SocorroMiddleware):

    URL_PREFIX = '/skiplist/'

    possible_params = (
        'category',
        'rule',
    )

    API_WHITELIST = (
        'hits',
        'total',
    )

    cache_seconds = 0

    def post(self, **payload):
        return super(SkipList, self).post(self.URL_PREFIX, payload)

    def delete(self, **kwargs):
        url = self.URL_PREFIX + 'category/%(category)s/rule/%(rule)s/'
        params = kwargs
        self.urlencode_params(params)
        url = url % params
        return super(SkipList, self).delete(url, None)


class CrashesCountByDay(SocorroMiddleware):

    cache_seconds = 60 * 60 * 18  # 18 hours of cache should be good.

    URL_PREFIX = '/crashes/count_by_day/'

    required_params = (
        'signature',
        'start_date'
    )

    possible_params = (
        'end_date',
    )

    API_WHITELIST = None

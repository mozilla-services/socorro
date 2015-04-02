"""
Remember! Every new model you introduce here automatically gets exposed
in the public API in the `api` app.
"""
import datetime
import functools
import hashlib
import os
import urlparse
import json
import logging
import requests
import stat
import time

import ujson

from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import iri_to_uri
from django.template.defaultfilters import slugify

from crashstats import scrubber
from crashstats.api.cleaner import Cleaner
# The reason to import this is if this file is, for some reason, imported
# before django's had a chance to register all models.py in the
# settings.INSTALLED_APPS list.
# This can happen if you use django-nose on a specific file.
# See https://bugzilla.mozilla.org/show_bug.cgi?id=1121749
from crashstats.dataservice import models
models = models  # silence pyflakes

logger = logging.getLogger('crashstats_models')


class Lazy(object):

    # used because None can be an actual result
    _marker = object()

    def __init__(self, func):
        self.func = func
        self.materialized = self._marker

    def materialize(self):
        if self.materialized is self._marker:
            self.materialized = self.func()
        return self.materialized

    def __iter__(self):
        return self.materialize().__iter__()

    def __add__(self, other):
        return self.materialize().__add__(other)


def get_api_whitelist(*args, **kwargs):

    def get_from_es(namespace, baseline=None):
        # @namespace is something like 'raw_crash' or 'processed_crash'

        cache_key = 'api_supersearch_fields_%s' % namespace
        fields = cache.get(cache_key)

        if fields is None:
            # This needs to be imported in runtime because otherwise you'll
            # get a circular import.
            from crashstats.supersearch.models import SuperSearchFields
            all = SuperSearchFields().get()
            fields = []
            if baseline:
                if isinstance(baseline, tuple):
                    baseline = list(baseline)
                fields.extend(baseline)
            for meta in all.itervalues():
                if (
                    meta['namespace'] == namespace and
                    not meta['permissions_needed'] and
                    meta['is_returned']
                ):
                    if meta['in_database_name'] not in fields:
                        fields.append(meta['in_database_name'])
            fields = tuple(fields)

            # Cache for 1 hour.
            cache.set(cache_key, fields, 60 * 60)
        return fields

    return Lazy(
        functools.partial(get_from_es, *args, **kwargs)
    )


class BadStatusCodeError(Exception):
    def __init__(self, status, message="Bad status code"):
        self.message = message
        self.status = status
        combined = '%d: %s' % (status, message)
        super(BadStatusCodeError, self).__init__(combined)


class RequiredParameterError(Exception):
    pass


class ParameterTypeError(Exception):
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


def measure_fetches(method):

    @functools.wraps(method)
    def inner(*args, **kwargs):
        t0 = time.time()
        result = method(*args, **kwargs)
        if not (isinstance(result, tuple) and len(result) == 2):
            # happens when fetch() is used recursively
            return result
        result, hit_or_miss = result
        if not getattr(settings, 'ANALYZE_MODEL_FETCHES', False):
            return result
        t1 = time.time()
        self = args[0]
        url = args[1]
        msecs = int((t1 - t0) * 1000)
        hit_or_miss = 'HIT' if hit_or_miss else 'MISS'

        try:
            groups = (('classes', self.__class__.__name__), ('urls', url))
            for value_type, value in groups:
                key = 'all_%s' % value_type
                all = cache.get(key) or []
                if value not in all:
                    all.append(value)
                    cache.set(key, all, 60 * 60 * 24)

                valuekey = hashlib.md5(value.encode('utf-8')).hexdigest()
                for prefix, incr in (('times', msecs), ('uses', 1)):
                    key = '%s_%s_%s' % (prefix, hit_or_miss, valuekey)
                    try:
                        cache.incr(key, incr)
                    except ValueError:
                        cache.set(key, incr, 60 * 60 * 24)
        except Exception:
            logger.error('Unable to collect model fetches data', exc_info=True)
        finally:
            return result

    return inner


def memoize(function):
    """Decorator for model methods to cache in memory or the filesystem
    using CACHE_MIDDLEWARE and/or CACHE_MIDDLEWARE_FILES Django config"""

    @functools.wraps(function)
    def memoizer(instance, *args, **kwargs):

        def get_cached_result(key, instance, stringified_args):
            result = cache.get(key)
            if result is not None:
                logger.debug("CACHE HIT %s" % stringified_args)
                return result

            # Didn't find key in middleware_cache, so try filecache
            cache_file = get_cache_filename(key, instance)
            if settings.CACHE_MIDDLEWARE_FILES and os.path.isfile(cache_file):
                # but is it fresh enough?
                age = time.time() - os.stat(cache_file)[stat.ST_MTIME]
                if age > instance.cache_seconds:
                    logger.debug("CACHE FILE TOO OLD")
                    os.remove(cache_file)
                else:
                    logger.debug("CACHE FILE HIT %s" % stringified_args)
                    delete_cache_file = False
                    with open(cache_file) as f:
                        if instance.expect_json:
                            try:
                                return json.load(f)
                            except ValueError:
                                logger.warn(
                                    "%s is not a valid JSON file and will "
                                    "be deleted" % (
                                        cache_file,
                                    )
                                )
                                delete_cache_file = True
                        else:
                            return f.read()
                    if delete_cache_file:
                        os.remove(cache_file)

            # Didn't find our values in the cache
            return None

        def get_cache_filename(key, instance):
            root = settings.CACHE_MIDDLEWARE_FILES
            if isinstance(root, bool):
                cache_file = os.path.join(
                    settings.ROOT,
                    'models-cache'
                )
            else:
                cache_file = root

            cache_file = os.path.join(cache_file, classname, key)
            cache_file += instance.expect_json and '.json' or '.dump'
            return cache_file

        def refresh_caches(key, instance, result):
            cache.set(key, result, instance.cache_seconds)
            cache_file = get_cache_filename(key, instance)
            if cache_file and settings.CACHE_MIDDLEWARE_FILES:
                if not os.path.isdir(os.path.dirname(cache_file)):
                    os.makedirs(os.path.dirname(cache_file))
                with open(cache_file, 'w') as f:
                    if instance.expect_json:
                        json.dump(result, f, indent=2)
                    else:
                        f.write(result)

        # Check if item is in the cache and call the decorated method if needed
        do_cache = settings.CACHE_MIDDLEWARE and instance.cache_seconds
        if do_cache:
            classname = instance.__class__.__name__
            stringified_args = classname + " " + str(kwargs)
            key = hashlib.md5(stringified_args).hexdigest()
            result = get_cached_result(key, instance, stringified_args)
            if result is not None:
                return result

        # Didn't find it in the cache or not using a cache, so run our function
        result = function(instance, *args, **kwargs)

        if do_cache:
            refresh_caches(key, instance, result)
        return result

    return memoizer


class SocorroCommon(object):
    """ Soon to be deprecated by classes using socorro dataservice classes
    and memoize decorator """

    # by default, we don't need username and password
    username = password = None
    # http_host
    http_host = None

    # default cache expiration time if applicable
    cache_seconds = 60 * 60

    @measure_fetches
    def fetch(
        self,
        url,
        headers=None,
        method='get',
        params=None,
        data=None,
        expect_json=True,
        dont_cache=False,
        refresh_cache=False,
        retries=None,
        retry_sleeptime=None
    ):

        if retries is None:
            retries = settings.MIDDLEWARE_RETRIES
        if retry_sleeptime is None:
            retry_sleeptime = settings.MIDDLEWARE_RETRY_SLEEPTIME

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
            # Prepare a fake Request object to use it to get the full URL that
            # will be used. Needed for caching.
            req = requests.Request(
                method=method.upper(),
                url=url,
                auth=auth,
                headers=headers,
                data=data,
                params=params,
            ).prepare()
            cache_key = hashlib.md5(iri_to_uri(req.url)).hexdigest()

            if not refresh_cache:
                result = cache.get(cache_key)
                if result is not None:
                    logger.debug("CACHE HIT %s" % url)
                    return result, True

                # not in the memcache/locmem but is it in cache files?
                if settings.CACHE_MIDDLEWARE_FILES:
                    root = settings.CACHE_MIDDLEWARE_FILES
                    if isinstance(root, bool):
                        cache_file = os.path.join(
                            settings.ROOT,
                            'models-cache'
                        )
                    else:
                        cache_file = root
                    split = urlparse.urlparse(url)
                    cache_file = os.path.join(
                        cache_file,
                        split.netloc,
                        _clean_path(split.path)
                    )
                    if split.query:
                        cache_file = os.path.join(
                            cache_file,
                            _clean_query(split.query)
                        )
                    if expect_json:
                        cache_file = os.path.join(
                            cache_file,
                            '%s.json' % cache_key
                        )
                    else:
                        cache_file = os.path.join(
                            cache_file,
                            '%s.dump' % cache_key
                        )

                    if os.path.isfile(cache_file):
                        # but is it fresh enough?
                        age = time.time() - os.stat(cache_file)[stat.ST_MTIME]
                        if age > self.cache_seconds:
                            logger.debug("CACHE FILE TOO OLD")
                            os.remove(cache_file)
                        else:
                            logger.debug("CACHE FILE HIT %s" % url)
                            delete_cache_file = False
                            with open(cache_file) as f:
                                if expect_json:
                                    try:
                                        return json.load(f), True
                                    except ValueError:
                                        logger.warn(
                                            "%s is not a valid JSON file and "
                                            "will be deleted" % (
                                                cache_file,
                                            ),
                                            exc_info=True
                                        )
                                        delete_cache_file = True
                                else:
                                    return f.read(), True
                            if delete_cache_file:
                                os.remove(cache_file)

        if method == 'post':
            request_method = requests.post
            logger.info("POSTING TO %s" % url)
        elif method == 'get':
            request_method = requests.get
            logger.info("FETCHING %s" % url)
        elif method == 'put':
            request_method = requests.put
            logger.info("PUTTING TO %s" % url)
        elif method == 'delete':
            request_method = requests.delete
            logger.info("DELETING ON %s" % url)
        else:
            raise ValueError(method)

        try:
            resp = request_method(
                url=url,
                auth=auth,
                headers=headers,
                data=data,
                params=params,
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
                params=params,
                expect_json=expect_json,
                dont_cache=dont_cache,
                retry_sleeptime=retry_sleeptime,
                retries=retries - 1
            )

        if resp.status_code >= 400 and resp.status_code < 500:
            raise BadStatusCodeError(resp.status_code, resp.content)
        elif not resp.status_code == 200:
            raise BadStatusCodeError(
                resp.status_code,
                '%s (%s)' % (resp.content, url)
            )

        result = resp.content
        if expect_json:
            result = ujson.loads(result)

        if cache_key:
            cache.set(cache_key, result, self.cache_seconds)
            if cache_file:
                if not os.path.isdir(os.path.dirname(cache_file)):
                    os.makedirs(os.path.dirname(cache_file))
                if expect_json:
                    json.dump(result, open(cache_file, 'w'), indent=2)
                else:
                    open(cache_file, 'w').write(result)

        return result, False

    def _complete_url(self, url):
        if url.startswith('/'):
            if not getattr(self, 'base_url', None):
                raise NotImplementedError("No base_url defined in context")
            url = '%s%s' % (self.base_url, url)
        return url


class SocorroMiddleware(SocorroCommon):
    """ Soon to be deprecated by classes using socorro dataservice classes
    and memoize decorator """

    base_url = settings.MWARE_BASE_URL
    http_host = settings.MWARE_HTTP_HOST
    username = settings.MWARE_USERNAME
    password = settings.MWARE_PASSWORD

    default_date_format = '%Y-%m-%d'
    default_datetime_format = '%Y-%m-%dT%H:%M:%S'

    # by default, no particular permission is needed to use a model
    API_REQUIRED_PERMISSIONS = None

    # by default, no binary response
    API_BINARY_RESPONSE = {}
    # and thus no needed binary filename
    API_BINARY_FILENAME = None

    # by default no special permissions are needed for binary response
    API_BINARY_PERMISSIONS = ()

    def get(self, expect_json=True, **kwargs):
        return self._get(expect_json=expect_json, **kwargs)

    def post(self, url, payload):
        return self._post(url, payload)

    def put(self, url, payload):
        return self._post(url, payload, method='put')

    def delete(self, **kwargs):
        # Set dont_cache=True here because we never want to cache a delete.
        return self._get(
            method='delete',
            dont_cache=True,
            **kwargs
        )

    def _post(self, url, payload, method='post'):
        # set dont_cache=True here because the request depends on the payload
        return self.fetch(
            url,
            method=method,
            data=payload,
            dont_cache=True,
        )

    def _get(
        self,
        method='get',
        dont_cache=False,
        refresh_cache=False,
        expect_json=True,
        **kwargs
    ):
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

        defaults = getattr(self, 'defaults', {})
        aliases = getattr(self, 'aliases', {})

        for key, value in defaults.items():
            kwargs[key] = kwargs.get(key) or value

        params = self.kwargs_to_params(kwargs)
        for param in params:
            if aliases.get(param):
                params[aliases.get(param)] = params[param]
                del params[param]

        return self.fetch(
            url,
            params=params,
            method=method,
            dont_cache=dont_cache,
            refresh_cache=refresh_cache,
            expect_json=expect_json,
        )

    def kwargs_to_params(self, kwargs):
        """Return a dict suitable for making the URL based on inputted
        keyword arguments to the .get() method.

        This method will do a "rough" type checking. "Rough" because
        it's quite forgiving. For example, things that *can( be
        converted are left alone. For example, if value is '123' and
        the required type is `int` then it's fine.
        Also, if you pass in a datetime.datetime instance and it's
        supposed to be a datetime.date instance, it converts it
        for you.

        Parameters that are *not* required and have a falsy value
        are ignored/skipped.

        Lastly, certain types are forcibly converted to safe strings.
        For example, datetime.datetime instance become strings with
        their `.isoformat()` method. datetime.date instances are converted
        to strings with `strftime('%Y-%m-%d')`.
        And any lists are converted to strings by joining on a `+`
        character.
        And some specially named parameters are extra encoded for things
        like `/` and `+` in the string.
        """
        params = {}

        for param in self.get_annotated_params():
            name = param['name']
            if param['required'] and not kwargs.get(name):
                raise RequiredParameterError(name)
            value = kwargs.get(name)
            if not value:
                continue

            if isinstance(value, param['type']):
                if (
                    isinstance(value, datetime.datetime) and
                    param['type'] is datetime.date
                ):
                    value = value.date()
            else:
                if isinstance(value, basestring) and param['type'] is list:
                    value = [value]
                elif param['type'] is basestring:
                    # we'll let the url making function later deal with this
                    pass
                else:
                    try:
                        # test if it can be cast
                        param['type'](value)
                    except (TypeError, ValueError):
                        raise ParameterTypeError(
                            'Expected %s to be a %s not %s' % (
                                name,
                                param['type'],
                                type(value)
                            )
                        )
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            elif isinstance(value, datetime.date):
                value = value.strftime('%Y-%m-%d')
            params[name] = value
        return params

    def get_annotated_params(self):
        """return an iterator. One dict for each parameter that the
        class takes.
        Each dict must have the following keys:
            * name
            * type
            * required
        """
        for required, items in ((True, getattr(self, 'required_params', [])),
                                (False, getattr(self, 'possible_params', []))):
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

    def get(self, currentproducts=None):
        if currentproducts is None:
            currentproducts = CurrentProducts().get()
        products = currentproducts['products']
        releases = currentproducts['hits']
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

    def post(self, **data):
        # why does this feel so clunky?!
        return super(CurrentProducts, self).post(self.URL_PREFIX, data)


class Releases(SocorroMiddleware):

    URL_PREFIX = '/releases/release/'

    possible_params = (
        ('beta_number', int),
    )

    required_params = (
        'product',
        'version',
        'update_channel',
        'build_id',
        'platform',
        'release_channel',
        ('throttle', int),
    )

    def post(self, **data):
        # why does this feel so clunky?!
        return super(Releases, self).post(self.URL_PREFIX, data)


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

    URL_PREFIX = '/platforms/'

    API_WHITELIST = (
        'code',
        'name',
    )

    def get(self):
        # When we first exposed this model it would just return a plain
        # list. It was hardcoded. To avoid deprecating things for people
        # we continue this trandition by only returning the hits directly
        result = super(Platforms, self).get()
        return [
            dict(x, display=x['name'] in settings.DISPLAY_OS_NAMES)
            for x in result['hits']
        ]


class CrashesPerAdu(SocorroMiddleware):
    # Fetch records for active daily installs.

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
            'is_gc_count',
        )
    }


class ProcessedCrash(SocorroMiddleware):
    URL_PREFIX = '/crash_data/'

    required_params = (
        'crash_id',
    )
    possible_params = (
        'datatype',
    )

    aliases = {
        'crash_id': 'uuid',
    }

    defaults = {
        'datatype': 'processed',
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
        'json_dump',
        'upload_file_minidump_*',
    )

    # Same as for RawCrash, we supplement with the existing list, on top
    # of the Super Search Fields, because there are many fields not yet
    # listed in Super Search Fields.
    API_WHITELIST = get_api_whitelist(
        'processed_crash',
        baseline=API_WHITELIST
    )

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL),
        ('user_comments', scrubber.URL),
    )


class UnredactedCrash(ProcessedCrash):
    URL_PREFIX = '/crash_data/'

    defaults = {
        'datatype': 'unredacted',
    }

    API_REQUIRED_PERMISSIONS = (
        'crashstats.view_exploitability',
        'crashstats.view_pii'
    )

    # Why no `API_WHITELIST` here?
    #
    # Basically, the intention is this; the `UnredactedCrash` model should
    # only be usable if you have those two permissions. And if you have
    # `view_pii` it doesn't matter what `API_WHITELIST` does at all
    # because of this. Basically, it doesn't even get to the
    # `API_WHITELIST checking stuff.
    #
    # The assumption is that "unredacted = processed + sensitive stuff". So,
    # if you don't have `view_pii` you won't get anything here you don't
    # already get from `ProcessedCrash`. And if you have `view_pii`
    # there's no point writing down a whitelist.


class RawCrash(SocorroMiddleware):
    """
    To access any of the raw dumps (e.g. format=raw) you need an API
    token that carries the "View Raw Dumps" permission.
    """

    URL_PREFIX = '/crash_data/'

    required_params = (
        'crash_id',
    )
    possible_params = (
        'format',
        'name',
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
        'B2G_OS_Version',
        'Theme',
        'Version',
        'id',
        'Vendor',
        'EMCheckCompatibility',
        'Throttleable',
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
        'Android_Display',
        'Android_Board',
        'Android_Model',
        'Android_Manufacturer',
        'Android_CPU_ABI',
        'Android_CPU_ABI2',
        'Android_Fingerprint',
        'throttle_rate',
        'AsyncShutdownTimeout',
        'BIOS_Manufacturer',
        'upload_file_minidump_*',
        'useragent_locale',
        'AdapterSubsysID',
        'AdapterDriverVersion',
        'ShutdownProgress',
        'DOMIPCEnabled',
    )

    # The reason we use the old list and pass it into the more dynamic wrapper
    # for getting the complete list is because we're apparently way behind
    # on having all of these added to the Super Search Fields.
    API_WHITELIST = get_api_whitelist('raw_crash', baseline=API_WHITELIST)

    API_CLEAN_SCRUB = (
        ('Comments', scrubber.EMAIL),
        ('Comments', scrubber.URL),
    )

    # If this is matched in the query string parameters, then
    # we will return the response in binary format in the API
    API_BINARY_RESPONSE = {
        'format': 'raw',
    }
    API_BINARY_FILENAME = '%(crash_id)s.dmp'
    # permissions needed to download it as a binary response
    API_BINARY_PERMISSIONS = (
        'crashstats.view_rawdump',
    )

    def get(self, **kwargs):
        format = kwargs.get('format', 'meta')
        if format == 'raw_crash':
            format = kwargs['format'] = 'raw'
        kwargs['expect_json'] = format != 'raw'
        return super(RawCrash, self).get(**kwargs)


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
        'product',
        'version',
    )

    defaults = {
        'page': 1
    }

    API_REQUIRED_PERMISSIONS = (
        'crashstats.view_exploitability',
    )

    API_WHITELIST = None


class Bugs(SocorroMiddleware):

    required_params = settings.DATASERVICE_CONFIG.services.Bugs.required_params
    expect_json = settings.DATASERVICE_CONFIG.services.Bugs.output_is_json

    API_WHITELIST = settings.DATASERVICE_CONFIG.services.Bugs.api_whitelist

    @memoize
    def get(self, **kwargs):
        bugs_cls = settings.DATASERVICE_CONFIG.services.Bugs.cls
        bugs = bugs_cls(settings.DATASERVICE_CONFIG.services.Bugs)

        if not kwargs.get('signatures'):
            raise ValueError("'signatures' can not be empty")
        return bugs.post(**kwargs)


class SignaturesByBugs(SocorroMiddleware):

    settings.DATASERVICE_CONFIG.services.Bugs.required_params = (
        'bug_ids',
    )
    required_params = settings.\
        DATASERVICE_CONFIG.services.Bugs.required_params
    expect_json = settings.DATASERVICE_CONFIG.services.Bugs.output_is_json

    API_WHITELIST = settings.DATASERVICE_CONFIG.services.Bugs.api_whitelist

    def get(self, **kwargs):
        bugs_cls = settings.DATASERVICE_CONFIG.services.Bugs.cls
        bugs = bugs_cls(settings.DATASERVICE_CONFIG.services.Bugs)

        if not kwargs.get('bug_ids'):
            raise ValueError("'bug_ids' can not be empty")
        return bugs.post(**kwargs)


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
        ('report_types', list),
        'signature',
        ('start_date', datetime.date),
        ('end_date', datetime.date),
    )

    possible_params = (
        ('versions', list),
        'report_type',  # kept for legacy
    )

    API_WHITELIST = (
        'category',
        'percentage',
        'product_name',
        'version_string',
        'reports',
    )


class Status(SocorroMiddleware):

    possible_params = (
        'duration',
    )

    cache_seconds = 0

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
        ('from', datetime.date),
        ('to', datetime.date),
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


class GCCrashes(SocorroMiddleware):

    cache_seconds = 60

    URL_PREFIX = '/gccrashes/'
    required_params = (
        'product',
        'version',
    )

    possible_params = (
        ('from_date', datetime.date),
        ('to_date', datetime.date),
    )

    API_WHITELIST = (
        'hits',
        'total',
    )


class GraphicsDevices(SocorroMiddleware):

    cache_seconds = 0

    URL_PREFIX = '/graphics_devices/'

    API_WHITELIST = (
        'hits',
        'total',
    )

    required_params = (
        'vendor_hex',
        'adapter_hex',
    )

    def post(self, payload):
        return super(GraphicsDevices, self).post(self.URL_PREFIX, payload)


class LagLog(SocorroMiddleware):

    cache_seconds = 0

    URL_PREFIX = '/laglog/'
    required_params = ()
    possible_params = ()

    # never anything sensitive
    API_WHITELIST = None


class AduBySignature(SocorroMiddleware):

    URL_PREFIX = '/crashes/adu_by_signature/'
    required_params = (
        'product_name',
        'signature',
        'channel',
    )

    possible_params = (
        ('start_date', datetime.date),
        ('end_date', datetime.date),
    )

    API_WHITELIST = (
        'hits',
        'total',
    )

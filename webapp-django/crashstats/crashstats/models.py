"""
Remember! Every new model you introduce here automatically gets exposed
in the public API in the `api` app.
"""
import datetime
import functools
import hashlib
import logging
import time

from configman import configuration, Namespace

from socorro.lib import BadArgumentError
from socorro.external.es.base import ElasticsearchConfig
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.external.rabbitmq.crashstorage import (
    ReprocessingOneRabbitMQCrashStore,
    PriorityjobRabbitMQCrashStore,
)
import socorro.external.postgresql.platforms
import socorro.external.postgresql.bugs
import socorro.external.postgresql.products
import socorro.external.postgresql.graphics_devices
import socorro.external.postgresql.crontabber_state
import socorro.external.postgresql.adi
import socorro.external.postgresql.product_build_types
import socorro.external.postgresql.signature_first_date
import socorro.external.postgresql.server_status
import socorro.external.postgresql.releases
import socorro.external.boto.crash_data

from socorro.app import socorro_app

from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import iri_to_uri
from django.template.defaultfilters import slugify

from crashstats import scrubber
from crashstats.base.utils import requests_retry_session


logger = logging.getLogger('crashstats.models')


class DeprecatedModelError(DeprecationWarning):
    """Used when a deprecated model is being used in debug mode"""


class BugzillaRestHTTPUnexpectedError(Exception):
    """Happens Bugzilla's REST API doesn't give us a HTTP error we expect"""


def config_from_configman():
    definition_source = Namespace()
    definition_source.namespace('logging')
    definition_source.logging = socorro_app.App.required_config.logging

    definition_source.namespace('metricscfg')
    definition_source.metricscfg = socorro_app.App.required_config.metricscfg

    definition_source.namespace('elasticsearch')
    definition_source.elasticsearch.add_option(
        'elasticsearch_class',
        default=ElasticsearchConfig,
    )
    definition_source.namespace('database')
    definition_source.database.add_option(
        'database_storage_class',
        default=PostgreSQLCrashStorage,
    )
    definition_source.namespace('queuing')
    definition_source.queuing.add_option(
        'rabbitmq_reprocessing_class',
        default=ReprocessingOneRabbitMQCrashStore,
    )
    definition_source.namespace('priority')
    definition_source.priority.add_option(
        'rabbitmq_priority_class',
        default=PriorityjobRabbitMQCrashStore,
    )
    definition_source.namespace('data')
    definition_source.data.add_option(
        'crash_data_class',
        default=socorro.external.boto.crash_data.SimplifiedCrashData,
    )
    config = configuration(
        definition_source=definition_source,
        values_source_list=[
            settings.SOCORRO_IMPLEMENTATIONS_CONFIG,
        ]
    )
    # The ReprocessingOneRabbitMQCrashStore crash storage, needs to have
    # a "logger" in the config object. To avoid having to use the
    # logger set up by configman as an aggregate, we just use the
    # same logger as we have here in the webapp.
    config.queuing.logger = logger
    config.priority.logger = logger
    config.data.logger = logger
    return config


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

    return functools.partial(get_from_es, *args, **kwargs)


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
        msecs = int((t1 - t0) * 1000)
        hit_or_miss = 'HIT' if hit_or_miss else 'MISS'

        try:
            value = self.__class__.__name__
            key = 'all_classes'
            all_ = cache.get(key) or []
            if value not in all_:
                all_.append(value)
                cache.set(key, all_, 60 * 60 * 24)

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


class SocorroCommon(object):

    # by default, we don't need username and password
    username = password = None
    # http_host
    http_host = None

    # default cache expiration time if applicable
    cache_seconds = 60 * 60

    # At the moment, we're supporting talk HTTP to the middleware AND
    # instantiating implementation classes so this is None by default.
    implementation = None

    # By default, the model is not called with an API user.
    # This is applicable when the models are used from views that
    # originate from pure class instanciation instead of from
    # web GET or POST requests
    api_user = None

    @measure_fetches
    def fetch(
        self,
        implementation,
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
        cache_key = None

        if (
            settings.CACHE_IMPLEMENTATION_FETCHES and
            not dont_cache and
            self.cache_seconds
        ):
            name = implementation.__class__.__name__
            cache_key = hashlib.md5(
                name + unicode(params)
            ).hexdigest()

            if not refresh_cache:
                result = cache.get(cache_key)
                if result is not None:
                    logger.debug(
                        "CACHE HIT %s" % implementation.__class__.__name__
                    )
                    return result, True

        implementation_method = getattr(implementation, method)
        result = implementation_method(**params)

        if cache_key:
            cache.set(cache_key, result, self.cache_seconds)

        return result, False

    def _complete_url(self, url):
        if url.startswith('/'):
            if not getattr(self, 'base_url', None):
                raise NotImplementedError("No base_url defined in context")
            url = '%s%s' % (self.base_url, url)
        return url

    def get_implementation(self):
        if self.implementation:
            key = self.__class__.__name__
            global _implementations
            try:
                return _implementations[key]
            except KeyError:
                config = config_from_configman()
                if self.implementation_config_namespace:
                    config = config[self.implementation_config_namespace]
                _implementations[key] = self.implementation(
                    config=config
                )
                return _implementations[key]
        return None

    @classmethod
    def clear_implementations_cache(cls):
        # Why not allow of specific keys to clear?
        # Because it's sometimes complicated to know which implementation
        # something depends on. "Is it SuperSearch or SuperSearchUnredacted?"
        # Also, the price of losing them all is not that expensive.
        global _implementations
        _implementations = {}


# Global cache dict to helps us only instantiate an implementation
# class only once per process.
_implementations = {}


class SocorroMiddleware(SocorroCommon):

    # by default, assume the class to not have an implementation reference
    implementation = None

    # The default, is 'database' which means it's to do with talking
    # to a PostgreSQL based implementation.
    implementation_config_namespace = 'database'

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
        a call to the parent `fetch` method.
        """
        implementation = self.get_implementation()

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
            implementation,
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
            value = kwargs.get(name)

            # 0 is a perfectly fine value, it should not be considered "falsy".
            if not value and value is not 0 and value is not False:
                if param['required']:
                    raise RequiredParameterError(name)
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


class ProductVersions(SocorroMiddleware):

    implementation = socorro.external.postgresql.products.ProductVersions

    possible_params = (
        ('product', list),
        ('version', list),
        ('is_featured', bool),
        'start_date',
        'end_date',
        ('active', bool),
        ('is_rapid_beta', bool),
        ('build_type', list),
    )

    API_WHITELIST = (
        'hits',
        'total',
    )

    def post(self, **data):
        return self.get_implementation().post(**data)


class Releases(SocorroMiddleware):

    implementation = socorro.external.postgresql.releases.Releases

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
        return self.get_implementation().post(**data)


class Platforms(SocorroMiddleware):

    implementation = socorro.external.postgresql.platforms.Platforms

    API_WHITELIST = (
        'code',
        'name',
    )

    def get(self):
        # XXX (peterbe, Mar 2016): Oh I wish we had stats on how many people
        # are using /api/Platforms/. If we knew we could be brave about
        # removing this legacy hack.

        # When we first exposed this model it would just return a plain
        # list. It was hardcoded. To avoid deprecating things for people
        # we continue this trandition by only returning the hits directly
        result = super(Platforms, self).get()
        return [
            dict(x, display=x['name'] in settings.DISPLAY_OS_NAMES)
            for x in result['hits']
        ]

    def get_all(self):
        """Return all platforms without reducing them to a pre-configured list.
        """
        return super(Platforms, self).get()


class ProcessedCrash(SocorroMiddleware):

    implementation = socorro.external.boto.crash_data.SimplifiedCrashData
    implementation_config_namespace = 'data'

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
        'mdsw_status_string',
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

    implementation = socorro.external.boto.crash_data.SimplifiedCrashData
    implementation_config_namespace = 'data'

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
        format_ = kwargs.get('format', 'meta')
        if format_ == 'raw_crash':
            # legacy
            format_ = kwargs['format'] = 'raw'
        expect_dict = format_ != 'raw'
        result = super(RawCrash, self).get(**kwargs)
        # This 'result', will either be a binary blob or a python dict.
        # Unless kwargs['format']==raw, this has to be a python dict.
        if expect_dict and not isinstance(result, dict):
            raise BadArgumentError('format')
        return result


class Bugs(SocorroMiddleware):

    implementation = socorro.external.postgresql.bugs.Bugs

    required_params = (
        ('signatures', list),
    )

    API_WHITELIST = {
        'hits': (
            'id',
            'signature',
        ),
    }


class SignaturesByBugs(SocorroMiddleware):

    implementation = socorro.external.postgresql.bugs.Bugs

    required_params = (
        ('bug_ids', list),
    )

    API_WHITELIST = {
        'hits': (
            'id',
            'signature',
        ),
    }


class SignatureFirstDate(SocorroMiddleware):

    # Set to a short cache time because, the only real user of this
    # model is the Top Crasher page and that one uses the highly
    # optimized method `.get_dates()` which internally uses caching
    # for each individual signature and does so with a very long
    # cache time.
    # Making it non-0 is to prevent the stampeding herd on this endpoint
    # alone when exposed in the API.
    cache_seconds = 5 * 60  # 5 minutes only

    implementation = (
        socorro.external.postgresql.signature_first_date.SignatureFirstDate
    )

    required_params = (
        ('signatures', list),
    )

    API_WHITELIST = {
        'hits': (
            'signature',
            'first_date',
            'first_build',
        )
    }

    def get_dates(self, signatures):
        """A highly optimized version, that returns a dictionary where
        the keys are the signature and the values are dicts that look
        like this for example::

            {
                'first_build': u'20101214170338',
                'first_date': datetime.datetime(
                    2011, 1, 17, 21, 24, 18, 979850, tzinfo=...)
                )
            }

        """
        dates = {}
        missing = {}
        for signature in signatures:
            # calculate a good cache key for each signature
            cache_key = 'signature_first_date-{}'.format(
                hashlib.md5(signature.encode('utf-8')).hexdigest()
            )
            cached = cache.get(cache_key)
            if cached is not None:
                dates[signature] = cached
            else:
                # remember the cache keys of those we need to look up
                missing[signature] = cache_key

        if missing:
            hits = super(SignatureFirstDate, self).get(
                signatures=missing.keys()
            )['hits']

            for hit in hits:
                signature = hit.pop('signature')
                cache.set(
                    # get the cache key back
                    missing[signature],
                    # what's left when 'signature' is popped
                    hit,
                    # make it a really large number
                    60 * 60 * 24
                )
                dates[signature] = hit
        return dates


class Status(SocorroMiddleware):

    # This model uses an implementation that only really reads
    # files off disk so it doesn't have to be protected from
    # a stampeding herd.
    cache_seconds = 0

    API_WHITELIST = None

    implementation = (
        socorro.external.postgresql.server_status.ServerStatus
    )


class CrontabberState(SocorroMiddleware):

    implementation = (
        socorro.external.postgresql.crontabber_state.CrontabberState
    )

    # make it small but but non-zero
    cache_seconds = 60  # 1 minute

    # will never contain PII
    API_WHITELIST = None

    def get(self, *args, **kwargs):
        resp = super(CrontabberState, self).get(*args, **kwargs)
        apps = resp['state']

        # Redact last_error data so it doesn't bleed infrastructure info into
        # the world
        for name, state in apps.items():
            if state.get('last_error'):
                # NOTE(willkg): The structure of last_error is defined in
                # crontabber in crontabber/app.py.
                state['last_error'] = {
                    'traceback': 'See error logging system.',
                    'value': 'See error logging system.',
                    'type': state['last_error'].get('type', 'Unknown')
                }
        return resp


class BugzillaBugInfo(SocorroCommon):

    # This is for how long we cache the metadata of each individual bug.
    BUG_CACHE_SECONDS = 60 * 60

    # How patient we are with the Bugzilla REST API
    BUGZILLA_REST_TIMEOUT = 5  # seconds

    @staticmethod
    def make_cache_key(bug_id):
        # This is the same cache key that we use in show_bug_link()
        # the jinja helper function.
        return 'buginfo:{}'.format(bug_id)

    def get(self, bugs):
        if isinstance(bugs, basestring):
            bugs = [bugs]
        fields = ('summary', 'status', 'id', 'resolution')
        results = []
        missing = []
        for bug in bugs:
            cache_key = self.make_cache_key(bug)
            cached = cache.get(cache_key)
            if cached is None:
                missing.append(bug)
            else:
                results.append(cached)
        if missing:
            params = {
                'bugs': ','.join(missing),
                'fields': ','.join(fields),
            }
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            url = settings.BZAPI_BASE_URL + (
                '/bug?id=%(bugs)s&include_fields=%(fields)s' % params
            )
            response = requests_retry_session(
                # BZAPI isn't super reliable, so be extra patient
                retries=5,
                # 502 = Bad Gateway
                # 504 = Gateway Time-out
                status_forcelist=(500, 502, 504),
            ).get(
                url,
                headers=headers,
                timeout=self.BUGZILLA_REST_TIMEOUT,
            )
            if response.status_code != 200:
                raise BugzillaRestHTTPUnexpectedError(response.status_code)

            for each in response.json()['bugs']:
                cache_key = self.make_cache_key(each['id'])
                cache.set(cache_key, each, self.BUG_CACHE_SECONDS)
                results.append(each)
        return {'bugs': results}


class GraphicsDevices(SocorroMiddleware):

    cache_seconds = 0

    implementation = (
        socorro.external.postgresql.graphics_devices.GraphicsDevices
    )

    API_WHITELIST = (
        'hits',
        'total',
    )

    required_params = (
        'vendor_hex',
        'adapter_hex',
    )

    def post(self, **payload):
        return self.get_implementation().post(**payload)

    def get_pairs(self, adapter_hexes, vendor_hexes):
        """return a dict where each tuple of (adapter_hex, vendor_hex)
        corresponds to a (adapter_name, vendor_name) pair."""
        assert len(adapter_hexes) == len(vendor_hexes)
        names = {}
        missing = {}
        for i, adapter_hex in enumerate(adapter_hexes):
            cache_key = (
                'graphics_adapters' + adapter_hex + ':' + vendor_hexes[i]
            )
            name_pair = cache.get(cache_key)
            key = (adapter_hex, vendor_hexes[i])
            if name_pair is not None:
                names[key] = name_pair
            else:
                missing[key] = cache_key

        missing_vendor_hexes = []
        missing_adapter_hexes = []
        for adapter_hex, vendor_hex in missing:
            missing_adapter_hexes.append(adapter_hex)
            missing_vendor_hexes.append(vendor_hex)

        hits = []
        # In order to avoid hitting the maximum URL size limit, we split the
        # query in smaller chunks, and then we reconstruct the results.
        max_number_of_hexes = 50
        for i in range(0, len(missing_vendor_hexes), max_number_of_hexes):
            vendors = set(missing_vendor_hexes[i:i + max_number_of_hexes])
            adapters = set(missing_adapter_hexes[i:i + max_number_of_hexes])
            res = self.get(
                vendor_hex=vendors,
                adapter_hex=adapters,
            )
            hits.extend(res['hits'])

        for group in hits:
            name_pair = (group['adapter_name'], group['vendor_name'])
            key = (group['adapter_hex'], group['vendor_hex'])
            # This if statement is important.
            # For example there repeated adapter hexes that have different
            # vendor hexes. E.g.:
            # breakpad=> select count(distinct vendor_hex) from
            # breakpad-> graphics_device where adapter_hex='0x0102';
            #  count
            # -------
            #     21
            # Therefore it's important to only bother with specific
            # ones that we asked for.
            if key in missing:
                cache_key = missing[key]
                cache.set(cache_key, name_pair, 60 * 60 * 24)
                names[key] = name_pair

        return names


class ADI(SocorroMiddleware):

    implementation = socorro.external.postgresql.adi.ADI

    required_params = (
        ('start_date', datetime.date),
        ('end_date', datetime.date),
        'product',
        ('versions', list),
        ('platforms', list),
    )

    API_WHITELIST = (
        'hits',
        'total',
    )


class ProductBuildTypes(SocorroMiddleware):

    cache_seconds = 60 * 60 * 24

    implementation = (
        socorro.external.postgresql.product_build_types.ProductBuildTypes
    )

    required_params = (
        'product',
    )

    API_WHITELIST = (
        'hits',
    )


class Reprocessing(SocorroMiddleware):
    """Return true if all supplied crash IDs
    were sucessfully submitted onto the reprocessing queue.
    """

    API_REQUIRED_PERMISSIONS = (
        'crashstats.reprocess_crashes',
    )

    API_WHITELIST = None

    implementation = ReprocessingOneRabbitMQCrashStore

    implementation_config_namespace = 'queuing'

    required_params = (
        ('crash_ids', list),
    )

    get = None

    def post(self, **data):
        return self.get_implementation().reprocess(**data)


class Priorityjob(SocorroMiddleware):
    """Return true if all supplied crash IDs
    were sucessfully submitted onto the priority queue.
    """

    implementation = PriorityjobRabbitMQCrashStore

    implementation_config_namespace = 'priority'

    required_params = (
        ('crash_ids', list),
    )

    get = None

    def post(self, **kwargs):
        return self.get_implementation().process(**kwargs)

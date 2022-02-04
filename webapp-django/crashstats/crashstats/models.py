# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Remember! Every new model you introduce here automatically gets exposed
in the public API in the `api` app.
"""

import datetime
import functools
import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils.encoding import iri_to_uri
from django.utils.module_loading import import_string

import markus
from pymemcache.exceptions import MemcacheServerError

from socorro.external.boto.crash_data import SimplifiedCrashData, TelemetryCrashData
from socorro.lib import BadArgumentError
from socorro.lib.ooid import is_crash_id_valid
from socorro.lib.requestslib import session_with_retries

from crashstats.crashstats.configman_utils import config_from_configman


logger = logging.getLogger("crashstats.models")


metrics = markus.get_metrics("webapp.crashstats.models")


# Django models first


class BugAssociationManager(models.Manager):
    def get_bugs_and_related_bugs(self, signatures):
        # NOTE(willkg): We might be able to do this in a single SQL pass, but
        # it seemed prudent to go for simpler for now
        bug_ids = [
            bug[0]
            for bug in self.filter(signature__in=signatures).values_list("bug_id")
        ]
        return self.filter(bug_id__in=bug_ids)


class BugAssociation(models.Model):
    """Specifies assocations between bug ids in Bugzilla and signatures"""

    bug_id = models.IntegerField(null=False, help_text="Bugzilla bug id")
    signature = models.TextField(
        null=False, blank=False, help_text="Socorro-style crash report signature"
    )

    objects = BugAssociationManager()

    class Meta:
        unique_together = ["bug_id", "signature"]


class GraphicsDeviceManager(models.Manager):
    def get_pair(self, vendor_hex, adapter_hex):
        """Returns (vendor_name, adapter_name) or None"""
        try:
            obj = self.get(vendor_hex=vendor_hex, adapter_hex=adapter_hex)
            return (obj.vendor_name, obj.adapter_name)
        except self.model.DoesNotExist:
            return None

    def get_pairs(self, vendor_hexes, adapter_hexes):
        """Returns dict of (vendor_hex, adapter_hex) -> (vendor_name, adapter_name)"""
        # NOTE(willkg): graphics devices are hierarchical, but it's easier to do
        # one query and get some extra stuff than to do one query per vendor
        qs = self.filter(
            vendor_hex__in=vendor_hexes, adapter_hex__in=adapter_hexes
        ).values()
        names = {
            (item["vendor_hex"], item["adapter_hex"]): (
                item["vendor_name"],
                item["adapter_name"],
            )
            for item in qs
        }

        return names


class GraphicsDevice(models.Model):
    """Specifies a device hex/name"""

    vendor_hex = models.CharField(max_length=100)
    adapter_hex = models.CharField(max_length=100, blank=True, null=True)
    vendor_name = models.TextField(blank=True, null=True)
    adapter_name = models.TextField(blank=True, null=True)

    objects = GraphicsDeviceManager()

    class Meta:
        unique_together = ["vendor_hex", "adapter_hex"]

    def __str__(self):
        return "%s %s %s %s" % (
            self.vendor_hex,
            self.vendor_name,
            self.adapter_hex,
            self.adapter_name,
        )


class Platform(models.Model):
    """Lookup table for platforms"""

    name = models.CharField(
        max_length=20,
        blank=False,
        null=False,
        unique=True,
        help_text="Name of the platform",
    )
    short_name = models.CharField(
        max_length=20,
        blank=False,
        null=False,
        help_text="Short abbreviated name of the platform",
    )


class ProductVersion(models.Model):
    """Lookup table for product versions and build information."""

    product_name = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        help_text="ProductName of product as it appears in crash reports",
    )
    release_channel = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        help_text="release channel for this version",
    )
    major_version = models.IntegerField(
        help_text='major version of this version; for example "63.0b4" would be 63'
    )
    release_version = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        help_text="version as it appears in crash reports",
    )
    version_string = models.CharField(
        max_length=50, blank=False, null=False, help_text="actual version"
    )
    build_id = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        help_text="the build id for this version",
    )
    archive_url = models.TextField(
        blank=True,
        null=True,
        help_text="the url on archive.mozilla.org for data on this build",
    )

    class Meta:
        unique_together = [
            "product_name",
            "release_channel",
            "build_id",
            "version_string",
        ]


class Signature(models.Model):
    """Bookkeeping table to keep track of when we first saw a signature."""

    signature = models.TextField(unique=True, help_text="the crash report signature")
    first_build = models.BigIntegerField(
        help_text="the first build id this signature was seen in"
    )
    first_date = models.DateTimeField(
        help_text="the first crash report date this signature was seen in"
    )


class MissingProcessedCrash(models.Model):
    """Bookkeeping table to keep track of missing processed crashes."""

    crash_id = models.CharField(
        unique=True, max_length=36, help_text="crash id for missing processed crash"
    )
    is_processed = models.BooleanField(
        default=False, help_text="whether this crash was eventually processed"
    )
    created = models.DateTimeField(
        auto_now_add=True, help_text="date discovered it was missing"
    )

    def collected_date(self):
        return "20" + self.crash_id[-6:]

    def report_url(self):
        return reverse("crashstats:report_index", args=(self.crash_id,))

    class Meta:
        verbose_name = "missing processed crash"
        verbose_name_plural = "missing processed crashes"


# Socorro x-middleware models


class DeprecatedModelError(DeprecationWarning):
    """Used when a deprecated model is being used in debug mode"""


class BugzillaRestHTTPUnexpectedError(Exception):
    """Happens Bugzilla's REST API doesn't give us a HTTP error we expect"""


def get_api_allowlist(*args, **kwargs):
    def get_from_es(namespace, baseline=None):
        # @namespace is something like 'raw_crash' or 'processed_crash'

        cache_key = "api_supersearch_fields_%s" % namespace
        fields = cache.get(cache_key)

        if fields is None:
            # This needs to be imported in runtime because otherwise you'll
            # get a circular import.
            from crashstats.supersearch.models import SuperSearchFields

            all_fields = SuperSearchFields().get()
            fields = []
            if baseline:
                if isinstance(baseline, tuple):
                    baseline = list(baseline)
                fields.extend(baseline)
            for meta in all_fields.values():
                if (
                    meta["namespace"] == namespace
                    and not meta["permissions_needed"]
                    and meta["is_returned"]
                ):
                    if meta["in_database_name"] not in fields:
                        fields.append(meta["in_database_name"])
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
    """Santize a URL path

    :arg path: the path to sanitize

    :returns: sanitized path

    """
    path = iri_to_uri(path)
    path = path.replace(" ", "_")
    path = "/".join(slugify(x) for x in path.split("/"))
    if path.startswith("/"):
        path = path[1:]
    return path


def _clean_query(query, max_length=30):
    cleaned = _clean_path(query.replace("&", "/"))
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
        if not getattr(settings, "ANALYZE_MODEL_FETCHES", False):
            return result
        t1 = time.time()
        self = args[0]
        msecs = int((t1 - t0) * 1000)
        hit_or_miss = "HIT" if hit_or_miss else "MISS"

        try:
            value = self.__class__.__name__
            key = "all_classes"
            all_ = cache.get(key) or []
            if value not in all_:
                all_.append(value)
                cache.set(key, all_, 60 * 60 * 24)

            valuekey = hashlib.md5(value.encode("utf-8")).hexdigest()
            for prefix, incr in (("times", msecs), ("uses", 1)):
                key = "%s_%s_%s" % (prefix, hit_or_miss, valuekey)
                try:
                    cache.incr(key, incr)
                except ValueError:
                    cache.set(key, incr, 60 * 60 * 24)
        except Exception:
            logger.error("Unable to collect model fetches data", exc_info=True)
        finally:
            return result

    return inner


class SocorroCommon:
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
        method="get",
        params=None,
        data=None,
        expect_json=True,
        dont_cache=False,
        refresh_cache=False,
        retries=None,
        retry_sleeptime=None,
    ):
        cache_key = None

        if (
            settings.CACHE_IMPLEMENTATION_FETCHES
            and not dont_cache
            and self.cache_seconds
        ):
            name = implementation.__class__.__name__
            key_string = name + repr(params)
            cache_key = hashlib.md5(key_string.encode("utf-8")).hexdigest()

            if not refresh_cache:
                result = cache.get(cache_key)
                if result is not None:
                    logger.debug("CACHE HIT %s" % implementation.__class__.__name__)
                    return result, True

        implementation_method = getattr(implementation, method)
        result = implementation_method(**params)
        if cache_key:
            try:
                cache.set(cache_key, result, self.cache_seconds)
            except MemcacheServerError:
                metrics.incr("cache_set_error")

        return result, False

    def _complete_url(self, url):
        if url.startswith("/"):
            if not getattr(self, "base_url", None):
                raise NotImplementedError("No base_url defined in context")
            url = "%s%s" % (self.base_url, url)
        return url

    def get_implementation(self):
        if self.implementation:
            config = config_from_configman()
            if self.implementation_config_namespace:
                config = config[self.implementation_config_namespace]
            return self.implementation(config=config)
        return None


class SocorroMiddleware(SocorroCommon):
    # By default, assume the class to not have an implementation reference
    implementation = None

    # Config namespace to use for the implementation
    implementation_config_namespace = ""

    default_date_format = "%Y-%m-%d"
    default_datetime_format = "%Y-%m-%dT%H:%M:%S"

    # Help text shown in the documentation
    HELP_TEXT = ""

    # By default, no particular permission is needed to use a model
    API_REQUIRED_PERMISSIONS = None

    # By default, no binary response
    API_BINARY_RESPONSE = {}

    # By default no special permissions are needed for binary response
    API_BINARY_PERMISSIONS = ()

    # Whether or not this is public and documented
    IS_PUBLIC = False

    @classmethod
    def get_binary_filename(cls, params):
        return None

    def get(self, expect_json=True, **kwargs):
        return self._get(expect_json=expect_json, **kwargs)

    def post(self, url, payload):
        return self._post(url, payload)

    def options(self):
        return self._options()

    def put(self, url, payload):
        return self._post(url, payload, method="put")

    def delete(self, **kwargs):
        # Set dont_cache=True here because we never want to cache a delete.
        return self._get(method="delete", dont_cache=True, **kwargs)

    def _post(self, url, payload, method="post"):
        # set dont_cache=True here because the request depends on the payload
        return self.fetch(url, method=method, data=payload, dont_cache=True)

    def _options(self, method="options"):
        return {}, False

    def parse_parameters(self, kwargs):
        defaults = getattr(self, "defaults", {})
        aliases = getattr(self, "aliases", {})

        for key, value in defaults.items():
            kwargs[key] = kwargs.get(key) or value

        params = self.kwargs_to_params(kwargs)
        for param in list(params):
            if aliases.get(param):
                params[aliases.get(param)] = params[param]
                del params[param]
        return params

    def _get(
        self,
        method="get",
        dont_cache=False,
        refresh_cache=False,
        expect_json=True,
        **kwargs,
    ):
        """
        Generic `get` method that will take `self.required_params` and
        `self.possible_params` and construct a call to the parent `fetch`
        method.
        """
        implementation = self.get_implementation()

        params = self.parse_parameters(kwargs)

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
            name = param["name"]
            value = kwargs.get(name)

            # 0 is a perfectly fine value, it should not be considered "falsy".
            if not value and value != 0 and value is not False:
                if param["required"]:
                    raise RequiredParameterError(name)
                continue

            if isinstance(value, param["type"]):
                if (
                    isinstance(value, datetime.datetime)
                    and param["type"] is datetime.date
                ):
                    value = value.date()
            else:
                if isinstance(value, str) and param["type"] is list:
                    value = [value]
                elif param["type"] is str:
                    # we'll let the url making function later deal with this
                    pass
                else:
                    try:
                        # test if it can be cast
                        param["type"](value)
                    except (TypeError, ValueError):
                        raise ParameterTypeError(
                            "Expected %s to be a %s not %s"
                            % (name, param["type"], type(value))
                        )
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            elif isinstance(value, datetime.date):
                value = value.strftime("%Y-%m-%d")
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
        for required, items in (
            (True, getattr(self, "required_params", [])),
            (False, getattr(self, "possible_params", [])),
        ):
            for item in items:
                if isinstance(item, str):
                    type_ = str
                    name = item
                elif isinstance(item, dict):
                    type_ = item["type"]
                    name = item["name"]
                else:
                    assert isinstance(item, tuple)
                    name = item[0]
                    type_ = item[1]

                yield {"name": name, "required": required, "type": type_}


class TelemetryCrash(SocorroMiddleware):
    """Model for data we store in the S3 bucket to send to Telemetry"""

    implementation = TelemetryCrashData
    implementation_config_namespace = "telemetrydata"

    required_params = ("crash_id",)
    aliases = {"crash_id": "uuid"}


class ProcessedCrash(SocorroMiddleware):
    implementation = SimplifiedCrashData
    implementation_config_namespace = "crashdata"

    required_params = ("crash_id",)
    possible_params = ("datatype",)

    aliases = {"crash_id": "uuid"}

    defaults = {"datatype": "processed"}

    IS_PUBLIC = True

    HELP_TEXT = """
    API for retrieving crash data generated by processing.

    Requires protected data acess to view protected parts of the raw crash.

    Params:

    * crash_id: the crash id for the processed crash you're requesting

    * datatype: (optional) "processed" for the processed crash as JSON

    """

    # List of fields that are public and don't require view_pii permissions to view.
    API_ALLOWLIST = (
        "additional_minidumps",
        "addons",
        "addons_checked",
        "address",
        "app_notes",
        "build",
        "client_crash_date",
        "completed_datetime",
        "cpu_arch",
        "cpu_info",
        "crashedThread",
        "crash_time",
        "date_processed",
        "dump",
        "flash_version",
        "hangid",
        "hang_type",
        "id",
        "install_age",
        "java_exception",
        "java_stack_trace",
        "json_dump",
        "last_crash",
        "mac_available_memory_sysctl",
        "mac_memory_pressure",
        "mac_memory_pressure_critical_time",
        "mac_memory_pressure_normal_time",
        "mac_memory_pressure_sysctl",
        "mac_memory_pressure_warning_time",
        "major_version",
        "moz_crash_reason",
        "mdsw_status_string",
        "os_name",
        "os_version",
        "pluginFilename",
        "pluginName",
        "pluginVersion",
        "processor_notes",
        "process_type",
        "product",
        "productid",
        "reason",
        "release_channel",
        "ReleaseChannel",
        "signature",
        "started_datetime",
        "success",
        "topmost_filenames",
        "upload_file_minidump_*",
        "uptime",
        "uuid",
        "version",
        "windows_error_reporting",
        "Winsock_LSP",
    )

    # Same as for RawCrash, we supplement with the existing list, on top
    # of the Super Search Fields, because there are many fields not yet
    # listed in Super Search Fields.
    API_ALLOWLIST = get_api_allowlist("processed_crash", baseline=API_ALLOWLIST)


class UnredactedCrash(ProcessedCrash):
    implementation = SimplifiedCrashData
    defaults = {"datatype": "unredacted"}

    API_REQUIRED_PERMISSIONS = ("crashstats.view_exploitability", "crashstats.view_pii")

    IS_PUBLIC = True

    HELP_TEXT = """
    API for retrieving crash data generated by processing including the protected and
    exploitability parts.

    Requires protected data acess.

    Params:

    * crash_id: the crash id for the processed crash you're requesting

    * datatype: (optional) "unredacted" for the unredacted crash as JSON

    """

    # Why no `API_ALLOWLIST` here?
    #
    # Basically, the intention is this; the `UnredactedCrash` model should
    # only be usable if you have those two permissions. And if you have
    # `view_pii` it doesn't matter what `API_ALLOWLIST` does at all
    # because of this. Basically, it doesn't even get to the
    # `API_ALLOWLIST checking stuff.
    #
    # The assumption is that "unredacted = processed + sensitive stuff". So,
    # if you don't have `view_pii` you won't get anything here you don't
    # already get from `ProcessedCrash`. And if you have `view_pii`
    # there's no point writing down a allowlist.


class RawCrash(SocorroMiddleware):
    """
    To access any of the raw dumps (e.g. format=raw) you need an API
    token that carries the "View Raw Dumps" permission.
    """

    implementation = SimplifiedCrashData
    implementation_config_namespace = "crashdata"

    required_params = ("crash_id",)
    possible_params = ("format", "name")

    defaults = {"format": "meta"}

    aliases = {"crash_id": "uuid", "format": "datatype"}

    IS_PUBLIC = True

    HELP_TEXT = """
    API for retrieving the raw crash data. This includes the crash annotations and
    fields generated by the collector (format=meta) as well as minidumps (format=raw,
    name=NAME) and memory report (format=raw, name=memory_report).

    Requires protected data acess to view protected parts of the raw crash.

    Params:

    * crash_id: the crash id for the raw crash you're requesting

    * format: (optional) "meta" for the crash annotations or "raw" for the other
      files

    * name: (optional) the name of the file in the crash report you want to download

    Examples:

    * annotations: /api/RawCrash/?crash_id=XXX&format=meta
    * memory_report: /api/RawCrash/?crash_id=XXX&format=raw&name=memory_report
    * upload_file_minidump: /api/RawCrash/?crash_id=XXX&format=raw&name=upload_file_minidump

    """

    API_ALLOWLIST = (
        "Accessibility",
        "AdapterDeviceID",
        "AdapterDriverVersion",
        "AdapterRendererIDs",
        "AdapterSubsysID",
        "AdapterVendorID",
        "ApplicationBuildID",
        "additional_minidumps",
        "Add-ons",
        "Android_Board",
        "Android_Brand",
        "Android_CPU_ABI",
        "Android_CPU_ABI2",
        "Android_Device",
        "Android_Display",
        "Android_Fingerprint",
        "Android_Hardware",
        "Android_Manufacturer",
        "Android_Model",
        "Android_Version",
        "AsyncShutdownTimeout",
        "AvailablePageFile",
        "AvailablePhysicalMemory",
        "AvailableVirtualMemory",
        "B2G_OS_Version",
        "BIOS_Manufacturer",
        "bug836263-size",
        "buildid",
        "BuildID",
        "CrashTime",
        "DOMIPCEnabled",
        "EMCheckCompatibility",
        "FlashVersion",
        "id",
        "InstallTime",
        "IsGarbageCollecting",
        "MacAvailableMemorySysctl",
        "MacMemoryPressure",
        "MacMemoryPressureCriticalTime",
        "MacMemoryPressureNormalTime",
        "MacMemoryPressureSysctl",
        "MacMemoryPressureWarningTime",
        "Min_ARM_Version",
        "MinidumpSha256Hash",
        "Notes",
        "NumberOfProcessors",
        "OOMAllocationSize",
        "PluginFilename",
        "PluginName",
        "PluginUserComment",
        "PluginVersion",
        "ProcessType",
        "ProductID",
        "ProductName",
        "RecordReplay",
        "ReleaseChannel",
        "SecondsSinceLastCrash",
        "ShutdownProgress",
        "StartupTime",
        "submitted_timestamp",
        "SystemMemoryUsePercentage",
        "Theme",
        "TotalVirtualMemory",
        "upload_file_minidump_*",
        "useragent_locale",
        "uuid",
        "Vendor",
        "version",
        "Version",
        "WindowsErrorReporting",
        "Winsock_LSP",
        "XPCOMSpinEventLoopStack",
    )

    # The reason we use the old list and pass it into the more dynamic wrapper
    # for getting the complete list is because we're apparently way behind
    # on having all of these added to the Super Search Fields.
    API_ALLOWLIST = get_api_allowlist("raw_crash", baseline=API_ALLOWLIST)

    # If this is matched in the query string parameters, then
    # we will return the response in binary format in the API
    API_BINARY_RESPONSE = {"format": "raw"}
    # permissions needed to download it as a binary response
    API_BINARY_PERMISSIONS = ("crashstats.view_rawdump",)

    @classmethod
    def get_binary_filename(cls, params):
        name = params["name"]
        crash_id = params["crash_id"]

        if name == "memory_report":
            return "memory_report.json.gz"
        elif name:
            return f"{crash_id}-{name}.dmp"
        else:
            return f"{crash_id}.dmp"

    def get(self, **kwargs):
        format_ = kwargs.get("format", "meta")
        if format_ == "raw_crash":
            # legacy
            format_ = kwargs["format"] = "raw"
        expect_dict = format_ != "raw"
        result = super().get(**kwargs)
        # This 'result', will either be a binary blob or a python dict.
        # Unless kwargs['format']==raw, this has to be a python dict.
        if expect_dict and not isinstance(result, dict):
            raise BadArgumentError("format")
        return result


class Bugs(SocorroMiddleware):
    # NOTE(willkg): This is implemented with a Django model.
    required_params = (("signatures", list),)

    IS_PUBLIC = True

    HELP_TEXT = """
    API to retrieve Bugzilla bug ids for given signatures as well as bug ids for all the
    signatures covered by those bug ids.

    Params:

    * signatures: signatures to check

    Example searching for two signatures:

    /api/Bugs/?signatures=OOM | small&signatures=OOM | large

    Note: This works with both GET and passing signatures via the querystring of the url
    and also with POST and passing signatures in the HTTP request body.

    """

    API_ALLOWLIST = {"hits": ("id", "signature")}

    def get_bug_id_data(self, signatures):
        """
        :arg list-of-str signatures: list of signatures to check

        :returns: list of dict of "id" and "signature keys
        """
        hits = list(
            BugAssociation.objects.get_bugs_and_related_bugs(signatures=signatures)
            .values("bug_id", "signature")
            .order_by("bug_id", "signature")
        )

        return [
            {"id": int(hit["bug_id"]), "signature": hit["signature"]} for hit in hits
        ]

    def get(self, *args, **kwargs):
        params = self.parse_parameters(kwargs)

        hits = self.get_bug_id_data(params["signatures"])
        return {"hits": hits, "total": len(hits)}

    def post(self, **data):
        signatures = data["signatures"]
        if not isinstance(signatures, (list, tuple)):
            signatures = [signatures]

        hits = self.get_bug_id_data(signatures)
        return {"hits": hits, "total": len(hits)}


class SignaturesByBugs(SocorroMiddleware):
    # NOTE(willkg): This is implemented with a Django model.

    required_params = (("bug_ids", list),)

    IS_PUBLIC = True

    HELP_TEXT = """
    API for getting signatures associated with specified bug ids.

    Params:

    * bug_ids: list of bug ids

    Example with two bug ids:

    /api/SignatureByBugs/?bug_ids=XXX&bug_ids=YYY

    """

    API_ALLOWLIST = {"hits": ("id", "signature")}

    def get(self, *args, **kwargs):
        params = self.parse_parameters(kwargs)

        # Make sure bug_ids is a list of numbers and if not, raise
        # and error
        if not all([bug_id.isdigit() for bug_id in params["bug_ids"]]):
            raise BadArgumentError("bug_ids")

        hits = list(
            BugAssociation.objects.filter(bug_id__in=params["bug_ids"]).values(
                "bug_id", "signature"
            )
        )

        hits = [
            {"id": int(hit["bug_id"]), "signature": hit["signature"]} for hit in hits
        ]

        return {"hits": hits, "total": len(hits)}


class SignatureFirstDate(SocorroMiddleware):
    # NOTE(willkg): This is implemented with a Django model.

    # Set to a short cache time because, the only real user of this
    # model is the Top Crasher page and that one uses the highly
    # optimized method `.get_dates()` which internally uses caching
    # for each individual signature and does so with a very long
    # cache time.
    #
    # Making it non-0 is to prevent the stampeding herd on this endpoint
    # alone when exposed in the API.
    cache_seconds = 5 * 60  # 5 minutes only

    required_params = (("signatures", list),)

    IS_PUBLIC = True

    HELP_TEXT = """
    API for getting the first date and build id Socorro saw the specified signature.

    Params:

    * signatures: signatures to check

    Example searching for two signatures:

    /api/SignatureFirstDate/?signatures=OOM | small&signatures=OOM | large

    """

    API_ALLOWLIST = {"hits": ("signature", "first_date", "first_build")}

    def get(self, *args, **kwargs):
        params = self.parse_parameters(kwargs)

        hits = list(
            Signature.objects.filter(signature__in=params["signatures"]).values(
                "signature", "first_build", "first_date"
            )
        )

        hits = [
            {
                "signature": hit["signature"],
                "first_build": str(hit["first_build"]),
                "first_date": hit["first_date"].isoformat(),
            }
            for hit in hits
        ]

        return {"hits": hits, "total": len(hits)}


class VersionString(SocorroMiddleware):
    # NOTE(willkg): This is implemented with a Django model.

    # Set to a short cache time because it's just a db lookup. Making it non-0
    # is to prevent the stampeding herd on this endpoint alone when exposed in
    # the API.
    cache_seconds = 2 * 60  # 2 minutes only

    required_params = ("product", "channel", "build_id")

    IS_PUBLIC = True

    HELP_TEXT = """
    API used by Socorro processor for looking up beta and rc version strings
    for (product, channel, build_id) combination.

    Params:

    * product: the product to query

    * channel: the channel to query

    * build_id: the build id to query

    """

    API_ALLOWLIST = {"hits": ("version_string",)}

    def get(self, *args, **kwargs):
        params = self.parse_parameters(kwargs)

        versions = list(
            ProductVersion.objects.filter(
                product_name=params["product"],
                release_channel=params["channel"].lower(),
                build_id=params["build_id"],
            ).values_list("version_string", flat=True)
        )

        if versions:
            if params["channel"].lower() in ("aurora", "beta"):
                if "b" in versions[0]:
                    # If we're looking at betas which have a "b" in the
                    # versions, then ignore "rc" versions because they didn't
                    # get released
                    versions = [version for version in versions if "rc" not in version]

                else:
                    # If we're looking at non-betas, then only return "rc"
                    # versions because this crash report is in the beta channel
                    # and not the release channel
                    versions = [version for version in versions if "rc" in version]

        versions = [{"version_string": vers} for vers in versions]

        return {"hits": versions, "total": len(versions)}


class BugzillaBugInfo(SocorroCommon):
    # This is for how long we cache the metadata of each individual bug.
    BUG_CACHE_SECONDS = 60 * 60

    IS_PUBLIC = True

    @staticmethod
    def make_cache_key(bug_id):
        # This is the same cache key that we use in show_bug_link()
        # the jinja helper function.
        return f"buginfo:{bug_id}"

    def get(self, bugs):
        if isinstance(bugs, str):
            bugs = [bugs]
        fields = ("summary", "status", "id", "resolution")
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
            params = {"bugs": ",".join(missing), "fields": ",".join(fields)}
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            if settings.BZAPI_TOKEN:
                headers["X-BUGZILLA-API-KEY"] = settings.BZAPI_TOKEN
            url = settings.BZAPI_BASE_URL + (
                "/bug?id=%(bugs)s&include_fields=%(fields)s" % params
            )
            session = session_with_retries(
                total_retries=5,
                # 502 = Bad Gateway
                # 503 = Service Unavailable
                # 504 = Gateway Time-out
                status_forcelist=(500, 502, 503, 504),
            )
            response = session.get(url, headers=headers)
            if response.status_code != 200:
                raise BugzillaRestHTTPUnexpectedError(response.status_code)

            for each in response.json()["bugs"]:
                cache_key = self.make_cache_key(each["id"])
                cache.set(cache_key, each, self.BUG_CACHE_SECONDS)
                results.append(each)
        return {"bugs": results}


class Reprocessing(SocorroMiddleware):
    """Submit crash ids to reprocessing queue."""

    IS_PUBLIC = True

    HELP_TEXT = """
    API for submitting crash ids for reprocessing.

    Requires reprocess_crashes permission.

    Params:

    * crashids: crash ids for reprocessing

    Example for submitting two crash ids for reprocessing:

    /api/Reprocessing/?crash_ids=XXX&crash_ids=YYY

    Each crash id can also specify a processing pipeline ruleset to use by appending
    the crash id with a ":" and a ruleset name.

    Example for submitting a crash id using the "regenerate_signature" ruleset:

    /api/Reprocessing/?crashids=9b79af22-fcb4-4e85-bada-f3d230210421:regenerate_signature

    """

    implementation = import_string(settings.CRASHQUEUE)

    API_REQUIRED_PERMISSIONS = ("crashstats.reprocess_crashes",)

    API_ALLOWLIST = None

    required_params = (("crash_ids", list),)

    get = None

    def post(self, **data):
        crash_ids = data["crash_ids"]
        if not isinstance(crash_ids, (list, tuple)):
            crash_ids = [crash_ids]

        # If one of the crash ids or rulesets isn't valid, raise an HTTP 400.
        for crash_id in crash_ids:
            if ":" in crash_id:
                crash_id, ruleset_name = crash_id.split(":", 1)
            else:
                crash_id, ruleset_name = crash_id, "default"

            if not is_crash_id_valid(crash_id):
                raise BadArgumentError(f"Crash id {crash_id!r} is not valid.")

            if ruleset_name not in settings.VALID_RULESETS:
                raise BadArgumentError(f"Ruleset {ruleset_name!r} is not valid.")

        return self.get_implementation().publish(
            queue="reprocessing", crash_ids=crash_ids
        )


class PriorityJob(SocorroMiddleware):
    """Submit crash ids to priority queue."""

    implementation = import_string(settings.CRASHQUEUE)

    required_params = (("crash_ids", list),)

    get = None

    def post(self, **data):
        crash_ids = data["crash_ids"]
        if not isinstance(crash_ids, (list, tuple)):
            crash_ids = [crash_ids]
        return self.get_implementation().publish(queue="priority", crash_ids=crash_ids)


class NoOpMiddleware(SocorroMiddleware):
    """Does nothing--used for testing API infrastructure"""

    IS_PUBLIC = True

    HELP_TEXT = """
    API that does nothing except help us test our API infrastructure.
    """

    API_ALLOWLIST = ("hits", "total")

    required_params = ("product",)

    def get(self, **kwargs):
        params = self.parse_parameters(kwargs)

        if params["product"] == "bad":
            raise BadArgumentError("Bad product")

        return {"hits": [], "total": 0}

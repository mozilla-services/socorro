# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import suppress
from dataclasses import dataclass
import datetime
import gzip
import json
import re
from typing import Any
from urllib.parse import unquote_plus, urlsplit
from zlib import error as ZlibError

from glom import glom
import jsonschema
import sentry_sdk

from socorro.libmarkus import METRICS
from socorro.lib import libsocorrodataschema
from socorro.lib.libdatetime import date_to_string, isoformat_to_time
from socorro.lib.libcache import ExpiringCache
from socorro.lib.libdatetime import UTC
from socorro.lib.libjsonschema import InvalidSchemaError, resolve_references
from socorro.lib.librequests import session_with_retries
from socorro.lib.libsocorrodataschema import SocorroDataReducer, validate_instance
from socorro.processor.rules.base import Rule
from socorro.signature.generator import SignatureGenerator
from socorro.signature.utils import convert_to_crash_data


# NOTE(willkg): This is the sys.maxint value for Python in the docker container
# we run it in. Python 3 doesn't have a maxint, so when we switch to Python 3
# I'm not sure what we should replace this with.
MAXINT = 9223372036854775807


@dataclass
class CopyItem:
    # Type to validate and normalize the annotation value to
    type_: str

    # The source annotation in the raw crash
    annotation: str

    # The destination key in the processed crash
    key: str

    # The default value to use if the annotation doesn't exist
    default: Any


class NoDefault:
    def __repr__(self):
        return "no-default"


NO_DEFAULT = NoDefault()


class CopyFromRawCrashRule(Rule):
    """Copy data from raw crash to processed crash with correct name.

    This copies and normalizes crash annotations from the raw crash.

    """

    def __init__(self, schema):
        super().__init__()
        schema = resolve_references(schema)
        self.schema = schema
        self.fields = self.build_fields(schema)

        self._reducer_cache = {}

    def build_fields(self, schema):
        fields = []

        if schema.get("type", "string") != "object":
            raise InvalidSchemaError("schema type is not object")

        # NOTE(willkg): all items copied from the raw crash will get put at the top
        # level of the processed crash and are not "$ref"
        properties = schema.get("properties", {})
        for key, schema_property in properties.items():
            copy_source = schema_property.get("source_annotation", "")
            if copy_source:
                default = schema_property.get("default", NO_DEFAULT)

                # Use the first non-null type
                valid_types = schema_property["type"]
                if isinstance(valid_types, list):
                    # Take the first non-null type
                    type_ = [t for t in valid_types if t != "null"][0]
                else:
                    type_ = valid_types

                fields.append(
                    CopyItem(
                        type_=type_,
                        annotation=copy_source,
                        key=key,
                        default=default,
                    )
                )
        return fields

    def get_reducer(self, schema_key):
        """Return the SocorroDataReducer for this subschema

        NOTE(willkg): results are cached on the CopyFromRawCrashRule instance.

        :arg schema_key: the property key in the processed crash schema to return the
            value of

        :returns: schema

        """
        cache_key = schema_key
        reducer = self._reducer_cache.get(cache_key)
        if reducer is None:
            reducer = SocorroDataReducer(self.schema["properties"][schema_key])
            self._reducer_cache[cache_key] = reducer
        return reducer

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        for copy_item in self.fields:
            annotation = copy_item.annotation
            if annotation not in raw_crash:
                # If the annotation is not the raw crash, but there is a default value
                # specified, add that
                if copy_item.default is not NO_DEFAULT:
                    processed_crash[copy_item.key] = copy_item.default
                continue

            value = raw_crash[annotation]

            if copy_item.type_ == "boolean":
                value = str(value).lower()
                if value in ("1", "true"):
                    processed_crash[copy_item.key] = True
                elif value in ("0", "false"):
                    processed_crash[copy_item.key] = False
                else:
                    status.add_note(f"{annotation} has non-boolean value {value}")

            elif copy_item.type_ == "integer":
                try:
                    processed_crash[copy_item.key] = int(value)
                except ValueError:
                    status.add_note(f"{annotation} has a non-int value")

            elif copy_item.type_ == "number":
                # NOTE(willkg): in jsonschema, "number" is a float
                try:
                    processed_crash[copy_item.key] = float(value)
                except ValueError:
                    status.add_note(f"{annotation} has a non-float value")

            elif copy_item.type_ == "string":
                processed_crash[copy_item.key] = value

            elif copy_item.type_ == "object":
                # If it's a string, then assume it's json-encoded and decode it
                if isinstance(value, str):
                    try:
                        json_value = json.loads(value)
                    except json.JSONDecodeError:
                        status.add_note(f"{annotation} value is malformed json")
                        continue

                # Validate it against the schema at the specified copy_item.key of the
                # processed crash schema
                try:
                    reducer = self.get_reducer(copy_item.key)
                    reducer.traverse(json_value)
                    processed_crash[copy_item.key] = json_value
                except libsocorrodataschema.InvalidDocumentError:
                    status.add_note(f"{annotation} value is malformed {copy_item.key}")


class AccessibilityRule(Rule):
    """Add accessibility data to processed crash

    The Accessibility annotation is set to "Active" by the accessibility service when it
    is active and doesn't appear in the crash report when it is not.

    This converts that state of affairs to a True if the field exists and is "Active",
    and False if not.

    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        value = raw_crash.get("Accessibility", "")
        processed_crash["accessibility"] = value == "Active"


class ConvertModuleSignatureInfoRule(Rule):
    """Make ModuleSignatureInfo to a string.

    For a while, crash reports with annotations submitted as a JSON blob had
    ModuleSignatureInfo appended to the end of them as an object. This JSON-encodes that
    object so that the value is always a JSON-encoded string.

    Note: This value is used by the stackwalker. At some point, the stackwalker will
    pull this information from the minidump and we can stop doing this conversion.

    Bug #1607806

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return not isinstance(raw_crash.get("ModuleSignatureInfo", ""), str)

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        info = raw_crash["ModuleSignatureInfo"]
        raw_crash["ModuleSignatureInfo"] = json.dumps(info)


class SubmittedFromRule(Rule):
    """Determine submitted_from and submitted_from_infobar field values

    This looks at the SubmittedFrom and SubmittedFromInfobar annotations and fills
    in the appropriate processed crash fields.

    This handles the case where SubmittedFromInfobar had the value true when the
    annotations were submitted as a JSON blob. Bug #1626048

    NOTE: After August 2022, we can stop populating submitted_from_infobar field.

    """

    TRUE_VALUES = ("1", "true", True)

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        if "SubmittedFromInfobar" in raw_crash:
            submitted_from_infobar = (
                raw_crash["SubmittedFromInfobar"] in self.TRUE_VALUES
            )
            submitted_from = "Infobar" if submitted_from_infobar else "Unknown"

        else:
            submitted_from = raw_crash.get("SubmittedFrom", "Unknown")
            submitted_from_infobar = submitted_from == "Infobar"

        processed_crash["submitted_from"] = submitted_from
        processed_crash["submitted_from_infobar"] = submitted_from_infobar


class SubmittedFromInfobarFixRule(Rule):
    """Fix SubmittedFromInfobar annotation values to "1" """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return "SubmittedFromInfobar" in raw_crash and raw_crash[
            "SubmittedFromInfobar"
        ] in ("true", True)

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        raw_crash["SubmittedFromInfobar"] = "1"


class MajorVersionRule(Rule):
    """Sets "version" to the major version number of the Version annotation or 0"""

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        major_version = None
        with suppress(ValueError, IndexError):
            version = raw_crash.get("Version", "")
            major_version = int(version.split(".")[0])

        major_version = major_version if major_version is not None else 0
        processed_crash["major_version"] = major_version


class PluginRule(Rule):
    """Handle plugin-related fields."""

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        process_type = raw_crash.get("ProcessType", "parent")
        if process_type == "plugin":
            processed_crash["plugin_filename"] = raw_crash.get("PluginFilename", "")
            processed_crash["plugin_name"] = raw_crash.get("PluginName", "")
            processed_crash["plugin_version"] = raw_crash.get("PluginVersion", "")


class AddonsRule(Rule):
    def _get_formatted_addon(self, addon):
        """Return a properly formatted addon string.

        Format is: addon_identifier:addon_version

        This is used because some addons are missing a version. In order to
        simplify subsequent queries, we make sure the format is consistent.

        """
        return addon if ":" in addon else addon + ":NO_VERSION"

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        processed_crash["addons_checked"] = None

        # it's okay to not have EMCheckCompatibility
        if "EMCheckCompatibility" in raw_crash:
            addons_checked_txt = raw_crash["EMCheckCompatibility"].lower()
            processed_crash["addons_checked"] = False
            if addons_checked_txt == "true":
                processed_crash["addons_checked"] = True

        original_addon_str = raw_crash.get("Add-ons", "")
        if not original_addon_str:
            processed_crash["addons"] = []
        else:
            processed_crash["addons"] = [
                unquote_plus(self._get_formatted_addon(x))
                for x in original_addon_str.split(",")
            ]


class DatesAndTimesRule(Rule):
    @staticmethod
    def _get_truncate_or_warn(a_mapping, key, status, default=None, max_length=10000):
        try:
            return a_mapping[key][:max_length]
        except (KeyError, AttributeError):
            status.add_note("WARNING: raw_crash missing %s" % key)
            return default
        except TypeError as x:
            status.add_note(
                "WARNING: raw_crash[%s] contains unexpected value: %s; %s"
                % (key, a_mapping[key], str(x))
            )
            return default

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # NOTE(willkg): The submitted_timestamp comes from the collector when the crash
        # report is accepted. It should always be there and should always be
        # an isoformat string.
        submitted_timestamp_str = raw_crash["submitted_timestamp"]
        processed_crash["submitted_timestamp"] = submitted_timestamp_str

        # NOTE(willkg): This means that the date_processed is the same as
        # submitted_timestamp which is the datetime when the crash report was collected
        processed_crash["date_processed"] = submitted_timestamp_str

        # We want the seconds since epoch as an int--not a float
        submitted_timestamp_epoch = int(isoformat_to_time(submitted_timestamp_str))
        try:
            crash_time = int(
                self._get_truncate_or_warn(
                    raw_crash,
                    "CrashTime",
                    status,
                    submitted_timestamp_epoch,
                    10,
                )
            )
        except ValueError:
            crash_time = 0
            status.add_note('non-integer value of "CrashTime"')

        processed_crash["crash_time"] = crash_time
        if crash_time == submitted_timestamp_epoch:
            status.add_note("client_crash_date is unknown")

        # startup_time: must have started up some time before crash
        startup_time = int(processed_crash.get("startup_time", crash_time))

        # InstallTime: must have installed some time before startup
        try:
            install_time = int(raw_crash.get("InstallTime", startup_time))
        except ValueError:
            install_time = 0
            status.add_note('non-integer value of "InstallTime"')

        client_crash_date = datetime.datetime.fromtimestamp(crash_time, UTC)
        processed_crash["client_crash_date"] = date_to_string(client_crash_date)

        processed_crash["install_age"] = crash_time - install_time
        processed_crash["uptime"] = max(0, crash_time - startup_time)
        try:
            last_crash = int(raw_crash["SecondsSinceLastCrash"])
        except KeyError:
            last_crash = None
        except (TypeError, ValueError):
            last_crash = None
            status.add_note('non-integer value of "SecondsSinceLastCrash"')
        if last_crash and last_crash > MAXINT:
            last_crash = None
            status.add_note('"SecondsSinceLastCrash" larger than MAXINT - set to NULL')
        processed_crash["last_crash"] = last_crash


class BreadcrumbsRule(Rule):
    """Validate and copy over Breadcrumbs data."""

    def __init__(self, schema):
        super().__init__()
        self.schema = schema

        # NOTE(willkg): if the "breadcrumbs" section ever gets moved in the processed
        # crash schema, we'll need to update this
        self.breadcrumbs_schema = schema["properties"]["breadcrumbs"]

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return bool(raw_crash.get("Breadcrumbs", None))

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        breadcrumbs = raw_crash["Breadcrumbs"]

        try:
            breadcrumbs_data = json.loads(breadcrumbs)

            # NOTE(willkg): Sentry specifies breadcrumbs with an intermediary "values"
            # dict. This check lets us handle how android-components crash reporter is
            # sending breadcrumbs as well as what a Sentry client would send.
            if isinstance(breadcrumbs_data, dict) and "values" in breadcrumbs_data:
                breadcrumbs_data = breadcrumbs_data["values"]

            validate_instance(breadcrumbs_data, self.breadcrumbs_schema)
            processed_crash["breadcrumbs"] = breadcrumbs_data
        except json.JSONDecodeError:
            status.add_note("Breadcrumbs: malformed: not valid json")
        except jsonschema.exceptions.ValidationError as jexc:
            status.add_note(f"Breadcrumbs: malformed: {jexc.message}")


class MacBootArgsRule(Rule):
    """Extracts mac_boot_args from json_dump

    If there's a mac_boot_args in the json_dump and it's not an empty value, this
    copies it to the processed_crash.

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return bool(glom(processed_crash, "json_dump.mac_boot_args", default=None))

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        value = processed_crash["json_dump"]["mac_boot_args"]

        if not isinstance(value, str):
            status.add_note(
                f"MacBootArgsRule: mac_boot_args is {type(value).__qualname__} and not str"
            )
            return

        # Ignore empty values
        value = value.strip()
        if value:
            processed_crash["mac_boot_args"] = value
            processed_crash["has_mac_boot_args"] = True


class MacCrashInfoRule(Rule):
    """Extracts mac_crash_info from json_dump

    If there's a mac_crash_info in the json_dump and there are valid records, this
    extracts it and keeps it around as a JSON-encoded string.

    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        if "mac_crash_info" in processed_crash:
            del processed_crash["mac_crash_info"]

        mac_crash_info = glom(processed_crash, "json_dump.mac_crash_info", default={})

        if mac_crash_info and mac_crash_info.get("num_records", 0) > 0:
            # NOTE(willkg): use sort_keys=True so this is stable and doesn't change
            # between iterations
            processed_crash["mac_crash_info"] = json.dumps(
                mac_crash_info, sort_keys=True
            )


class MozCrashReasonRule(Rule):
    """This rule sanitizes the MozCrashReason value

    MozCrashReason values should be constants defined in the code, but currently
    some reasons can come from Rust error messages which are dynamic and related
    to the specifics of whatever triggered the crash which includes url parsing.

    This rule generates raw and sanitized values of MozCrashReason.

    """

    # NOTE(willkg): We're going with a "disallow" list because it seems like
    # there's a very limited set of problematic prefixes. If that changes,
    # we should switch to only allowing values that start with "MOZ" since
    # those are constants.
    DISALLOWED_PREFIXES = (
        "Failed to load module",
        "byte index",
        "do not use eval with system privileges",
    )

    def sanitize_reason(self, reason):
        if reason.startswith(self.DISALLOWED_PREFIXES):
            return "sanitized--see moz_crash_reason_raw"
        return reason

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return bool(raw_crash.get("MozCrashReason", None))

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        crash_reason = raw_crash["MozCrashReason"]

        # This can contain PII in the exception message
        processed_crash["moz_crash_reason_raw"] = crash_reason
        processed_crash["moz_crash_reason"] = self.sanitize_reason(crash_reason)


class OutOfMemoryBinaryRule(Rule):
    # Number of bytes, max, that we accept memory_report value as JSON.
    MAX_SIZE_UNCOMPRESSED = 20 * 1024 * 1024  # ~20Mb

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return "memory_report" in dumps

    def _extract_memory_info(self, dump_pathname, status):
        """Extract and return the JSON data from the .json.gz memory report"""

        def error_out(error_message):
            status.add_note(error_message)
            return {"ERROR": error_message}

        try:
            fd = gzip.open(dump_pathname, "rb")
        except OSError as x:
            error_message = "error in gzip for %s: %r" % (dump_pathname, x)
            return error_out(error_message)

        try:
            memory_info_as_string = fd.read()
            if len(memory_info_as_string) > self.MAX_SIZE_UNCOMPRESSED:
                error_message = "Uncompressed memory info too large %d (max: %d)" % (
                    len(memory_info_as_string),
                    self.MAX_SIZE_UNCOMPRESSED,
                )
                return error_out(error_message)

            memory_info = json.loads(memory_info_as_string)
        except (EOFError, OSError, ZlibError) as x:
            error_message = "error in gzip for %s: %r" % (dump_pathname, x)
            return error_out(error_message)
        except ValueError as x:
            error_message = "error in json for %s: %r" % (dump_pathname, x)
            return error_out(error_message)
        finally:
            fd.close()

        return memory_info

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        pathname = dumps["memory_report"]
        memory_report = self._extract_memory_info(dump_pathname=pathname, status=status)

        if isinstance(memory_report, dict) and memory_report.get("ERROR"):
            processed_crash["memory_report_error"] = memory_report["ERROR"]
        else:
            processed_crash["memory_report"] = memory_report


class FenixVersionRewriteRule(Rule):
    """Fix 'Nightly YYMMDD HH:MM' version values to '0.0a1'

    This allows nightlies for Fenix to group in Crash Stats. We can probably ditch this
    at some point when we're not getting crash reports that have this version structure.

    Bug #1624911

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        is_nightly = (raw_crash.get("Version") or "").startswith("Nightly ")
        return raw_crash.get("ProductName") == "Fenix" and is_nightly

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        status.add_note("Changed version from %r to 0.0a1" % raw_crash.get("Version"))
        raw_crash["Version"] = "0.0a1"


class ESRVersionRewrite(Rule):
    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return raw_crash.get("ReleaseChannel", "") == "esr"

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        try:
            raw_crash["Version"] += "esr"
        except KeyError:
            status.add_note('"Version" missing from esr release raw_crash')


class TopMostFilesRule(Rule):
    """Determines the top-most filename in the stack

    This takes into account stack frames and inline function data for Rust/C++ stacks to
    determine the filename of the top-most thing in the stack.

    If there is no stack, then this omits the field.

    While the field name is "topmost_filenames" (plural), this only determines the
    top-most filename (singular) because of historical reasons.

    Bug #519703.
    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        try:
            crashing_thread = processed_crash["crashing_thread"]
            frames = processed_crash["json_dump"]["threads"][crashing_thread]["frames"]
        except (IndexError, TypeError, KeyError):
            return

        source_filename = ""

        for frame in frames:
            inlines = frame.get("inlines") or []
            for inline in inlines:
                source_filename = inline.get("file")
                if source_filename:
                    processed_crash["topmost_filenames"] = source_filename
                    return

            source_filename = frame.get("file")
            if source_filename:
                processed_crash["topmost_filenames"] = source_filename
                return


class MissingSymbolsRule(Rule):
    """
    Adds ``missing_symbols`` field where the value is a semi-colon separated set of
    module information strings for modules where the stackwalker couldn't find a symbols
    file. Module information strings have one of two forms depending on whether there's
    a codeid value in the module data or not:

    * ``module/version/debugid``
    * ``module/version/debugid/codeid``

    """

    # Filenames should contain A-Za-z0-9_.- and that's it.
    BAD_FILENAME_CHARACTERS = re.compile(r"[^a-zA-Z0-9_\.-]", re.IGNORECASE)

    # Debug ids and code ids are hex strings
    BAD_HEXID_CHARACTERS = re.compile(r"[^a-f0-9]", re.IGNORECASE)

    NULL_DEBUG_ID = "0" * 33

    def format_module(self, item):
        filename = item["filename"]
        filename = self.BAD_FILENAME_CHARACTERS.sub("", filename)

        version = item.get("version", "") or "None"
        version = version.replace("/", "\\/")

        debugid = item.get("debug_id", self.NULL_DEBUG_ID)
        debugid = self.BAD_HEXID_CHARACTERS.sub("", debugid)

        codeid = item.get("code_id", None)
        if codeid:
            codeid = self.BAD_HEXID_CHARACTERS.sub("", codeid)

        if codeid:
            return f"{filename}/{version}/{debugid}/{codeid}"
        else:
            return f"{filename}/{version}/{debugid}"

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return bool(glom(processed_crash, "json_dump.modules", default=[]))

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        modules = processed_crash["json_dump"]["modules"]

        missing_symbols = [
            self.format_module(module)
            for module in modules
            if module.get("filename") and module.get("missing_symbols") is True
        ]
        if missing_symbols:
            missing_symbols.sort()
            processed_crash["missing_symbols"] = ";".join(missing_symbols)


class ModulesInStackRule(Rule):
    """
    Adds ``modules_in_stack`` field where the value is a semi-colon separated set of
    ``module/debugid`` strings for all the modules that show up in the stack of the
    crashing thread.
    """

    # Filenames should contain A-Za-z0-9_.- and that's it.
    BAD_FILENAME_CHARACTERS = re.compile(r"[^a-zA-Z0-9_\.-]", re.IGNORECASE)

    # Debug ids are hex strings
    BAD_DEBUGID_CHARACTERS = re.compile(r"[^a-f0-9]", re.IGNORECASE)

    def format_module(self, item):
        filename = item.get("filename", "")
        filename = self.BAD_FILENAME_CHARACTERS.sub("", filename)

        debugid = item.get("debug_id", "")
        debugid = self.BAD_DEBUGID_CHARACTERS.sub("", debugid)

        return f"{filename}/{debugid}"

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return "json_dump" in processed_crash

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        json_dump = processed_crash["json_dump"]
        crashing_thread = processed_crash["crashing_thread"]

        # If there is no crashing thread, then there's nothing to do.
        if crashing_thread is None:
            return

        try:
            stack = json_dump["threads"][crashing_thread]["frames"]
        except (KeyError, IndexError):
            # If those things aren't in the raw crash, then this rule doesn't
            # have anything to do.
            return

        module_to_module_info = {
            item["filename"]: self.format_module(item)
            for item in json_dump.get("modules", [])
            if "filename" in item
        }

        modules_in_stack = {
            module_to_module_info.get(frame.get("module")) for frame in stack
        }
        modules_in_stack = sorted(module for module in modules_in_stack if module)
        if modules_in_stack:
            processed_crash["modules_in_stack"] = ";".join(modules_in_stack)


class BetaVersionRule(Rule):
    # Hold at most this many items in cache; items are a key and a value
    # both of which are short strings, so this doesn't take much memory
    CACHE_MAX_SIZE = 5000

    # Items in cache expire after 30 minutes by default
    SHORT_CACHE_TTL = 60 * 30

    # If we know it's good, cache it for 24 hours because it won't change
    LONG_CACHE_TTL = 60 * 60 * 24

    # List of products to do lookups for--case-sensitive and must match ProductName from
    # the crash report annotations
    SUPPORTED_PRODUCTS = ["Firefox", "Thunderbird"]

    def __init__(self, version_string_api):
        super().__init__()
        self.cache = ExpiringCache(
            max_size=self.CACHE_MAX_SIZE, default_ttl=self.SHORT_CACHE_TTL
        )

        # For looking up version strings
        self.version_string_api = version_string_api
        self.session = session_with_retries()

    def __repr__(self):
        return self.generate_repr(keys=["version_string_api"])

    def _get_real_version(self, product, channel, build_id):
        """Return real version number from crashstats_productversion table

        :arg str product: the product
        :arg str channel: the release channel
        :arg int build_id: the build id as a string

        :returns: ``None`` or the version string that should be used

        """
        # NOTE(willkg): "DevEdition" on archive.mozilla.org matches the mystical
        # eldritch Firefox aurora channel, so we do this check-and-switch to have the
        # right "product name" for the lookup
        if (product, channel) == ("Firefox", "aurora") and build_id > "20170601":
            product = "DevEdition"

        key = "%s:%s:%s" % (product, channel, build_id)
        if key in self.cache:
            METRICS.incr("processor.betaversionrule.cache", tags=["result:hit"])
            return self.cache[key]

        METRICS.incr("processor.betaversionrule.cache", tags=["result:miss"])

        resp = self.session.get(
            self.version_string_api,
            params={"product": product, "channel": channel, "build_id": build_id},
        )

        if resp.status_code != 200:
            versions = []
        else:
            versions = resp.json()["hits"]

        if not versions:
            # We didn't get an answer which could mean that this is a weird build and
            # there is no answer or it could mean that Socorro doesn't know, yet. Maybe
            # in the future we get a better answer so we use the short ttl.
            METRICS.incr("processor.betaversionrule.lookup", tags=["result:fail"])
            self.cache.set(key, value=None, ttl=self.SHORT_CACHE_TTL)
            return None

        # If we got an answer we should keep it around for a while because it's
        # a real answer and it's not going to change so use the long ttl plus
        # a fudge factor.
        real_version = versions[0]["version_string"]
        METRICS.incr("processor.betaversionrule.lookup", tags=["result:success"])
        self.cache.set(key, value=real_version, ttl=self.LONG_CACHE_TTL)
        return real_version

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # Beta and aurora versions send the wrong version in the crash report for
        # certain products
        product = processed_crash.get("product", "")
        release_channel = processed_crash.get("release_channel", "").lower()
        return product in self.SUPPORTED_PRODUCTS and release_channel in (
            "beta",
            "aurora",
        )

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        product = processed_crash["product"]
        build_id = processed_crash.get("build", "").strip()
        release_channel = processed_crash["release_channel"].lower()

        # Only run if we've got all the things we need
        if product and build_id and release_channel:
            # Convert the build_id to a str for lookups
            build_id = str(build_id)

            real_version = self._get_real_version(
                product=product, channel=release_channel, build_id=build_id
            )
            if real_version:
                processed_crash["version"] = real_version
                return

            self.logger.debug("betaversionrule: using %r", self.version_string_api)
            self.logger.info(
                "betaversionrule: failed lookup %r %r %r %r",
                processed_crash.get("uuid"),
                product,
                release_channel,
                build_id,
            )

        # No real version, but this is an aurora or beta crash report, so we
        # tack on "b0" to make it match the channel
        processed_crash["version"] += "b0"
        status.add_note(
            'release channel is %s but no version data was found - added "b0" '
            "suffix to version number" % release_channel
        )


class OSPrettyVersionRule(Rule):
    """Sets os_pretty_version with most readable operating system version string.

    This rule attempts to extract the most useful, singular, human understandable field
    for operating system version.

    * os_pretty_version

    For Windows, this is a lookup against a map.

    For Mac OSX, this pulls from os_name and os_version.

    For Linux, this uses json_dump.lsb_release.description if it's available.

    Must be run after OSInfoRule.

    """

    MAJOR_MINOR_RE = re.compile(r"^(\d+)\.(\d+)")

    WINDOWS_VERSIONS = {
        "3.5": "Windows NT",
        "4.0": "Windows NT",
        "4.1": "Windows 98",
        "4.9": "Windows Me",
        "5.0": "Windows 2000",
        "5.1": "Windows XP",
        "5.2": "Windows Server 2003",
        "6.0": "Windows Vista",
        "6.1": "Windows 7",
        "6.2": "Windows 8",
        "6.3": "Windows 8.1",
        "10.0": "Windows 10",
        # NOTE(willkg): Windows 11 is 10.0.21996 and higher, so it's not in this map
    }

    def parse_version(self, os_version):
        if not os_version or not isinstance(os_version, str):
            return None

        match = self.MAJOR_MINOR_RE.match(os_version)
        if match is None:
            # The version number is missing or invalid, there's nothing more to do
            return None

        major_version = int(match.group(1))
        minor_version = int(match.group(2))

        return (major_version, minor_version)

    def compute_windows_pretty_version(self, os_name, os_version, processed_crash):
        result = self.parse_version(os_version)
        if result is None:
            return os_name

        major_version, minor_version = result

        if (major_version, minor_version) == (10, 0) and os_version >= "10.0.21996":
            pretty_version = "Windows 11"

        else:
            windows_version = f"{major_version}.{minor_version}"
            pretty_version = self.WINDOWS_VERSIONS.get(
                windows_version, "Windows Unknown"
            )

        return pretty_version

    def compute_macos_pretty_version(self, os_name, os_version, processed_crash):
        result = self.parse_version(os_version)
        if result is None:
            return os_name

        major_version, minor_version = result

        # https://en.wikipedia.org/wiki/MacOS#Release_history
        if major_version >= 11:
            # NOTE(willkg): this assumes Apple versions macOS with just the major
            # version going forward.
            pretty_version = "macOS %s" % major_version
        elif major_version >= 10 and minor_version >= 0:
            pretty_version = "OS X %s.%s" % (major_version, minor_version)
        else:
            pretty_version = "OS X Unknown"

        return pretty_version

    def compute_linux_pretty_version(self, processed_crash):
        pretty_version = glom(
            processed_crash, "json_dump.lsb_release.description", default=""
        )
        pretty_version = pretty_version or "Linux"
        return pretty_version

    def compute_android_pretty_version(self, os_name, os_version):
        if os_version:
            return f"{os_name} {os_version}"
        return os_name

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # we will overwrite this field with the current best option
        # in stages, as we divine a better name
        processed_crash["os_pretty_version"] = None

        os_name = processed_crash.get("os_name")
        os_version = processed_crash.get("os_version")

        if os_name and os_name.startswith("Windows"):
            pretty_version = self.compute_windows_pretty_version(
                os_name, os_version, processed_crash
            )

        elif os_name == "Mac OS X":
            pretty_version = self.compute_macos_pretty_version(
                os_name, os_version, processed_crash
            )

        elif os_name == "Linux":
            pretty_version = self.compute_linux_pretty_version(processed_crash)

        elif os_name == "Android":
            pretty_version = self.compute_android_pretty_version(os_name, os_version)

        else:
            pretty_version = os_name

        processed_crash["os_pretty_version"] = pretty_version


class ThemePrettyNameRule(Rule):
    """The Firefox theme shows up commonly in crash reports referenced by its
    internal ID. The ID is not easy to change, and is referenced by id in other
    software.

    This rule attempts to modify it to have a more identifiable name, like
    other built-in extensions.

    Must be run after the Addons Rule.

    """

    def __init__(self):
        super().__init__()
        self.conversions = {
            "{972ce4c6-7e08-4474-a285-3208198ce6fd}": (
                "{972ce4c6-7e08-4474-a285-3208198ce6fd} (default theme)"
            )
        }

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        """addons is expected to be a list of strings like 'extension:version',
        but we are being overly cautious and consider the case where they
        lack the ':version' part, because user inputs are never reliable.
        """
        addons = processed_crash.get("addons", [])

        for addon in addons:
            extension = addon.split(":")[0]
            if extension in self.conversions:
                return True
        return False

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        addons = processed_crash["addons"]

        for index, addon in enumerate(addons):
            if ":" in addon:
                extension, version = addon.split(":", 1)
                if extension in self.conversions:
                    addons[index] = ":".join((self.conversions[extension], version))
            elif addon in self.conversions:
                addons[index] = self.conversions[addon]


class SignatureGeneratorRule(Rule):
    """Generates a Socorro crash signature."""

    def __init__(self):
        super().__init__()
        self.generator = SignatureGenerator(error_handler=self._error_handler)

    def _error_handler(self, crash_data, exc_info, extra):
        """Captures errors from signature generation"""
        with sentry_sdk.push_scope() as scope:
            scope.set_extra("signature_rule", extra["rule"])
            sentry_sdk.capture_exception(exc_info)

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # Generate a crash signature and capture the signature and notes
        crash_data = convert_to_crash_data(processed_crash)
        result = self.generator.generate(crash_data)
        processed_crash["signature"] = result.signature
        status.add_notes(result.notes)
        if "proto_signature" in result.extra:
            processed_crash["proto_signature"] = result.extra["proto_signature"]
        processed_crash["signature_debug"] = "\n".join(result.debug_log)


class PHCRule(Rule):
    """Performs PHC-related annotation processing.

    PHC stands for probabilistic heap checker. It adds a set of annotations
    that need to be adjusted so as to be searchable and usable in Crash Stats.

    Bug #1523278.

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return "PHCKind" in raw_crash

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # Add PHCKind which is a string
        processed_crash["phc_kind"] = raw_crash["PHCKind"]

        # Convert PHCBaseAddress from decimal to hex and add to processed crash
        if "PHCBaseAddress" in raw_crash:
            with suppress(ValueError):
                phc_base_address = hex(int(raw_crash["PHCBaseAddress"]))
                processed_crash["phc_base_address"] = phc_base_address

        # Add PHCUsableSize which is an integer
        if "PHCUsableSize" in raw_crash:
            with suppress(ValueError):
                processed_crash["phc_usable_size"] = int(raw_crash["PHCUsableSize"])

        # FIXME(willkg): We should symbolicate PHCAllocStack and PHCFreeStack and
        # put the symbolicated stacks in a new field.
        # See bug #1523278.

        # Add PHCAllocStack which is a comma-separated list of integers
        if "PHCAllocStack" in raw_crash:
            processed_crash["phc_alloc_stack"] = raw_crash["PHCAllocStack"]

        # Add PHCFreeStack which is a comma-separated list of integers
        if "PHCFreeStack" in raw_crash:
            processed_crash["phc_free_stack"] = raw_crash["PHCFreeStack"]


class ModuleURLRewriteRule(Rule):
    """Rewrites module urls using symbols.mozilla.org redirector

    The rust-minidump minidump-stackwalk caches SYM files on disk and adds an "INFO URL"
    line to the end with the source url. This fixes that url up by:

    1. nixing the url altogether if it's for localhost
    2. removing querystring parameters if it's for symbols.mozilla.org

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return bool(glom(processed_crash, "json_dump.modules", default=None))

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        modules = processed_crash["json_dump"]["modules"]
        for module in modules:
            if not module.get("symbol_url"):
                continue

            url = module["symbol_url"]
            parsed = urlsplit(url)

            if "localhost" in parsed.netloc:
                # If this is a localhost url, then remove it.
                module["symbol_url"] = None
                name = module.get("filename", module.get("debug_file", "unknown"))
                status.add_note(f"Redacting symbol url for module {name}")
                continue

            if "symbols.mozilla.org" in parsed.netloc:
                # If this is a symbols.mozilla.org url, remove the querystring.
                parsed = parsed._replace(query="")
                module["symbol_url"] = parsed.geturl()


class DistributionIdRule(Rule):
    """Distribution ID for the product.

    If this is a crash annotation, use that. Otherwise, extracts the distributionId from
    the Telemetry environment

    The distributorid indicates which vendor built the product. This helps to know
    in cases where we might be missing symbols or build context is different.

    Bug #1732414, #1747846

    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        distribution_id = None

        if "DistributionID" in raw_crash:
            distribution_id = raw_crash["DistributionID"]

        if not distribution_id:
            try:
                telemetry = json.loads(raw_crash.get("TelemetryEnvironment", "{}"))
            except json.JSONDecodeError:
                telemetry = {}

            distribution_id = glom(
                telemetry, "partner.distributionId", default="unknown"
            )

        # Values for distribution_id:
        #
        # * not there -> "unknown"
        # * null or "" -> "mozilla" (falsey)
        # * value of DistributionID annotation or the distributionId field
        if not distribution_id:
            distribution_id = "mozilla"

        processed_crash["distribution_id"] = distribution_id


class UtilityActorsNameRule(Rule):
    """Parses the UtilityActorsName annotation value.

    The value is a comma-separated list of actors names. This splits it into a list of
    strings.

    Bug #1788681

    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        utility_actors_name = raw_crash.get("UtilityActorsName")
        if utility_actors_name is None:
            return

        names = [
            item.strip() for item in utility_actors_name.split(",") if item.strip()
        ]
        processed_crash["utility_actors_name"] = names


class ReportTypeRule(Rule):
    """Determines the category for the report.

    We get crash reports for different sorts of things. Some are from crashes. Others
    are from browser hangs, content process hangs, shutdown hangs, etc. This determines
    the type of the report and fills in the ``report_type`` field.

    Bug #1667997

    """

    def identify_report_type(self, processed_crash, status):
        # NOTE(willkg): This comes from the ipc_channel_error crash annotation
        if "ipc_channel_error" in processed_crash:
            return "hang"

        # NOTE(willkg): This comes from the AsyncShutdownTimeout crash annotation
        if "async_shutdown_timeout" in processed_crash:
            return "hang"

        # If this is a C++/Rust crash and there was a minidump and "RunWatchdog" is in
        # the crashing thread stack, then it's a hang
        if "json_dump" in processed_crash:
            crash_data = processed_crash["json_dump"]
            try:
                crash_info = crash_data.get("crash_info") or {}
                crashing_thread = int(crash_info.get("crashing_thread", 0))
            except (TypeError, ValueError):
                crashing_thread = 0

            stack = glom(crash_data, "threads.%d.frames" % crashing_thread, default=[])
            for frame in stack:
                if "RunWatchdog" in (frame.get("function") or ""):
                    return "hang"

        return "crash"

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # "crash" is the default type
        report_type = self.identify_report_type(processed_crash, status)

        processed_crash["report_type"] = report_type

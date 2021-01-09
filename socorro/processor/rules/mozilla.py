# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import gzip
import json
import re
import time
from urllib.parse import unquote_plus
from zlib import error as ZlibError

from configman.dotdict import DotDict
from glom import glom
import markus

from socorro.lib import javautil
from socorro.lib import sentry_client
from socorro.lib.cache import ExpiringCache
from socorro.lib.context_tools import temp_file_context
from socorro.lib.datetimeutil import UTC, datetime_from_isodate_string
from socorro.lib.ooid import date_from_ooid
from socorro.lib.requestslib import session_with_retries
from socorro.lib.util import dotdict_to_dict
from socorro.processor.rules.base import Rule
from socorro.signature.generator import SignatureGenerator
from socorro.signature.utils import convert_to_crash_data


# NOTE(willkg): This is the sys.maxint value for Python in the docker container
# we run it in. Python 3 doesn't have a maxint, so when we switch to Python 3
# I'm not sure what we should replace this with.
MAXINT = 9223372036854775807


class ConvertModuleSignatureInfoRule(Rule):
    """Make ModuleSignatureInfo to a string.

    For a while, crash reports with annotations submitted as a JSON blob had
    ModuleSignatureInfo appended to the end of them as an object. This JSON-encodes that
    object so that the value is always a JSON-encoded string. That way, the rest of the
    processor doesn't have to handle both cases. Bug #1607806

    """

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return "ModuleSignatureInfo" in raw_crash and not isinstance(
            raw_crash["ModuleSignatureInfo"], str
        )

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        info = raw_crash["ModuleSignatureInfo"]
        if isinstance(info, DotDict):
            # Sometimes the value is a DotDict which json.dumps doesn't work with so
            # convert it to a dict first
            info = dotdict_to_dict(info)
        raw_crash["ModuleSignatureInfo"] = json.dumps(info)


class SubmittedFromInfobarFixRule(Rule):
    """Fix SubmittedFromInfobar annotation values to "1"

    SubmittedFromInfobar value was "true", but it should be "1". For crash reports
    with annotations submitted as a JSON blob, the value is not true (JSON bool true).
    This fixes both of those to "1" which is what the value should be. Bug #1626048

    Crash reports with annotations submitted as a JSON blob.

    """

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return "SubmittedFromInfobar" in raw_crash and raw_crash[
            "SubmittedFromInfobar"
        ] in ("true", True)

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash["SubmittedFromInfobar"] = "1"


class ProductRule(Rule):
    """Copy product data from raw crash to processed crash."""

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash["product"] = raw_crash.get("ProductName", "")
        processed_crash["version"] = raw_crash.get("Version", "")
        processed_crash["productid"] = raw_crash.get("ProductID", "")
        processed_crash["release_channel"] = raw_crash.get("ReleaseChannel", "")
        # redundant, but I want to exactly match old processors.
        processed_crash["ReleaseChannel"] = raw_crash.get("ReleaseChannel", "")
        processed_crash["build"] = raw_crash.get("BuildID", "")

        # NOTE(willkg): ApplicationBuildID is for Fenix which sends the gecko view build
        # id in BuildID.
        processed_crash["application_build_id"] = raw_crash.get(
            "ApplicationBuildID", ""
        )


class UserDataRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash["url"] = raw_crash.get("URL", None)
        processed_crash["user_comments"] = raw_crash.get("Comments", None)
        processed_crash["email"] = raw_crash.get("Email", None)


class EnvironmentRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash["app_notes"] = raw_crash.get("Notes", "")


class PluginRule(Rule):  # Hangs are here
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            plugin_hang_as_int = int(raw_crash.get("PluginHang", False))
        except ValueError:
            plugin_hang_as_int = 0
        if plugin_hang_as_int:
            processed_crash["hangid"] = "fake-" + raw_crash["uuid"]
        else:
            processed_crash["hangid"] = raw_crash.get("HangID", None)

        # the processed_crash["hang_type"] has the following meaning:
        #    hang_type == -1 is a plugin hang
        #    hang_type ==  1 is a browser hang
        #    hang_type ==  0 is not a hang at all, but a normal crash

        try:
            hang_as_int = int(raw_crash.get("Hang", False))
        except ValueError:
            hang_as_int = 0
        if hang_as_int:
            processed_crash["hang_type"] = 1
        elif plugin_hang_as_int:
            processed_crash["hang_type"] = -1
        elif processed_crash["hangid"]:
            processed_crash["hang_type"] = -1
        else:
            processed_crash["hang_type"] = 0

        processed_crash["process_type"] = raw_crash.get("ProcessType", None)

        if not processed_crash["process_type"]:
            return

        if processed_crash["process_type"] == "plugin":
            # Bug#543776 We actually will are relaxing the non-null policy...
            # a null filename, name, and version is OK. We'll use empty strings
            processed_crash["PluginFilename"] = raw_crash.get("PluginFilename", "")
            processed_crash["PluginName"] = raw_crash.get("PluginName", "")
            processed_crash["PluginVersion"] = raw_crash.get("PluginVersion", "")


class AddonsRule(Rule):
    def _get_formatted_addon(self, addon):
        """Return a properly formatted addon string.

        Format is: addon_identifier:addon_version

        This is used because some addons are missing a version. In order to
        simplify subsequent queries, we make sure the format is consistent.
        """
        return addon if ":" in addon else addon + ":NO_VERSION"

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
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
    def _get_truncate_or_warn(
        a_mapping, key, notes_list, default=None, max_length=10000
    ):
        try:
            return a_mapping[key][:max_length]
        except (KeyError, AttributeError):
            notes_list.append("WARNING: raw_crash missing %s" % key)
            return default
        except TypeError as x:
            notes_list.append(
                "WARNING: raw_crash[%s] contains unexpected value: %s; %s"
                % (key, a_mapping[key], str(x))
            )
            return default

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processor_notes = processor_meta["processor_notes"]

        processed_crash["submitted_timestamp"] = raw_crash.get(
            "submitted_timestamp", date_from_ooid(raw_crash["uuid"])
        )
        if isinstance(processed_crash["submitted_timestamp"], str):
            processed_crash["submitted_timestamp"] = datetime_from_isodate_string(
                processed_crash["submitted_timestamp"]
            )
        processed_crash["date_processed"] = processed_crash["submitted_timestamp"]
        # defaultCrashTime: must have crashed before date processed
        submitted_timestamp_as_epoch = int(
            time.mktime(processed_crash["submitted_timestamp"].timetuple())
        )
        try:
            # the old name for crash time
            timestampTime = int(
                raw_crash.get("timestamp", submitted_timestamp_as_epoch)
            )
        except ValueError:
            timestampTime = 0
            processor_notes.append('non-integer value of "timestamp"')
        try:
            crash_time = int(
                self._get_truncate_or_warn(
                    raw_crash, "CrashTime", processor_notes, timestampTime, 10
                )
            )
        except ValueError:
            crash_time = 0
            processor_notes.append(
                'non-integer value of "CrashTime" (%s)' % raw_crash["CrashTime"]
            )

        processed_crash["crash_time"] = crash_time
        if crash_time == submitted_timestamp_as_epoch:
            processor_notes.append("client_crash_date is unknown")
        # StartupTime: must have started up some time before crash
        try:
            startupTime = int(raw_crash.get("StartupTime", crash_time))
        except ValueError:
            startupTime = 0
            processor_notes.append('non-integer value of "StartupTime"')
        # InstallTime: must have installed some time before startup
        try:
            installTime = int(raw_crash.get("InstallTime", startupTime))
        except ValueError:
            installTime = 0
            processor_notes.append('non-integer value of "InstallTime"')
        processed_crash["client_crash_date"] = datetime.datetime.fromtimestamp(
            crash_time, UTC
        )
        processed_crash["install_age"] = crash_time - installTime
        processed_crash["uptime"] = max(0, crash_time - startupTime)
        try:
            last_crash = int(raw_crash["SecondsSinceLastCrash"])
        except (KeyError, TypeError, ValueError):
            last_crash = None
            processor_notes.append('non-integer value of "SecondsSinceLastCrash"')
        if last_crash and last_crash > MAXINT:
            last_crash = None
            processor_notes.append(
                '"SecondsSinceLastCrash" larger than MAXINT - set to NULL'
            )
        processed_crash["last_crash"] = last_crash


class JavaProcessRule(Rule):
    """Move Java-crash-related bits over."""

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return bool(raw_crash.get("JavaStackTrace", None))

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        # This can contain PII in the exception message
        processed_crash["java_stack_trace_raw"] = raw_crash["JavaStackTrace"]

        try:
            java_exception = javautil.parse_java_stack_trace(
                raw_crash["JavaStackTrace"]
            )
            java_stack_trace = java_exception.to_public_string()
        except javautil.MalformedJavaStackTrace:
            processor_meta["processor_notes"].append(
                "JavaProcessRule: malformed java stack trace"
            )
            java_stack_trace = "malformed"

        processed_crash["java_stack_trace"] = java_stack_trace


class MalformedBreadcrumbs(Exception):
    pass


def validate_breadcrumbs(data):
    """Validates a Breadcrumbs data structure

    :arg list data: list of breadcrumbs dicts

    :raises: MalformedBreadcrumbs if it's malformed in some way

    """
    # NOTE(willkg): Sentry doesn't _require_ timestamp in their Breadcrumbs event, but
    # it's highly recommended. We try to match their spec since that seemed helpful.
    # The other top level fields are optional. If we want to require other fields, we
    # can add them here.
    required_keys = {"timestamp"}

    if not isinstance(data, list):
        raise MalformedBreadcrumbs("not a list")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise MalformedBreadcrumbs(f"item {i} not a dict")

        # missing_keys is the required_keys minus the intersection of required_keys and
        # the item's keys
        missing_keys = required_keys - (required_keys & set(item.keys()))
        if missing_keys:
            missing_keys = ", ".join(sorted(missing_keys))
            raise MalformedBreadcrumbs(f"item {i} missing keys: {missing_keys}")


class BreadcrumbsRule(Rule):
    """Validate and move over breadcrumbs."""

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return bool(raw_crash.get("Breadcrumbs", None))

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        breadcrumbs = raw_crash["Breadcrumbs"]

        try:
            breadcrumbs_data = json.loads(breadcrumbs)

            # NOTE(willkg): Sentry specifies breadcrumbs with an intermediary "values"
            # dict. This check lets us handle how android-components crash reporter is
            # sending breadcrumbs as well as what a Sentry client would send.
            if isinstance(breadcrumbs_data, dict) and "values" in breadcrumbs_data:
                breadcrumbs_data = breadcrumbs_data["values"]

            validate_breadcrumbs(breadcrumbs_data)
            processed_crash["breadcrumbs"] = breadcrumbs_data
        except json.JSONDecodeError:
            processor_meta["processor_notes"].append(
                "Breadcrumbs: malformed: not valid json"
            )
        except MalformedBreadcrumbs as exc:
            processor_meta["processor_notes"].append(f"Breadcrumbs: malformed: {exc}")


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

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return bool(raw_crash.get("MozCrashReason", None))

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        crash_reason = raw_crash["MozCrashReason"]

        # This can contain PII in the exception message
        processed_crash["moz_crash_reason_raw"] = crash_reason
        processed_crash["moz_crash_reason"] = self.sanitize_reason(crash_reason)


class OutOfMemoryBinaryRule(Rule):
    # Number of bytes, max, that we accept memory info payloads as JSON.
    MAX_SIZE_UNCOMPRESSED = 20 * 1024 * 1024  # ~20Mb

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return "memory_report" in raw_dumps

    def _extract_memory_info(self, dump_pathname, processor_notes):
        """Extract and return the JSON data from the .json.gz memory report"""

        def error_out(error_message):
            processor_notes.append(error_message)
            return {"ERROR": error_message}

        try:
            fd = gzip.open(dump_pathname, "rb")
        except IOError as x:
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
        except (EOFError, IOError, ZlibError) as x:
            error_message = "error in gzip for %s: %r" % (dump_pathname, x)
            return error_out(error_message)
        except ValueError as x:
            error_message = "error in json for %s: %r" % (dump_pathname, x)
            return error_out(error_message)
        finally:
            fd.close()

        return memory_info

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        pathname = raw_dumps["memory_report"]
        with temp_file_context(pathname):
            memory_report = self._extract_memory_info(
                dump_pathname=pathname,
                processor_notes=processor_meta["processor_notes"],
            )

            if isinstance(memory_report, dict) and memory_report.get("ERROR"):
                processed_crash["memory_report_error"] = memory_report["ERROR"]
            else:
                processed_crash["memory_report"] = memory_report


class ProductRewrite(Rule):
    """Fix ProductName in raw crash for certain situations."""

    PRODUCT_MAP = {"{aa3c5121-dab2-40e2-81ca-7ea25febc110}": "FennecAndroid"}

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        product_name = raw_crash.get("ProductName", "")
        original_product_name = product_name

        # Rewrite from PRODUCT_MAP fixes.
        if raw_crash.get("ProductID", "") in self.PRODUCT_MAP:
            product_name = self.PRODUCT_MAP[raw_crash["ProductID"]]

        # If we made any product name changes, persist them and keep the
        # original one so we can look at things later
        if product_name != original_product_name:
            processor_meta["processor_notes"].append(
                "Rewriting ProductName from %r to %r"
                % (original_product_name, product_name)
            )
            raw_crash["ProductName"] = product_name
            raw_crash["OriginalProductName"] = original_product_name


class FenixVersionRewriteRule(Rule):
    """Fix 'Nightly YYMMDD HH:MM' version values to '0.0a1'

    This allows nightlies for Fenix to group in Crash Stats. We can probably ditch this
    at some point when we're not getting crash reports that have this version structure.

    Bug #1624911

    """

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        is_nightly = (raw_crash.get("Version") or "").startswith("Nightly ")
        return raw_crash.get("ProductName") == "Fenix" and is_nightly

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processor_meta["processor_notes"].append(
            "Changed version from %r to 0.0a1" % raw_crash.get("Version")
        )
        raw_crash["Version"] = "0.0a1"


class ESRVersionRewrite(Rule):
    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return raw_crash.get("ReleaseChannel", "") == "esr"

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            raw_crash["Version"] += "esr"
        except KeyError:
            processor_meta["processor_notes"].append(
                '"Version" missing from esr release raw_crash'
            )


class PluginContentURL(Rule):
    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            return bool(raw_crash["PluginContentURL"])
        except KeyError:
            return False

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash["URL"] = raw_crash["PluginContentURL"]


class PluginUserComment(Rule):
    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            return bool(raw_crash["PluginUserComment"])
        except KeyError:
            return False

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash["Comments"] = raw_crash["PluginUserComment"]


class ExploitablityRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            processed_crash["exploitability"] = processed_crash["json_dump"][
                "sensitive"
            ]["exploitability"]
        except KeyError:
            processed_crash["exploitability"] = "unknown"
            processor_meta["processor_notes"].append(
                "exploitability information missing"
            )


class FlashVersionRule(Rule):
    # A subset of the known "debug identifiers" for flash versions, associated
    # to the version
    KNOWN_FLASH_IDENTIFIERS = {
        "7224164B5918E29AF52365AF3EAF7A500": "10.1.51.66",
        "C6CDEFCDB58EFE5C6ECEF0C463C979F80": "10.1.51.66",
        "4EDBBD7016E8871A461CCABB7F1B16120": "10.1",
        "D1AAAB5D417861E6A5B835B01D3039550": "10.0.45.2",
        "EBD27FDBA9D9B3880550B2446902EC4A0": "10.0.45.2",
        "266780DB53C4AAC830AFF69306C5C0300": "10.0.42.34",
        "C4D637F2C8494896FBD4B3EF0319EBAC0": "10.0.42.34",
        "B19EE2363941C9582E040B99BB5E237A0": "10.0.32.18",
        "025105C956638D665850591768FB743D0": "10.0.32.18",
        "986682965B43DFA62E0A0DFFD7B7417F0": "10.0.23",
        "937DDCC422411E58EF6AD13710B0EF190": "10.0.23",
        "860692A215F054B7B9474B410ABEB5300": "10.0.22.87",
        "77CB5AC61C456B965D0B41361B3F6CEA0": "10.0.22.87",
        "38AEB67F6A0B43C6A341D7936603E84A0": "10.0.12.36",
        "776944FD51654CA2B59AB26A33D8F9B30": "10.0.12.36",
        "974873A0A6AD482F8F17A7C55F0A33390": "9.0.262.0",
        "B482D3DFD57C23B5754966F42D4CBCB60": "9.0.262.0",
        "0B03252A5C303973E320CAA6127441F80": "9.0.260.0",
        "AE71D92D2812430FA05238C52F7E20310": "9.0.246.0",
        "6761F4FA49B5F55833D66CAC0BBF8CB80": "9.0.246.0",
        "27CC04C9588E482A948FB5A87E22687B0": "9.0.159.0",
        "1C8715E734B31A2EACE3B0CFC1CF21EB0": "9.0.159.0",
        "F43004FFC4944F26AF228334F2CDA80B0": "9.0.151.0",
        "890664D4EF567481ACFD2A21E9D2A2420": "9.0.151.0",
        "8355DCF076564B6784C517FD0ECCB2F20": "9.0.124.0",
        "51C00B72112812428EFA8F4A37F683A80": "9.0.124.0",
        "9FA57B6DC7FF4CFE9A518442325E91CB0": "9.0.115.0",
        "03D99C42D7475B46D77E64D4D5386D6D0": "9.0.115.0",
        "0CFAF1611A3C4AA382D26424D609F00B0": "9.0.47.0",
        "0F3262B5501A34B963E5DF3F0386C9910": "9.0.47.0",
        "C5B5651B46B7612E118339D19A6E66360": "9.0.45.0",
        "BF6B3B51ACB255B38FCD8AA5AEB9F1030": "9.0.28.0",
        "83CF4DC03621B778E931FC713889E8F10": "9.0.16.0",
    }

    # A regular expression to match Flash file names
    FLASH_RE = re.compile(
        r"NPSWF32_?(.*)\.dll|"
        r"FlashPlayerPlugin_?(.*)\.exe|"
        r"libflashplayer(.*)\.(.*)|"
        r"Flash ?Player-?(.*)"
    )

    def _get_flash_version(self, **kwargs):
        """Extract flash version if recognized or None

        :returns: version; else (None or '')

        """
        filename = kwargs.get("filename", None)
        version = kwargs.get("version", None)
        debug_id = kwargs.get("debug_id", None)
        m = self.FLASH_RE.match(filename)
        if m:
            if version:
                return version

            # We didn't get a version passed in, so try do deduce it
            groups = m.groups()
            if groups[0]:
                return groups[0].replace("_", ".")
            if groups[1]:
                return groups[1].replace("_", ".")
            if groups[2]:
                return groups[2]
            if groups[4]:
                return groups[4]
            return self.KNOWN_FLASH_IDENTIFIERS.get(debug_id)
        return None

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash["flash_version"] = ""
        flash_version = None

        modules = processed_crash.get("json_dump", {}).get("modules", [])
        if isinstance(modules, (tuple, list)):
            for index, a_module in enumerate(modules):
                flash_version = self._get_flash_version(**a_module)
                if flash_version:
                    break

        if flash_version:
            processed_crash["flash_version"] = flash_version
        else:
            processed_crash["flash_version"] = "[blank]"


class TopMostFilesRule(Rule):
    """Origninating from Bug 519703, the topmost_filenames was specified as
    singular, there would be only one.  The original programmer, in the
    source code stated "Lets build in some flex" and allowed the field to
    have more than one in a list.  However, in all the years that this existed
    it was never expanded to use more than just one.  Meanwhile, the code
    ambiguously would sometimes give this as as single value and other times
    return it as a list of one item.

    This rule does not try to reproduce that imbiguity and avoids the list
    entirely, just giving one single value.  The fact that the destination
    varible in the processed_crash is plural rather than singular is
    unfortunate.

    """

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash["topmost_filenames"] = None
        try:
            crashing_thread = processed_crash["json_dump"]["crash_info"][
                "crashing_thread"
            ]
            stack_frames = processed_crash["json_dump"]["threads"][crashing_thread][
                "frames"
            ]
        except KeyError as x:
            # guess we don't have frames or crashing_thread or json_dump
            # we have to give up
            processor_meta["processor_notes"].append(
                "no 'topmost_file' name because '%s' is missing" % x
            )
            return

        for a_frame in stack_frames:
            source_filename = a_frame.get("file", None)
            if source_filename:
                processed_crash["topmost_filenames"] = source_filename
                return


class ModulesInStackRule(Rule):
    """
    Adds value with semi-colon separated set of "module/debugid" strings for
    all the modules that show up in the stack of the crashing thread.
    """

    # Filenames should contain A-Za-z0-9_. and that's it.
    BAD_FILENAME_CHARACTERS = re.compile(r"[^a-z0-9_\.]", re.IGNORECASE)

    # Debug ids are hex strings
    BAD_DEBUGID_CHARACTERS = re.compile(r"[^a-f0-9]", re.IGNORECASE)

    def format_module(self, item):
        filename = item.get("filename", "")
        filename = self.BAD_FILENAME_CHARACTERS.sub("", filename)

        debugid = item.get("debug_id", "")
        debugid = self.BAD_DEBUGID_CHARACTERS.sub("", debugid)

        return f"{filename}/{debugid}"

    def predicate(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        return "json_dump" in processed_crash

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        json_dump = processed_crash["json_dump"]
        try:
            crashing_thread = json_dump["crash_info"]["crashing_thread"]
        except KeyError:
            # If there is no crashing thread, then there's nothing to do.
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
    #: Hold at most this many items in cache; items are a key and a value
    #: both of which are short strings, so this doesn't take much memory
    CACHE_MAX_SIZE = 5000

    #: Items in cache expire after 30 minutes by default
    SHORT_CACHE_TTL = 60 * 30

    #: If we know it's good, cache it for 24 hours because it won't change
    LONG_CACHE_TTL = 60 * 60 * 24

    #: List of products to do lookups for
    SUPPORTED_PRODUCTS = ["firefox", "fennec", "fennecandroid"]

    def __init__(self, version_string_api):
        super().__init__()
        self.cache = ExpiringCache(
            max_size=self.CACHE_MAX_SIZE, default_ttl=self.SHORT_CACHE_TTL
        )
        self.metrics = markus.get_metrics("processor.betaversionrule")

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
        # Fix the product so it matches the data in the table
        if (product, channel) == ("firefox", "aurora") and build_id > "20170601":
            product = "DevEdition"
        elif product == "firefox":
            product = "Firefox"
        elif product in ("fennec", "fennecandroid"):
            product = "Fennec"

        key = "%s:%s:%s" % (product, channel, build_id)
        if key in self.cache:
            self.metrics.incr("cache", tags=["result:hit"])
            return self.cache[key]

        self.metrics.incr("cache", tags=["result:miss"])

        resp = self.session.get(
            self.version_string_api,
            params={"product": product, "channel": channel, "build_id": build_id},
        )

        if resp.status_code != 200:
            versions = []
        else:
            versions = resp.json()["hits"]

        if not versions:
            # We didn't get an answer which could mean that this is a weird
            # build and there is no answer or it could mean that Buildhub
            # doesn't know, yet. Maybe in the future we get a better answer so
            # we use the short ttl.
            self.metrics.incr("lookup", tags=["result:fail"])
            self.cache.set(key, value=None, ttl=self.SHORT_CACHE_TTL)
            return None

        # If we got an answer we should keep it around for a while because it's
        # a real answer and it's not going to change so use the long ttl plus
        # a fudge factor.
        real_version = versions[0]["version_string"]
        self.metrics.incr("lookup", tags=["result:success"])
        self.cache.set(key, value=real_version, ttl=self.LONG_CACHE_TTL)
        return real_version

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        # Beta and aurora versions send the wrong version in the crash report for
        # certain products
        product = processed_crash.get("product", "")
        release_channel = processed_crash.get("release_channel", "")
        return (
            product.lower() in self.SUPPORTED_PRODUCTS
            and release_channel.lower()
            in (
                "beta",
                "aurora",
            )
        )

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        product = processed_crash.get("product", "").strip().lower()
        build_id = processed_crash.get("build", "").strip()
        release_channel = processed_crash.get("release_channel").strip()

        # Only run if we've got all the things we need
        if (
            product
            and build_id
            and release_channel
            and product in self.SUPPORTED_PRODUCTS
        ):
            # Convert the build_id to a str for lookups
            build_id = str(build_id)

            real_version = self._get_real_version(product, release_channel, build_id)
            if real_version:
                processed_crash["version"] = real_version
                return

            self.logger.info(
                "betaversionrule: failed lookup %s %s %s %s",
                processed_crash.get("uuid"),
                product,
                release_channel,
                build_id,
            )

        # No real version, but this is an aurora or beta crash report, so we
        # tack on "b0" to make it match the channel
        processed_crash["version"] += "b0"
        processor_meta["processor_notes"].append(
            'release channel is %s but no version data was found - added "b0" '
            "suffix to version number" % release_channel
        )


class OSPrettyVersionRule(Rule):
    """Populate os_pretty_version with most readable operating system version string.

    This rule attempts to extract the most useful, singular, human understandable field
    for operating system version. This should always be attempted.

    For Windows, this is a lookup against a map.

    For Mac OSX, this pulls from os_name and os_version.

    For Linux, this uses json_dump.lsb_release.description if it's available.

    """

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
    }

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        # we will overwrite this field with the current best option
        # in stages, as we divine a better name
        processed_crash["os_pretty_version"] = None

        pretty_name = processed_crash.get("os_name")
        if not isinstance(pretty_name, str):
            # This data is bogus or isn't there, there's nothing we can do.
            return True

        # At this point, os_name is the best info we have
        processed_crash["os_pretty_version"] = pretty_name

        os_version = processed_crash.get("os_version") or ""
        if not os_version:
            # The version number is missing, there's nothing more to do.
            return True

        version_split = os_version.split(".")
        if len(version_split) < 2:
            # The version number is invalid, there's nothing more to do.
            return

        os_name = processed_crash.get("os_name") or ""
        major_version = int(version_split[0])
        minor_version = int(version_split[1])

        if os_name.lower().startswith("windows"):
            processed_crash["os_pretty_version"] = self.WINDOWS_VERSIONS.get(
                "%s.%s" % (major_version, minor_version), "Windows Unknown"
            )
            return

        elif os_name == "Mac OS X":
            if major_version >= 10 and minor_version >= 0:
                pretty_name = "OS X %s.%s" % (major_version, minor_version)
            else:
                pretty_name = "OS X Unknown"

        elif os_name == "Linux":
            pretty_name = (
                glom(processed_crash, "json_dump.lsb_release.description", default="")
                or pretty_name
            )

        processed_crash["os_pretty_version"] = pretty_name


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

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
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

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
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
        extra["uuid"] = crash_data.get("uuid", None)
        sentry_client.capture_error(self.logger, exc_info=exc_info, extra=extra)

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        # Generate a crash signature and capture the signature and notes
        crash_data = convert_to_crash_data(raw_crash, processed_crash)
        ret = self.generator.generate(crash_data)
        processed_crash["signature"] = ret.signature
        processor_meta["processor_notes"].extend(ret.notes)
        # NOTE(willkg): this picks up proto_signature
        processed_crash.update(ret.extra)


class PHCRule(Rule):
    """Performs PHC-related annotation processing.

    PHC stands for probabilistic heap checker. It adds a set of annotations
    that need to be adjusted so as to be searchable and usable in Crash Stats.

    Bug #1523278.

    """

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return "PHCKind" in raw_crash

    def action(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        # Add PHCKind which is a string
        processed_crash["phc_kind"] = raw_crash["PHCKind"]

        # Convert PHCBaseAddress from decimal to hex and add to processed crash
        if "PHCBaseAddress" in raw_crash:
            try:
                phc_base_address = hex(int(raw_crash["PHCBaseAddress"]))
                processed_crash["phc_base_address"] = phc_base_address
            except ValueError:
                pass

        # Add PHCUsableSize which is an integer
        if "PHCUsableSize" in raw_crash:
            try:
                processed_crash["phc_usable_size"] = int(raw_crash["PHCUsableSize"])
            except ValueError:
                pass

        # FIXME(willkg): We should symbolicate PHCAllocStack and PHCFreeStack and
        # put the symbolicated stacks in a new field.
        # See bug #1523278.

        # Add PHCAllocStack which is a comma-separated list of integers
        if "PHCAllocStack" in raw_crash:
            processed_crash["phc_alloc_stack"] = raw_crash["PHCAllocStack"]

        # Add PHCFreeStack which is a comma-separated list of integers
        if "PHCFreeStack" in raw_crash:
            processed_crash["phc_free_stack"] = raw_crash["PHCFreeStack"]

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import gzip
import random
import re
from sys import maxint
from past.builtins import basestring
import time
from urllib import unquote_plus

from requests import RequestException
import ujson

from socorro.lib import javautil
from socorro.lib import raven_client
from socorro.lib.cache import ExpiringCache
from socorro.lib.context_tools import temp_file_context
from socorro.lib.datetimeutil import (
    UTC,
    datetime_from_isodate_string,
)
from socorro.lib.ooid import dateFromOoid
from socorro.lib.requestslib import session_with_retries
from socorro.lib.transform_rules import Rule
from socorro.signature.generator import SignatureGenerator
from socorro.signature.utils import convert_to_crash_data


class ProductRule(Rule):

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.product = raw_crash.get('ProductName', '')
        processed_crash.version = raw_crash.get('Version', '')
        processed_crash.productid = raw_crash.get('ProductID', '')
        processed_crash.distributor = raw_crash.get('Distributor', None)
        processed_crash.distributor_version = raw_crash.get(
            'Distributor_version',
            None
        )
        processed_crash.release_channel = raw_crash.get('ReleaseChannel', '')
        # redundant, but I want to exactly match old processors.
        processed_crash.ReleaseChannel = raw_crash.get('ReleaseChannel', '')
        processed_crash.build = raw_crash.get('BuildID', '')

        return True


class UserDataRule(Rule):

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.url = raw_crash.get('URL', None)
        processed_crash.user_comments = raw_crash.get('Comments', None)
        processed_crash.email = raw_crash.get('Email', None)
        #processed_crash.user_id = raw_crash.get('UserID', '')
        processed_crash.user_id = ''

        return True


class EnvironmentRule(Rule):

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.app_notes = raw_crash.get('Notes', '')

        return True


class PluginRule(Rule):   # Hangs are here

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        try:
            plugin_hang_as_int = int(raw_crash.get('PluginHang', False))
        except ValueError:
            plugin_hang_as_int = 0
        if plugin_hang_as_int:
            processed_crash.hangid = 'fake-' + raw_crash.uuid
        else:
            processed_crash.hangid = raw_crash.get('HangID', None)

        # the processed_crash.hang_type has the following meaning:
        #    hang_type == -1 is a plugin hang
        #    hang_type ==  1 is a browser hang
        #    hang_type ==  0 is not a hang at all, but a normal crash

        try:
            hang_as_int = int(raw_crash.get('Hang', False))
        except ValueError:
            hang_as_int = 0
        if hang_as_int:
            processed_crash.hang_type = 1
        elif plugin_hang_as_int:
            processed_crash.hang_type = -1
        elif processed_crash.hangid:
            processed_crash.hang_type = -1
        else:
            processed_crash.hang_type = 0

        processed_crash.process_type = raw_crash.get('ProcessType', None)

        if not processed_crash.process_type:
            return True

        if processed_crash.process_type == 'plugin':
            # Bug#543776 We actually will are relaxing the non-null policy...
            # a null filename, name, and version is OK. We'll use empty strings
            processed_crash.PluginFilename = (
                raw_crash.get('PluginFilename', '')
            )
            processed_crash.PluginName = (
                raw_crash.get('PluginName', '')
            )
            processed_crash.PluginVersion = (
                raw_crash.get('PluginVersion', '')
            )

        return True


class AddonsRule(Rule):

    def version(self):
        return '1.0'

    def _get_formatted_addon(self, addon):
        """Return a properly formatted addon string.

        Format is: addon_identifier:addon_version

        This is used because some addons are missing a version. In order to
        simplify subsequent queries, we make sure the format is consistent.
        """
        return addon if ':' in addon else addon + ':NO_VERSION'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.addons_checked = None

        # it's okay to not have EMCheckCompatibility
        if 'EMCheckCompatibility' in raw_crash:
            addons_checked_txt = raw_crash.EMCheckCompatibility.lower()
            processed_crash.addons_checked = False
            if addons_checked_txt == 'true':
                processed_crash.addons_checked = True

        original_addon_str = raw_crash.get('Add-ons', '')
        if not original_addon_str:
            processed_crash.addons = []
        else:
            processed_crash.addons = [
                unquote_plus(self._get_formatted_addon(x))
                for x in original_addon_str.split(',')
            ]

        return True


class DatesAndTimesRule(Rule):

    def version(self):
        return '1.0'

    @staticmethod
    def _get_truncate_or_warn(
        a_mapping,
        key,
        notes_list,
        default=None,
        max_length=10000
    ):
        try:
            return a_mapping[key][:max_length]
        except (KeyError, AttributeError):
            notes_list.append("WARNING: raw_crash missing %s" % key)
            return default
        except TypeError as x:
            notes_list.append(
                "WARNING: raw_crash[%s] contains unexpected value: %s; %s" %
                (key, a_mapping[key], str(x))
            )
            return default

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processor_notes = processor_meta.processor_notes

        processed_crash.submitted_timestamp = raw_crash.get(
            'submitted_timestamp',
            dateFromOoid(raw_crash.uuid)
        )
        if isinstance(processed_crash.submitted_timestamp, basestring):
            processed_crash.submitted_timestamp = datetime_from_isodate_string(
                processed_crash.submitted_timestamp
            )
        processed_crash.date_processed = processed_crash.submitted_timestamp
        # defaultCrashTime: must have crashed before date processed
        submitted_timestamp_as_epoch = int(
            time.mktime(processed_crash.submitted_timestamp.timetuple())
        )
        try:
            timestampTime = int(
                raw_crash.get('timestamp', submitted_timestamp_as_epoch)
            )  # the old name for crash time
        except ValueError:
            timestampTime = 0
            processor_notes.append('non-integer value of "timestamp"')
        try:
            crash_time = int(
                self._get_truncate_or_warn(
                    raw_crash,
                    'CrashTime',
                    processor_notes,
                    timestampTime,
                    10
                )
            )
        except ValueError:
            crash_time = 0
            processor_notes.append(
                'non-integer value of "CrashTime" (%s)' % raw_crash.CrashTime
            )

        processed_crash.crash_time = crash_time
        if crash_time == submitted_timestamp_as_epoch:
            processor_notes.append("client_crash_date is unknown")
        # StartupTime: must have started up some time before crash
        try:
            startupTime = int(raw_crash.get('StartupTime', crash_time))
        except ValueError:
            startupTime = 0
            processor_notes.append('non-integer value of "StartupTime"')
        # InstallTime: must have installed some time before startup
        try:
            installTime = int(raw_crash.get('InstallTime', startupTime))
        except ValueError:
            installTime = 0
            processor_notes.append('non-integer value of "InstallTime"')
        processed_crash.client_crash_date = datetime.datetime.fromtimestamp(
            crash_time,
            UTC
        )
        processed_crash.install_age = crash_time - installTime
        processed_crash.uptime = max(0, crash_time - startupTime)
        try:
            last_crash = int(raw_crash.SecondsSinceLastCrash)
        except (KeyError, TypeError, ValueError):
            last_crash = None
            processor_notes.append(
                'non-integer value of "SecondsSinceLastCrash"'
            )
        if last_crash > maxint:
            last_crash = None
            processor_notes.append(
                '"SecondsSinceLastCrash" larger than MAXINT - set to NULL'
            )
        processed_crash.last_crash = last_crash

        return True


class JavaProcessRule(Rule):

    def version(self):
        return '1.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return bool(raw_crash.get('JavaStackTrace', None))

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        # This can contain PII in the exception message
        processed_crash['java_stack_trace_full'] = raw_crash['JavaStackTrace']

        try:
            java_exception = javautil.parse_java_stack_trace(raw_crash['JavaStackTrace'])
            java_stack_trace = java_exception.to_public_string()
        except javautil.MalformedJavaStackTrace:
            processor_meta.processor_notes.append('JavaProcessRule: malformed java stack trace')
            java_stack_trace = 'malformed'

        processed_crash['java_stack_trace'] = java_stack_trace

        return True


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
        'Failed to load module',
        'byte index',
    )

    def sanitize_reason(self, reason):
        if reason.startswith(self.DISALLOWED_PREFIXES):
            return 'sanitized--see moz_crash_reason_raw'
        return reason

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return bool(raw_crash.get('MozCrashReason', None))

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        crash_reason = raw_crash['MozCrashReason']

        # This can contain PII in the exception message
        processed_crash['moz_crash_reason_raw'] = crash_reason
        processed_crash['moz_crash_reason'] = self.sanitize_reason(crash_reason)

        return True


class OutOfMemoryBinaryRule(Rule):

    # Number of bytes, max, that we accept memory info payloads as JSON.
    MAX_SIZE_UNCOMPRESSED = 20 * 1024 * 1024  # ~20Mb

    def version(self):
        return '1.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return 'memory_report' in raw_dumps

    def _extract_memory_info(self, dump_pathname, processor_notes):
        """Extract and return the JSON data from the .json.gz memory report.
        file"""
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
                error_message = (
                    "Uncompressed memory info too large %d (max: %d)" % (
                        len(memory_info_as_string),
                        self.MAX_SIZE_UNCOMPRESSED
                    )
                )
                return error_out(error_message)

            memory_info = ujson.loads(memory_info_as_string)
        except IOError as x:
            error_message = "error in gzip for %s: %r" % (dump_pathname, x)
            return error_out(error_message)
        except ValueError as x:
            error_message = "error in json for %s: %r" % (dump_pathname, x)
            return error_out(error_message)
        finally:
            fd.close()

        return memory_info

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        pathname = raw_dumps['memory_report']
        with temp_file_context(pathname):
            memory_report = self._extract_memory_info(
                dump_pathname=pathname,
                processor_notes=processor_meta.processor_notes
            )

            if isinstance(memory_report, dict) and memory_report.get('ERROR'):
                processed_crash.memory_report_error = memory_report['ERROR']
            else:
                processed_crash.memory_report = memory_report

        return True


class ProductRewrite(Rule):
    """Fix ProductName in raw crash for certain situations

    NOTE(willkg): This changes the raw crash which is gross.

    """

    PRODUCT_MAP = {
        "{aa3c5121-dab2-40e2-81ca-7ea25febc110}": "FennecAndroid",
    }

    def version(self):
        return '2.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return True

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        product_name = raw_crash.get('ProductName', '')
        original_product_name = product_name

        # Rewrite from PRODUCT_MAP fixes.
        if raw_crash.get('ProductID', '') in self.PRODUCT_MAP:
            product_name = self.PRODUCT_MAP[raw_crash['ProductID']]

        # If we made any product name changes, persist them and keep the
        # original one so we can look at things later
        if product_name != original_product_name:
            processor_meta.processor_notes.append(
                'Rewriting ProductName from %r to %r' % (original_product_name, product_name)
            )
            raw_crash['ProductName'] = product_name
            raw_crash['OriginalProductName'] = original_product_name

        return True


class ESRVersionRewrite(Rule):

    def version(self):
        return '2.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return raw_crash.get('ReleaseChannel', '') == 'esr'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            raw_crash['Version'] += 'esr'
        except KeyError:
            processor_meta.processor_notes.append(
                '"Version" missing from esr release raw_crash'
            )


class PluginContentURL(Rule):

    def version(self):
        return '2.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            return bool(raw_crash['PluginContentURL'])
        except KeyError:
            return False

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash['URL'] = raw_crash['PluginContentURL']
        return True


class PluginUserComment(Rule):

    def version(self):
        return '2.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            return bool(raw_crash['PluginUserComment'])
        except KeyError:
            return False

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash['Comments'] = raw_crash['PluginUserComment']
        return True


class ExploitablityRule(Rule):

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            processed_crash.exploitability = (
                processed_crash['json_dump']
                ['sensitive']['exploitability']
            )
        except KeyError:
            processed_crash.exploitability = 'unknown'
            processor_meta.processor_notes.append(
                "exploitability information missing"
            )
        return True


class FlashVersionRule(Rule):
    # A subset of the known "debug identifiers" for flash versions, associated
    # to the version
    KNOWN_FLASH_IDENTIFIERS = {
        '7224164B5918E29AF52365AF3EAF7A500': '10.1.51.66',
        'C6CDEFCDB58EFE5C6ECEF0C463C979F80': '10.1.51.66',
        '4EDBBD7016E8871A461CCABB7F1B16120': '10.1',
        'D1AAAB5D417861E6A5B835B01D3039550': '10.0.45.2',
        'EBD27FDBA9D9B3880550B2446902EC4A0': '10.0.45.2',
        '266780DB53C4AAC830AFF69306C5C0300': '10.0.42.34',
        'C4D637F2C8494896FBD4B3EF0319EBAC0': '10.0.42.34',
        'B19EE2363941C9582E040B99BB5E237A0': '10.0.32.18',
        '025105C956638D665850591768FB743D0': '10.0.32.18',
        '986682965B43DFA62E0A0DFFD7B7417F0': '10.0.23',
        '937DDCC422411E58EF6AD13710B0EF190': '10.0.23',
        '860692A215F054B7B9474B410ABEB5300': '10.0.22.87',
        '77CB5AC61C456B965D0B41361B3F6CEA0': '10.0.22.87',
        '38AEB67F6A0B43C6A341D7936603E84A0': '10.0.12.36',
        '776944FD51654CA2B59AB26A33D8F9B30': '10.0.12.36',
        '974873A0A6AD482F8F17A7C55F0A33390': '9.0.262.0',
        'B482D3DFD57C23B5754966F42D4CBCB60': '9.0.262.0',
        '0B03252A5C303973E320CAA6127441F80': '9.0.260.0',
        'AE71D92D2812430FA05238C52F7E20310': '9.0.246.0',
        '6761F4FA49B5F55833D66CAC0BBF8CB80': '9.0.246.0',
        '27CC04C9588E482A948FB5A87E22687B0': '9.0.159.0',
        '1C8715E734B31A2EACE3B0CFC1CF21EB0': '9.0.159.0',
        'F43004FFC4944F26AF228334F2CDA80B0': '9.0.151.0',
        '890664D4EF567481ACFD2A21E9D2A2420': '9.0.151.0',
        '8355DCF076564B6784C517FD0ECCB2F20': '9.0.124.0',
        '51C00B72112812428EFA8F4A37F683A80': '9.0.124.0',
        '9FA57B6DC7FF4CFE9A518442325E91CB0': '9.0.115.0',
        '03D99C42D7475B46D77E64D4D5386D6D0': '9.0.115.0',
        '0CFAF1611A3C4AA382D26424D609F00B0': '9.0.47.0',
        '0F3262B5501A34B963E5DF3F0386C9910': '9.0.47.0',
        'C5B5651B46B7612E118339D19A6E66360': '9.0.45.0',
        'BF6B3B51ACB255B38FCD8AA5AEB9F1030': '9.0.28.0',
        '83CF4DC03621B778E931FC713889E8F10': '9.0.16.0',
    }

    # A regular expression to match Flash file names
    FLASH_RE = re.compile(
        r'NPSWF32_?(.*)\.dll|'
        'FlashPlayerPlugin_?(.*)\.exe|'
        'libflashplayer(.*)\.(.*)|'
        'Flash ?Player-?(.*)'
    )

    def version(self):
        return '1.0'

    def _get_flash_version(self, **kwargs):
        """Extract flash version if recognized or None

        :returns: version; else (None or '')

        """
        filename = kwargs.get('filename', None)
        version = kwargs.get('version', None)
        debug_id = kwargs.get('debug_id', None)
        m = self.FLASH_RE.match(filename)
        if m:
            if version:
                return version

            # We didn't get a version passed in, so try do deduce it
            groups = m.groups()
            if groups[0]:
                return groups[0].replace('_', '.')
            if groups[1]:
                return groups[1].replace('_', '.')
            if groups[2]:
                return groups[2]
            if groups[4]:
                return groups[4]
            return self.KNOWN_FLASH_IDENTIFIERS.get(debug_id)
        return None

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.flash_version = ''
        flash_version = None

        modules = processed_crash.get('json_dump', {}).get('modules', [])
        if isinstance(modules, (tuple, list)):
            for index, a_module in enumerate(modules):
                flash_version = self._get_flash_version(**a_module)
                if flash_version:
                    break

        if flash_version:
            processed_crash.flash_version = flash_version
        else:
            processed_crash.flash_version = '[blank]'
        return True


class Winsock_LSPRule(Rule):

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.Winsock_LSP = raw_crash.get('Winsock_LSP', None)


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
    unfortunate."""

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.topmost_filenames = None
        try:
            crashing_thread = (
                processed_crash.json_dump['crash_info']['crashing_thread']
            )
            stack_frames = (
                processed_crash.json_dump['threads'][crashing_thread]['frames']
            )
        except KeyError as x:
            # guess we don't have frames or crashing_thread or json_dump
            # we have to give up
            processor_meta.processor_notes.append(
                "no 'topmost_file' name because '%s' is missing" % x
            )
            return True

        for a_frame in stack_frames:
            source_filename = a_frame.get('file', None)
            if source_filename:
                processed_crash.topmost_filenames = source_filename
                return True
        return True


class BetaVersionRule(Rule):
    #: Hold at most this many items in cache; items are a key and a value
    #: both of which are short strings, so this doesn't take much memory
    CACHE_MAX_SIZE = 5000

    #: Items in cache expire after 30 minutes by default
    SHORT_CACHE_TTL = 60 * 30

    #: If we know it's good, cache it for 24 hours because it won't change
    LONG_CACHE_TTL = 60 * 60 * 24

    #: Products that are on Buildhub--we don't want to ask Buildhub about others
    BUILDHUB_PRODUCTS = ['firefox', 'fennec', 'fennecandroid']

    def __init__(self, config):
        super(BetaVersionRule, self).__init__(config)
        # NOTE(willkg): These config values come from Processor2015 instance.
        self.buildhub_api = config.buildhub_api
        self.cache = ExpiringCache(max_size=self.CACHE_MAX_SIZE, default_ttl=self.SHORT_CACHE_TTL)

    def version(self):
        return '1.0'

    def _get_real_version(self, product, build_id, channel):
        """Return the real version number of a specified product, build, channel

        For example, beta builds of Firefox declare their version number as the
        major version (i.e. version 54.0b3 would say its version is 54.0). This
        database call returns the actual version number of said build (i.e.
        54.0b3 for the previous example).

        This caches good answers for a long time and bad answers for a short
        time to reduce Buildhub usage.

        :arg product: the product
        :arg build_id: the build_id as a string
        :arg channel: the release channel

        :returns: ``None`` or the version string that should be used

        :raises requests.RequestException: raised if it has connection issues with
            the host specified in ``version_string_api``

        """
        # NOTE(willkg): AURORA LIVES!
        #
        # But seriously, if this is for Firefox/aurora and the build id is after
        # 20170601, then we ask Buildhub about devedition/aurora instead because
        # devedition is the aurora channel
        if (product, channel) == ('firefox', 'aurora') and build_id > '20170601':
            product = 'devedition'

        # Buildhub product is "fennec", not "fennecandroid", so we have to switch
        # it
        if product == 'fennecandroid':
            product = 'fennec'

        key = '%s:%s:%s' % (product, build_id, channel)
        if key in self.cache:
            return self.cache[key]

        session = session_with_retries(self.buildhub_api)

        query = {
            'source.product': product,
            'build.id': '"%s"' % build_id,
            'target.channel': channel,
        }

        if channel == 'release':
            # If it's the release channel, we can specify we only want to see
            # "rc" versions and thus limit the result set to 1
            query['like_target.version'] = '*rc*'
            query['_limit'] = 1

        resp = session.get(self.buildhub_api, params=query)

        if resp.status_code == 200:
            hits = resp.json()['data']

            # Shimmy to add to ttl so as to distribute cache misses over time and reduce
            # HTTP requests from bunching up.
            shimmy = random.randint(1, 120)

            if hits and channel in ('aurora', 'beta'):
                # For aurora and beta channel lookups, we want a non-"rc"
                # version, but we can't specify that. So we ask for all the
                # versions and winnow out the rc ones on our own.
                #
                # FIXME(willkg): This is silly and it'd be better to filter
                # it out on Buildhub.
                hits = [
                    hit for hit in hits
                    if 'rc' not in hit['target']['version']
                ]

            if hits:
                # If we got an answer we should keep it around for a while because it's
                # a real answer and it's not going to change so use the long ttl plus
                # a fudge factor.
                real_version = hits[0]['target']['version']
                self.cache.set(key, value=real_version, ttl=self.LONG_CACHE_TTL + shimmy)
                return real_version

            # We didn't get an answer which could mean that this is a weird
            # build and there is no answer or it could mean that Buildhub
            # doesn't know, yet. Maybe in the future we get a better answer
            # so we use the short ttl plus a fudge factor.
            self.cache.set(key, value=None, ttl=self.SHORT_CACHE_TTL + shimmy)

        return None

    def is_final_beta(self, version):
        """Denotes whether this version could be a final beta"""
        # NOTE(willkg): this started with 26.0 and 38.0.5 was an out-of-cycle
        # exception
        return version > 26.0 and (version.endswith('.0') or version == '38.0.5')

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        # Beta and aurora versions send the wrong version in the crash report,
        # so we need to fix them
        return processed_crash.get('release_channel', '').lower() in ('beta', 'aurora')

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        product = processed_crash.get('product').strip().lower()
        try:
            # Convert the build id to an int as a hand-wavey validity check
            build_id = int(processed_crash.get('build').strip())
        except ValueError:
            build_id = None
        release_channel = processed_crash.get('release_channel').strip()

        # If we're missing one of the magic ingredients, then there's nothing
        # to do
        if product and build_id and release_channel and product in self.BUILDHUB_PRODUCTS:
            # Convert the build_id to a str for lookups
            build_id = str(build_id)

            try:
                real_version = self._get_real_version(product, build_id, release_channel)

                # If we got a real version, toss that in and we're done
                if real_version:
                    processed_crash['version'] = real_version
                    return True

                # We didn't get a version from Buildhub, but this might be a
                # "final beta" which Buildhub has an entry for in the release
                # channel. So we check Buildhub asking about the release
                # channel and get back an rc version.
                version = processed_crash.get('version').strip()
                if version and release_channel == 'beta' and self.is_final_beta(version):
                    real_version = self._get_real_version(product, build_id, 'release')

                    if real_version:
                        processed_crash['version'] = real_version
                        return True

            except RequestException as exc:
                processor_meta.processor_notes.append('could not connect to Buildhub')
                self.config.logger.exception(
                    '%s when connecting to %s', exc, self.version_string_api
                )

        # No real version, but this is an aurora or beta crash report, so we
        # tack on "b0" to make it match the channel
        processed_crash['version'] += 'b0'
        processor_meta.processor_notes.append(
            'release channel is %s but no version data was found - added "b0" '
            'suffix to version number' % release_channel
        )

        return True


class OSPrettyVersionRule(Rule):
    '''This rule attempts to extract the most useful, singular, human
    understandable field for operating system version. This should always be
    attempted.
    '''

    WINDOWS_VERSIONS = {
        '3.5': 'Windows NT',
        '4.0': 'Windows NT',
        '4.1': 'Windows 98',
        '4.9': 'Windows Me',
        '5.0': 'Windows 2000',
        '5.1': 'Windows XP',
        '5.2': 'Windows Server 2003',
        '6.0': 'Windows Vista',
        '6.1': 'Windows 7',
        '6.2': 'Windows 8',
        '6.3': 'Windows 8.1',
        '10.0': 'Windows 10',
    }

    def version(self):
        return '2.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        # we will overwrite this field with the current best option
        # in stages, as we divine a better name
        processed_crash['os_pretty_version'] = None

        pretty_name = processed_crash.get('os_name')
        if not isinstance(pretty_name, basestring):
            # This data is bogus or isn't there, there's nothing we can do.
            return True

        # at this point, os_name is the best info we have
        processed_crash['os_pretty_version'] = pretty_name

        if not processed_crash.get('os_version'):
            # The version number is missing, there's nothing more to do.
            return True

        version_split = processed_crash.os_version.split('.')

        if len(version_split) < 2:
            # The version number is invalid, there's nothing more to do.
            return True

        major_version = int(version_split[0])
        minor_version = int(version_split[1])

        if processed_crash.os_name.lower().startswith('windows'):
            processed_crash['os_pretty_version'] = self.WINDOWS_VERSIONS.get(
                '%s.%s' % (major_version, minor_version),
                'Windows Unknown'
            )
            return True

        if processed_crash.os_name == 'Mac OS X':
            if (
                major_version >= 10 and
                major_version < 11 and
                minor_version >= 0
            ):
                pretty_name = 'OS X %s.%s' % (major_version, minor_version)
            else:
                pretty_name = 'OS X Unknown'

        processed_crash['os_pretty_version'] = pretty_name
        return True


class ThemePrettyNameRule(Rule):
    """The Firefox theme shows up commonly in crash reports referenced by its
    internal ID. The ID is not easy to change, and is referenced by id in other
    software.

    This rule attempts to modify it to have a more identifiable name, like
    other built-in extensions.

    Must be run after the Addons Rule."""

    def __init__(self, config):
        super(ThemePrettyNameRule, self).__init__(config)
        self.conversions = {
            "{972ce4c6-7e08-4474-a285-3208198ce6fd}":
                "{972ce4c6-7e08-4474-a285-3208198ce6fd} "
                "(default theme)",
        }

    def version(self):
        return '1.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        '''addons is expected to be a list of strings like 'extension:version',
        but we are being overly cautious and consider the case where they
        lack the ':version' part, because user inputs are never reliable.
        '''
        addons = processed_crash.get('addons', [])

        for addon in addons:
            extension = addon.split(':')[0]
            if extension in self.conversions:
                return True
        return False

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        addons = processed_crash.addons

        for index, addon in enumerate(addons):
            if ':' in addon:
                extension, version = addon.split(':', 1)
                if extension in self.conversions:
                    addons[index] = ':'.join(
                        (self.conversions[extension], version)
                    )
            elif addon in self.conversions:
                addons[index] = self.conversions[addon]
        return True


class SignatureGeneratorRule(Rule):
    """Generates a Socorro crash signature"""

    def __init__(self, config):
        super(SignatureGeneratorRule, self).__init__(config)
        try:
            sentry_dsn = self.config.sentry.dsn
        except KeyError:
            # NOTE(willkg): DotDict raises a KeyError when things are missing
            sentry_dsn = None
        self.sentry_dsn = sentry_dsn
        self.generator = SignatureGenerator(error_handler=self._error_handler)

    def _error_handler(self, crash_data, exc_info, extra):
        """Captures errors from signature generation"""
        extra['uuid'] = crash_data.get('uuid', None)
        raven_client.capture_error(
            self.sentry_dsn, self.config.logger, exc_info=exc_info, extra=extra
        )

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        # Generate a crash signature and capture the signature and notes
        crash_data = convert_to_crash_data(raw_crash, processed_crash)
        ret = self.generator.generate(crash_data)
        processed_crash['signature'] = ret['signature']
        if 'proto_signature' in ret:
            processed_crash['proto_signature'] = ret['proto_signature']
        processor_meta['processor_notes'].extend(ret['notes'])
        return True

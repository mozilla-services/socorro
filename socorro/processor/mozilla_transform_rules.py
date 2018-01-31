# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import gzip
import re
from sys import maxint
import time
from urllib import unquote_plus

from configman import Namespace
from configman.converters import str_to_python_object
import ujson

from socorro.external.postgresql.dbapi2_util import (
    execute_query_fetchall,
    execute_no_results
)
from socorro.lib.context_tools import temp_file_context
from socorro.lib.datetimeutil import (
    UTC,
    datetime_from_isodate_string,
    datestring_to_weekly_partition
)
from socorro.lib.ooid import dateFromOoid
from socorro.lib.transform_rules import Rule
from socorro.signature.generator import SignatureGenerator


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
    required_config = Namespace()
    required_config.add_option(
        'collect_addon',
        doc='boolean indictating if information about add-ons should be '
        'collected',
        default=True,
    )

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
        try:
            addons_checked_txt = raw_crash.EMCheckCompatibility.lower()
            processed_crash.addons_checked = False
            if addons_checked_txt == 'true':
                processed_crash.addons_checked = True
        except KeyError as e:
            if 'EMCheckCompatibility' not in str(e):
                raise
            # it's okay to not have EMCheckCompatibility, other missing things
            # are bad

        if self.config.chatty:
            self.config.logger.debug(
                'AddonsRule: collect_addon: %s',
                self.config.collect_addon
            )

        if self.config.collect_addon:
            original_addon_str = raw_crash.get('Add-ons', '')
            if not original_addon_str:
                if self.config.chatty:
                    self.config.logger.debug(
                        'AddonsRule: no addons'
                    )
                processed_crash.addons = []
            else:
                if self.config.chatty:
                    self.config.logger.debug(
                        'AddonsRule: trying to split addons'
                    )
                processed_crash.addons = [
                    unquote_plus(self._get_formatted_addon(x))
                    for x in original_addon_str.split(',')
                ]
            if self.config.chatty:
                self.config.logger.debug(
                    'AddonsRule: done: %s',
                    processed_crash.addons
                )

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

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.java_stack_trace = raw_crash.setdefault(
            'JavaStackTrace',
            None
        )

        return True


class OutOfMemoryBinaryRule(Rule):

    required_config = Namespace()
    required_config.add_option(
        'max_size_uncompressed',
        default=20 * 1024 * 1024,  # ~20 Mb
        doc=(
            "Number of bytes, max, that we accept memory info payloads "
            "as JSON."
        )

    )

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
            if len(memory_info_as_string) > self.config.max_size_uncompressed:
                error_message = (
                    "Uncompressed memory info too large %d (max: %d)" % (
                        len(memory_info_as_string),
                        self.config.max_size_uncompressed,
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
    """This rule rewrites the product name for products that fail to report
    a useful product name
    """

    PRODUCT_MAP = {
        "{aa3c5121-dab2-40e2-81ca-7ea25febc110}": "FennecAndroid",
    }

    def version(self):
        return '2.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
            return raw_crash.get('ProductID') in self.PRODUCT_MAP

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash['ProductName'] = self.PRODUCT_MAP.get(raw_crash['ProductID'])
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
    required_config = Namespace()
    required_config.add_option(
        'known_flash_identifiers',
        doc='A subset of the known "debug identifiers" for flash versions, '
        'associated to the version',
        default={
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
        },
        from_string_converter=ujson.loads
    )
    required_config.add_option(
        'flash_re',
        doc='a regular expression to match Flash file names',
        default=(
            r'NPSWF32_?(.*)\.dll|'
            'FlashPlayerPlugin_?(.*)\.exe|'
            'libflashplayer(.*)\.(.*)|'
            'Flash ?Player-?(.*)'
        ),
        from_string_converter=re.compile
    )

    def version(self):
        return '1.0'

    def _get_flash_version(self, **kwargs):
        """If (we recognize this module as Flash and figure out a version):
        Returns version; else (None or '')"""
        filename = kwargs.get('filename', None)
        version = kwargs.get('version', None)
        debug_id = kwargs.get('debug_id', None)
        m = self.config.flash_re.match(filename)
        if m:
            if version:
                return version
            # we didn't get a version passed into us
            # try do deduce it
            groups = m.groups()
            if groups[0]:
                return groups[0].replace('_', '.')
            if groups[1]:
                return groups[1].replace('_', '.')
            if groups[2]:
                return groups[2]
            if groups[4]:
                return groups[4]
            return self.config.known_flash_identifiers.get(
                debug_id,
                None
            )
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


class MissingSymbolsRule(Rule):
    required_config = Namespace()
    required_config.add_option(
        'database_class',
        doc="the class of the database",
        default='socorro.external.postgresql.connection_context.'
                'ConnectionContext',
        from_string_converter=str_to_python_object,
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=str_to_python_object,
        reference_value_from='resource.postgresql',
    )

    def __init__(self, config):
        super(MissingSymbolsRule, self).__init__(config)
        self.database = self.config.database_class(config)
        self.transaction = self.config.transaction_executor_class(
            config,
            self.database,
        )
        self.sql = (
            "INSERT INTO missing_symbols_%s"
            " (date_processed, debug_file, debug_id, code_file, code_id)"
            " VALUES (%%s, %%s, %%s, %%s, %%s)"
        )

    def version(self):
        return '1.0'

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            date = processed_crash['date_processed']
            # update partition information based on date processed
            sql = self.sql % datestring_to_weekly_partition(date)
            for module in processed_crash['json_dump']['modules']:
                try:
                    # First of all, only bother if there are
                    # missing_symbols in this module.
                    # And because it's not useful if either of debug_file
                    # or debug_id are empty, we filter on that here too.
                    if (
                        module['missing_symbols'] and
                        module['debug_file'] and
                        module['debug_id']
                    ):
                        self.transaction(
                            execute_no_results,
                            sql,
                            (
                                date,
                                module['debug_file'],
                                module['debug_id'],
                                # These two use .get() because the keys
                                # were added later in history. If it's
                                # non-existent (or existant and None), it
                                # will proceed and insert as a nullable.
                                module.get('filename'),
                                module.get('code_id'),
                            )
                        )
                except self.database.ProgrammingError:
                    processor_meta.processor_notes.append(
                        "WARNING: missing symbols rule failed for"
                        " %s" % raw_crash.uuid
                    )
                except KeyError:
                    pass
        except KeyError:
            return False
        return True


class BetaVersionRule(Rule):
    required_config = Namespace()
    required_config.add_option(
        'database_class',
        doc="the class of the database",
        default='socorro.external.postgresql.connection_context.'
                'ConnectionContext',
        from_string_converter=str_to_python_object,
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=str_to_python_object,
        reference_value_from='resource.postgresql',
    )

    def __init__(self, config):
        super(BetaVersionRule, self).__init__(config)
        database = config.database_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            database,
        )
        self._versions_data_cache = {}

    def version(self):
        return '1.0'

    def _get_version_data(self, product, version, build_id):
        """Return the real version number of a specific product, version and
        build.

        For example, beta builds of Firefox declare their version
        number as the major version (i.e. version 54.0b3 would say its version
        is 54.0). This database call returns the actual version number of said
        build (i.e. 54.0b3 for the previous example).
        """
        key = '%s:%s:%s' % (product, version, build_id)

        if key in self._versions_data_cache:
            return self._versions_data_cache[key]

        sql = """
            SELECT
                pv.version_string
            FROM product_versions pv
                LEFT JOIN product_version_builds pvb ON
                    (pv.product_version_id = pvb.product_version_id)
            WHERE pv.product_name = %(product)s
            AND pv.release_version = %(version)s
            AND pvb.build_id = %(build_id)s
        """
        params = {
            'product': product,
            'version': version,
            'build_id': build_id,
        }
        results = self.transaction(
            execute_query_fetchall,
            sql,
            params
        )
        for real_version, in results:
            self._versions_data_cache[key] = real_version

        return self._versions_data_cache.get(key)

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            # We apply this Rule only if the release channel is beta, because
            # beta versions are the only ones sending an "incorrect" version
            # number in their data.
            # 2017-06-14: Ohai! This is not true anymore! With the removal of
            # the aurora channel, there is now a new type of build called
            # "DevEdition", that is released on the aurora channel, but has
            # the same version naming logic as builds on the beta channel.
            # We thus want to apply the same logic to aurora builds
            # as well now. Note that older crash reports won't be affected,
            # because they have a "correct" version number, usually containing
            # the letter 'a' (like '50.0a2').
            return processed_crash['release_channel'].lower() in ('beta', 'aurora')
        except KeyError:
            # No release_channel.
            return False

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            # Sanitize the build id to avoid errors during the SQL query.
            try:
                build_id = int(processed_crash['build'])
            except ValueError:
                build_id = None

            real_version = self._get_version_data(
                processed_crash['product'],
                processed_crash['version'],
                build_id,
            )

            if real_version:
                processed_crash['version'] = real_version
            else:
                # This is a beta version but we do not have data about it. It
                # could be because we don't have it yet (if the cron jobs are
                # running late for example), so we mark this crash. This way,
                # we can reprocess it later to give it the correct version.
                processed_crash['version'] += 'b0'
                processor_meta.processor_notes.append(
                    'release channel is %s but no version data was found '
                    '- added "b0" suffix to version number' % (
                        processed_crash['release_channel'],
                    )
                )
        except KeyError:
            return False
        return True


class AuroraVersionFixitRule(Rule):
    """Starting with Firefox 55, we ditched the aurora channel and converted
    devedition to its own "product" that are respins of the beta channel
    builds. These builds still use "aurora" as the release channel.

    However, the devedition .0b1 and .0b2 releases need to be treated as an
    "aurora" for Firefox. Because this breaks the invariants of Socorro
    (channel and version don't match) as well as the laws of physics, we fix
    these crashes by hand using a processor rule until we have time to swap
    ftpscraper and all the stored procedures out for buildhub scraper.

    """

    # NOTE(willkg): We'll have to add a build id -> version every time a new one comes
    # out. Ugh.
    buildid_to_version = {
        '20170612224034': '55.0b1',
        '20170615070049': '55.0b2',
        '20170808170225': '56.0b1',
        '20170810180547': '56.0b2',
        '20170917031738': '57.0b1',
        '20170921191414': '57.0b2',
        '20171103003834': '58.0b1',
        '20171109154410': '58.0b2',
        '20180116202029': '59.0b1',
        '20180117222144': '59.0b2',
    }

    def version(self):
        return '1.0'

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return raw_crash.get('BuildID', '') in self.buildid_to_version

    def _action(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        real_version = self.buildid_to_version[raw_crash['BuildID']]
        processed_crash['version'] = real_version
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
            # DotDict raises a KeyError when things are missing
            sentry_dsn = None

        self.generator = SignatureGenerator(sentry_dsn=sentry_dsn)

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        # Generate a crash signature and capture the signature and notes
        ret = self.generator.generate(raw_crash, processed_crash)
        processed_crash['signature'] = ret['signature']
        processor_meta['processor_notes'].extend(ret['notes'])
        return True

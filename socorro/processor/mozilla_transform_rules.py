# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import time
import ujson
import re

from sys import maxint

from gzip import open as gzip_open
from ujson import loads as json_loads
from urllib import unquote_plus

from configman import Namespace
from configman.converters import (
    str_to_python_object,
)

from socorrolib.lib.ooid import dateFromOoid
from socorrolib.lib.transform_rules import Rule
from socorrolib.lib.datetimeutil import (
    UTC,
    datetimeFromISOdateString,
    datestring_to_weekly_partition
)
from socorrolib.lib.context_tools import temp_file_context

from socorro.external.postgresql.dbapi2_util import (
    execute_query_fetchall,
    execute_no_results
)


#==============================================================================
class ProductRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
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


#==============================================================================
class UserDataRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.url = raw_crash.get('URL', None)
        processed_crash.user_comments = raw_crash.get('Comments', None)
        processed_crash.email = raw_crash.get('Email', None)
        #processed_crash.user_id = raw_crash.get('UserID', '')
        processed_crash.user_id = ''

        return True


#==============================================================================
class EnvironmentRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.app_notes = raw_crash.get('Notes', '')

        return True


#==============================================================================
class PluginRule(Rule):   # Hangs are here

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
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


#==============================================================================
class AddonsRule(Rule):
    required_config = Namespace()
    required_config.add_option(
        'collect_addon',
        doc='boolean indictating if information about add-ons should be '
        'collected',
        default=True,
    )

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    @staticmethod
    def _addon_split_or_warn(addon_pair, processor_notes):
        addon_splits = addon_pair.split(':', 1)
        if len(addon_splits) == 1:
            processor_notes.append(
                'add-on "%s" is a bad name and/or version' %
                addon_pair
            )
            addon_splits.append('')
        return tuple(unquote_plus(x) for x in addon_splits)

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.addons_checked = None
        try:
            addons_checked_txt = raw_crash.EMCheckCompatibility.lower()
            processed_crash.addons_checked = False
            if addons_checked_txt == 'true':
                processed_crash.addons_checked = True
        except KeyError, e:
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
                    self._addon_split_or_warn(
                        x,
                        processor_meta.processor_notes
                    )
                    for x in original_addon_str.split(',')
                ]
            if self.config.chatty:
                self.config.logger.debug(
                    'AddonsRule: done: %s',
                    processed_crash.addons
                )

        return True


#==============================================================================
class DatesAndTimesRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
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
        except TypeError, x:
            notes_list.append(
                "WARNING: raw_crash[%s] contains unexpected value: %s; %s" %
                (key, a_mapping[key], str(x))
            )
            return default

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processor_notes = processor_meta.processor_notes

        processed_crash.submitted_timestamp = raw_crash.get(
            'submitted_timestamp',
            dateFromOoid(raw_crash.uuid)
        )
        if isinstance(processed_crash.submitted_timestamp, basestring):
            processed_crash.submitted_timestamp = datetimeFromISOdateString(
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


#==============================================================================
class JavaProcessRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):

        processed_crash.java_stack_trace = raw_crash.setdefault(
            'JavaStackTrace',
            None
        )

        return True


#==============================================================================
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

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return 'memory_report' in raw_dumps

    #--------------------------------------------------------------------------
    def _extract_memory_info(self, dump_pathname, processor_notes):
        """Extract and return the JSON data from the .json.gz memory report.
        file"""
        try:
            fd = gzip_open(dump_pathname, "rb")
        except IOError, x:
            error_message = "error in gzip for %s: %r" % (dump_pathname, x)
            processor_notes.append(error_message)
            return {"ERROR": error_message}
        try:
            memory_info_as_string = fd.read()
            if len(memory_info_as_string) > self.config.max_size_uncompressed:
                error_message = (
                    "Uncompressed memory info too large %d (max: %d)" % (
                        len(memory_info_as_string),
                        self.config.max_size_uncompressed,
                    )
                )
                processor_notes.append(error_message)
                return {"ERROR": error_message}

            memory_info = json_loads(memory_info_as_string)
        except ValueError, x:
            error_message = "error in json for %s: %r" % (dump_pathname, x)
            processor_notes.append(error_message)
            return {"ERROR": error_message}
        finally:
            fd.close()

        return memory_info

    #--------------------------------------------------------------------------
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


#--------------------------------------------------------------------------
def setup_product_id_map(config, local_config, args_unused):
    database_connection = local_config.database_class(local_config)
    transaction = local_config.transaction_executor_class(
        local_config,
        database_connection
    )
    sql = (
        "SELECT product_name, productid, rewrite FROM "
        "product_productid_map WHERE rewrite IS TRUE"
    )
    product_mappings = transaction(
        execute_query_fetchall,
        sql
    )
    product_id_map = {}
    for product_name, productid, rewrite in product_mappings:
        product_id_map[productid] = {
            'product_name': product_name,
            'rewrite': rewrite
        }
    return product_id_map


#==============================================================================
class ProductRewrite(Rule):
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

    required_config.add_aggregation(
        'product_id_map',
        setup_product_id_map
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(ProductRewrite, self).__init__(config)
        self.product_id_map = setup_product_id_map(
            config,
            config,
            None
        )

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            return raw_crash['ProductID'] in self.product_id_map
        except KeyError:
            # no ProductID
            return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            product_id = raw_crash['ProductID']
        except KeyError:
            self.config.logger.debug('ProductID not in json_doc')
            return False
        old_product_name = raw_crash['ProductName']
        new_product_name = (
            self.product_id_map[product_id]['product_name']
        )
        raw_crash['ProductName'] = new_product_name
        self.config.logger.debug(
            'product name changed from %s to %s based '
            'on productID %s',
            old_product_name,
            new_product_name,
            product_id
        )
        return True


#==============================================================================
class ESRVersionRewrite(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '2.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return raw_crash.get('ReleaseChannel', '') == 'esr'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            raw_crash['Version'] += 'esr'
        except KeyError:
            processor_meta.processor_notes.append(
                '"Version" missing from esr release raw_crash'
            )


#==============================================================================
class PluginContentURL(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '2.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            return bool(raw_crash['PluginContentURL'])
        except KeyError:
            return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash['URL'] = raw_crash['PluginContentURL']
        return True


#==============================================================================
class PluginUserComment(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '2.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            return bool(raw_crash['PluginUserComment'])
        except KeyError:
            return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash['Comments'] = raw_crash['PluginUserComment']
        return True


#==============================================================================
class ExploitablityRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
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


#==============================================================================
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

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.flash_version = ''
        flash_version = None
        for index, a_module in enumerate(
            processed_crash['json_dump']['modules']
        ):
            flash_version = self._get_flash_version(**a_module)
            if flash_version:
                break
        if flash_version:
            processed_crash.flash_version = flash_version
        else:
            processed_crash.flash_version = '[blank]'
        return True


#==============================================================================
class Winsock_LSPRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.Winsock_LSP = raw_crash.get('Winsock_LSP', None)


#==============================================================================
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

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash.topmost_filenames = None
        try:
            crashing_thread = (
                processed_crash.json_dump['crash_info']['crashing_thread']
            )
            stack_frames = (
                processed_crash.json_dump['threads'][crashing_thread]['frames']
            )
        except KeyError, x:
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


#==============================================================================
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

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
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


#==============================================================================
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

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(BetaVersionRule, self).__init__(config)
        database = config.database_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            database,
        )
        self._versions_data_cache = {}

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _get_version_data(self, product, version, release_channel, build_id):
        key = '%s:%s:%s:%s' % (product, version, release_channel, build_id)

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
            AND pv.build_type ILIKE %(release_channel)s
            AND pvb.build_id = %(build_id)s
        """
        params = {
            'product': product,
            'version': version,
            'release_channel': release_channel,
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

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        try:
            # We apply this Rule only if the release channel is beta, because
            # beta versions are the only ones sending an "incorrect" version
            # number in their data.
            return processed_crash['release_channel'].lower() == 'beta'
        except KeyError:
            # No release_channel.
            return False

    #--------------------------------------------------------------------------
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
                processed_crash['release_channel'],
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
                    'release channel is beta but no version data was found '
                    '- added "b0" suffix to version number'
                )
        except KeyError:
            return False
        return True


#==============================================================================
class FennecBetaError20150430(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return raw_crash['ProductName'].startswith('Fennec') and \
            raw_crash['BuildID'] == '20150427090529' and \
            raw_crash['ReleaseChannel'] == 'release'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        raw_crash['ReleaseChannel'] = 'beta'
        return True


#==============================================================================
class OSPrettyVersionRule(Rule):
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

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(OSPrettyVersionRule, self).__init__(config)
        database = config.database_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            database,
        )
        self._windows_versions = self._get_windows_versions()

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _get_windows_versions(self):
        sql = """
            SELECT windows_version_name, major_version, minor_version
            FROM windows_versions
        """
        results = self.transaction(
            execute_query_fetchall,
            sql,
        )
        versions = {}
        for (version, major, minor) in results:
            key = '%s.%s' % (major, minor)
            versions[key] = version

        return versions

    #--------------------------------------------------------------------------
    def _get_pretty_os_version(self, processed_crash):
        try:
            pretty_name = processed_crash['os_name']
        except KeyError:
            # There is nothing we can do if the `os_name` is missing.
            return None

        if not isinstance(processed_crash.os_name, basestring):
            # This data is bogus, there's nothing we can do.
            return None

        if not processed_crash.get('os_version'):
            # The version number is missing, there's nothing to do.
            return pretty_name

        version_split = processed_crash.os_version.split('.')

        if len(version_split) < 2:
            # The version number is invalid, there's nothing to do.
            return pretty_name

        major_version = int(version_split[0])
        minor_version = int(version_split[1])

        if processed_crash.os_name.lower().startswith('windows'):
            # Get corresponding Windows version.
            key = '%s.%s' % (major_version, minor_version)
            if key in self._windows_versions:
                pretty_name = self._windows_versions[key]
            else:
                pretty_name = 'Windows Unknown'

        elif processed_crash.os_name == 'Mac OS X':
            if (
                major_version >= 10 and
                major_version < 11 and
                minor_version >= 0 and
                minor_version < 20
            ):
                pretty_name = 'OS X %s.%s' % (major_version, minor_version)
            else:
                pretty_name = 'OS X Unknown'

        return pretty_name

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash['os_pretty_version'] = self._get_pretty_os_version(
            processed_crash
        )
        return True


#==============================================================================
class ThemePrettyNameRule(Rule):
    """The Firefox theme shows up commonly in crash reports referenced by its
    internal ID. The ID is not easy to change, and is referenced by id in other
    software.

    This rule attempts to modify it to have a more identifiable name, like
    other built-in extensions.

    Must be run after the Addons Rule."""

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(ThemePrettyNameRule, self).__init__(config)
        self.conversions = {
            "{972ce4c6-7e08-4474-a285-3208198ce6fd}":
                "{972ce4c6-7e08-4474-a285-3208198ce6fd} "
                "(default theme)",
        }

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        '''addons is a list of tuples containing (extension, version)'''
        addons = processed_crash.get('addons', [])

        for extension, version in addons:
            if extension in self.conversions:
                return True
        return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        addons = processed_crash.addons

        for index, (extension, version) in enumerate(addons):
            if extension in self.conversions:
                addons[index] = (self.conversions[extension], version)
        return True

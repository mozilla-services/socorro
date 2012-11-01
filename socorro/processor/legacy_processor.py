# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""this file defines the method of converting a raw crash into a processed
crash using the traditional algorithm used from 2008 through 2012."""

import re
import os
import subprocess
import datetime
import time
from urllib import unquote_plus

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from socorro.lib.datetimeutil import utc_now
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.database.transaction_executor import TransactionExecutor
from socorro.lib.transform_rules import TransformRuleSystem
from socorro.lib.datetimeutil import datetimeFromISOdateString, UTC
from socorro.lib.ooid import dateFromOoid
from socorro.lib.util import (
    DotDict,
    emptyFilter,
    StrCachingIterator
)


#------------------------------------------------------------------------------
def create_symbol_path_str(input_str):
    symbols_sans_commas = input_str.replace(',', ' ')
    quoted_symbols_list = ['"%s"' % x.strip()
                           for x in symbols_sans_commas.split()]
    return ' '.join(quoted_symbols_list)


#==============================================================================
class LegacyCrashProcessor(RequiredConfig):
    """this class is a refactoring of the original processor algorithm into
    a single class.  This class is suitble for use in the 'processor_app'
    introducted in 2012."""

    required_config = Namespace()
    required_config.add_option(
        'database_class',
        doc="the class of the database",
        default=ConnectionContext,
        from_string_converter=class_converter
    )
    required_config.add_option(
        'transaction_executor_class',
        default=TransactionExecutor,
        doc='a class that will manage transactions',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'stackwalk_command_line',
        doc='the template for the command to invoke minidump_stackwalk',
        default='$minidump_stackwalk_pathname -m $dumpfilePathname '
        '$processor_symbols_pathname_list 2>/dev/null',
    )
    required_config.add_option(
        'minidump_stackwalk_pathname',
        doc='the full pathname of the extern program minidump_stackwalk '
        '(quote path with embedded spaces)',
        default='/data/socorro/stackwalk/bin/minidump_stackwalk',
    )
    required_config.add_option(
        'symbol_cache_path',
        doc='the path where the symbol cache is found (quote path with '
        'embedded spaces)',
        default='/mnt/socorro/symbols',
    )
    required_config.add_option(
        'processor_symbols_pathname_list',
        doc='comma or space separated list of symbol files for '
        'minidump_stackwalk (quote paths with embedded spaces)',
        default='/mnt/socorro/symbols/symbols_ffx,'
        '/mnt/socorro/symbols/symbols_sea,'
        '/mnt/socorro/symbols/symbols_tbrd,'
        '/mnt/socorro/symbols/symbols_sbrd,'
        '/mnt/socorro/symbols/symbols_os',
        from_string_converter=create_symbol_path_str
    )
    required_config.add_option(
        'crashing_thread_frame_threshold',
        doc='the number of frames to keep in the raw dump for the '
        'crashing thread',
        default=100,
    )
    required_config.add_option(
        'crashing_thread_tail_frame_threshold',
        doc='the number of frames to keep in the raw dump at the tail of the '
        'frame list',
        default=10,
    )
    required_config.add_option(
        'temporary_file_system_storage_path',
        doc='a local filesystem path where processor can write dumps '
        'temporarily for processing',
        default='/home/socorro/temp',
    )
    required_config.namespace('c_signature')
    required_config.c_signature.add_option(
        'c_signature_tool_class',
        doc='the class that can generate a C signature',
        default='socorro.processor.signature_utilities.CSignatureTool',
        from_string_converter=class_converter
    )
    required_config.namespace('java_signature')
    required_config.java_signature.add_option(
        'java_signature_tool_class',
        doc='the class that can generate a Java signature',
        default='socorro.processor.signature_utilities.JavaSignatureTool',
        from_string_converter=class_converter
    )
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
        }
    )
    required_config.add_option(
        'collect_addon',
        doc='boolean indictating if information about add-ons should be '
            'collected',
        default=True,
    )
    required_config.add_option(
        'collect_crash_process',
        doc='boolean indictating if information about process type should be '
            'collected',
        default=True,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(LegacyCrashProcessor, self).__init__()
        self.config = config
        if quit_check_callback:
            self.quit_check = quit_check_callback
        else:
            self.quit_check = lambda: False
        self.database = self.config.database_class(config)
        self.transaction = \
            self.config.transaction_executor_class(
                config,
                self.database,
                quit_check_callback
            )

        self.raw_crash_transform_rule_system = TransformRuleSystem()
        self._load_transform_rules()

        # *** originally from the ExternalProcessor class
        #preprocess the breakpad_stackwalk command line
        strip_parens_re = re.compile(r'\$(\()(\w+)(\))')
        convert_to_python_substitution_format_re = re.compile(r'\$(\w+)')
        # Canonical form of $(param) is $param. Convert any that are needed
        tmp = strip_parens_re.sub(
            r'$\2',
            config.stackwalk_command_line
        )
        # Convert canonical $dumpfilePathname to DUMPFILEPATHNAME
        tmp = tmp.replace('$dumpfilePathname', 'DUMPFILEPATHNAME')
        # finally, convert any remaining $param to pythonic %(param)s
        tmp = convert_to_python_substitution_format_re.sub(r'%(\1)s', tmp)
        self.command_line = tmp % config
        # *** end from ExternalProcessor

        self.c_signature_tool = config.c_signature.c_signature_tool_class(
            config.c_signature
        )
        self.java_signature_tool = \
            config.java_signature.java_signature_tool_class(
                config.java_signature
            )

    #--------------------------------------------------------------------------
    def reject_raw_crash(self, crash_id, reason):
        self._log_job_start(crash_id)
        self.config.logger.warning('%s rejected: %s', crash_id, reason)
        self._log_job_end(utc_now(), False, crash_id)

    #--------------------------------------------------------------------------
    def convert_raw_crash_to_processed_crash(self, raw_crash, raw_dump):
        """ This function is run only by a worker thread.
            Given a job, fetch a thread local database connection and the json
            document.  Use these to create the record in the 'reports' table,
            then start the analysis of the dump file.

            input parameters:
        """
        try:
            self.quit_check()
            crash_id = raw_crash.uuid
            processor_notes = []
            processed_crash = DotDict()
            processed_crash.uuid = raw_crash.uuid
            processed_crash.success = False

            started_timestamp = self._log_job_start(crash_id)

            #self.config.logger.debug('about to apply rules')
            self.raw_crash_transform_rule_system.apply_all_rules(raw_crash,
                                                                 self)
            #self.config.logger.debug('done applying transform rules')

            try:
                submitted_timestamp = datetimeFromISOdateString(
                    raw_crash.submitted_timestamp
                )
            except KeyError:
                submitted_timestamp = dateFromOoid(crash_id)

            # formerly the call to 'insertReportIntoDatabase'
            processed_crash_update = self._create_basic_processed_crash(
                crash_id,
                raw_crash,
                submitted_timestamp,
                started_timestamp,
                processor_notes
            )
            processed_crash.update(processed_crash_update)

            temp_dump_pathname = self._get_temp_dump_pathname(
                crash_id,
                raw_dump
            )
            try:
                #logger.debug('about to doBreakpadStackDumpAnalysis')
                processed_crash_update_dict = \
                    self._do_breakpad_stack_dump_analysis(
                        crash_id,
                        temp_dump_pathname,
                        processed_crash.hang_type,
                        processed_crash.java_stack_trace,
                        submitted_timestamp,
                        processor_notes
                    )
                processed_crash.update(processed_crash_update_dict)
            finally:
                self._cleanup_temp_file(temp_dump_pathname)

            processed_crash.topmost_filenames = "|".join(
                processed_crash.get('topmost_filenames', [])
            )
            try:
                processed_crash.Winsock_LSP = raw_crash.Winsock_LSP
            except KeyError:
                pass  # if it's not in the original raw_crash,
                        # it does get into the jsonz

        #except (KeyboardInterrupt, SystemExit):
            #self.config.logger.info("quit request detected")
            #raise
        except Exception, x:
            self.config.logger.warning(
                'Error while processing %s: %s',
                crash_id,
                str(x),
                exc_info=True
            )
            processor_notes.append(str(x))

        processor_notes = '; '.join(processor_notes)
        processed_crash.processor_notes = processor_notes
        completed_datetime = utc_now()
        processed_crash.completeddatetime = completed_datetime
        self._log_job_end(
            completed_datetime,
            processed_crash.success,
            crash_id
        )

        return processed_crash

    #--------------------------------------------------------------------------
    def _create_basic_processed_crash(self,
                                      uuid,
                                      raw_crash,
                                      submitted_timestamp,
                                      started_timestamp,
                                      processor_notes):
        """
        This function is run only by a worker thread.
          Create the record for the current job in the 'reports' table
          input parameters:
            uuid: the unique id identifying the job - corresponds with the
                  uuid column in the 'jobs' and the 'reports' tables
            jsonDocument: an object with a dictionary interface for fetching
                          the components of the json document
            submitted_timestamp: when job came in (a key used in partitioning)
            processor_notes: list of strings of error messages
        """
        #logger.debug("starting insertReportIntoDatabase")
        processed_crash = DotDict()
        processed_crash.success = False
        processed_crash.uuid = uuid
        processed_crash.startedDateTime = started_timestamp
        processed_crash.product = self._get_truncate_or_warn(
            raw_crash,
            'ProductName',
            processor_notes,
            None,
            30
        )
        processed_crash.version = self._get_truncate_or_warn(
            raw_crash,
            'Version',
            processor_notes,
            None,
            16
        )
        processed_crash.build = self._get_truncate_or_warn(
            raw_crash,
            'BuildID',
            processor_notes,
            None,
            16
        )
        processed_crash.url = self._get_truncate_or_none(
            raw_crash,
            'URL',
            255
        )
        processed_crash.user_comments = self._get_truncate_or_none(
            raw_crash,
            'Comments',
            500
        )
        processed_crash.app_notes = self._get_truncate_or_none(
            raw_crash,
            'Notes',
            1000
        )
        processed_crash.distributor = self._get_truncate_or_none(
            raw_crash,
            'Distributor',
            20
        )
        processed_crash.distributor_version = self._get_truncate_or_none(
            raw_crash,
            'Distributor_version',
            20
        )
        processed_crash.email = self._get_truncate_or_none(
            raw_crash,
            'Email',
            100
        )
        processed_crash.process_type = self._get_truncate_or_none(
            raw_crash,
            'ProcessType',
            10
        )
        processed_crash.release_channel = raw_crash.get(
            'ReleaseChannel',
            'unknown'
        )
        # userId is now deprecated and replace with empty string
        processed_crash.user_id = ""

        # ++++++++++++++++++++
        # date transformations
        processed_crash.date_processed = submitted_timestamp

        # defaultCrashTime: must have crashed before date processed
        submitted_timestamp_as_epoch = int(
            time.mktime(submitted_timestamp.timetuple())
        )
        timestampTime = int(
            raw_crash.get('timestamp', submitted_timestamp_as_epoch)
            )  # the old name for crash time
        crash_time = int(
            self._get_truncate_or_warn(
                raw_crash,
                'CrashTime',
                processor_notes,
                timestampTime,
                10
            )
        )
        processed_crash.crash_time = crash_time
        if crash_time == submitted_timestamp_as_epoch:
            processor_notes.append(
                "WARNING: No 'client_crash_date' "
                "could be determined from the raw_crash"
            )
        # StartupTime: must have started up some time before crash
        startupTime = int(raw_crash.get('StartupTime', crash_time))
        # InstallTime: must have installed some time before startup
        installTime = int(raw_crash.get('InstallTime', startupTime))
        processed_crash.client_crash_date = datetime.datetime.fromtimestamp(
            crash_time,
            UTC
        )
        processed_crash.install_age = crash_time - installTime
        processed_crash.uptime = max(0, crash_time - startupTime)
        try:
            last_crash = int(raw_crash.SecondsSinceLastCrash)
        except:
            last_crash = None
        processed_crash.last_crash = last_crash

        # TODO: not sure how to reimplemnt this
        #if crash_id in self.priority_job_set:
            #processor_notes.append('Priority Job')
            #self.priority_job_set.remove(crash_id)

        # can't get report id because we don't have the database here
        #reportId = processed_crash["id"]
        processed_crash.dump = ''

        try:
            processed_crash.ReleaseChannel = \
                raw_crash.ReleaseChannel
        except KeyError:
            processed_crash.ReleaseChannel = 'unknown'

        if self.config.collect_addon:
            #logger.debug("collecting Addons")
            # formerly 'insertAdddonsIntoDatabase'
            addons_as_a_list_of_tuples = self._process_list_of_addons(
                raw_crash,
                processor_notes
            )
            processed_crash.addons = addons_as_a_list_of_tuples

        if self.config.collect_crash_process:
            #logger.debug("collecting Crash Process")
            # formerly insertCrashProcess
            processed_crash.update(
                self._add_process_type_to_processed_crash(raw_crash)
            )

        processed_crash.addons_checked = None
        try:
            addons_checked_txt = raw_crash.EMCheckCompatibility.lower()
            processed_crash.addons_checked = False
            if addons_checked_txt == 'true':
                processed_crash.addons_checked = True
        except KeyError:
            pass  # leaving it as None if not in the document

        if int(raw_crash.get('PluginHang', False)):
            processed_crash.hangid = 'fake-' + uuid
        else:
            processed_crash.hangid = raw_crash.get('HangID', None)

        if int(raw_crash.get('Hang', False)):
            processed_crash.hang_type = 1
        elif int(raw_crash.get('PluginHang', False)):
            processed_crash.hang_type = -1
        elif processed_crash.hangid:
            processed_crash.hang_type = -1
        else:
            processed_crash.hang_type = 0

        processed_crash.java_stack_trace = \
            raw_crash.setdefault('JavaStackTrace', None)

        return processed_crash

    #--------------------------------------------------------------------------
    @staticmethod
    def _addon_split_or_warn(addon_pair, processor_notes):
        addon_splits = addon_pair.split(':', 1)
        if len(addon_splits) == 1:
            processor_notes.append(
                '"%s" is deficient as a name and version for an addon' %
                addon_pair
            )
            addon_splits.append('')
        return tuple(unquote_plus(x) for x in addon_splits)

    #--------------------------------------------------------------------------
    def _process_list_of_addons(self, raw_crash,
                                processor_notes):
        original_addon_str = self._get_truncate_or_warn(
            raw_crash,
            'Add-ons',
            processor_notes,
            ""
        )
        if not original_addon_str:
            return []
        addon_list = [
            self._addon_split_or_warn(x, processor_notes)
            for x in original_addon_str.split(',')
        ]
        return addon_list

    #--------------------------------------------------------------------------
    def _add_process_type_to_processed_crash(self, raw_crash):
        """ Electrolysis Support - Optional - raw_crash may contain a
        ProcessType of plugin. In the future this value would be default,
        content, maybe even Jetpack... This indicates which process was the
        crashing process.
        """
        process_type_additions_dict = DotDict()
        process_type = self._get_truncate_or_none(raw_crash,
                                                  'ProcessType',
                                                  10)
        if not process_type:
            return process_type_additions_dict
        process_type_additions_dict.process_type = process_type

        #logger.debug('processType %s', processType)
        if process_type == 'plugin':
            # Bug#543776 We actually will are relaxing the non-null policy...
            # a null filename, name, and version is OK. We'll use empty strings
            process_type_additions_dict.PluginFilename = (
                raw_crash.get('PluginFilename', '')
            )
            process_type_additions_dict.PluginName = (
                raw_crash.get('PluginName', '')
            )
            process_type_additions_dict.PluginVersion = (
                raw_crash.get('PluginVersion', '')
            )

        return process_type_additions_dict

    #--------------------------------------------------------------------------
    def _invoke_minidump_stackwalk(self, dump_pathname):
        """ This function invokes breakpad_stackdump as an external process
        capturing and returning the text output of stdout.  This version
        represses the stderr output.

              input parameters:
                dump_pathname: the complete pathname of the dumpfile to be
                                  analyzed
        """
        command_line = self.command_line.replace("DUMPFILEPATHNAME",
                                                 dump_pathname)
        subprocess_handle = subprocess.Popen(
            command_line,
            shell=True,
            stdout=subprocess.PIPE
        )
        return (StrCachingIterator(subprocess_handle.stdout),
                subprocess_handle)

    #--------------------------------------------------------------------------
    def _do_breakpad_stack_dump_analysis(self, crash_id, dump_pathname,
                                         is_hang, java_stack_trace,
                                         submitted_timestamp,
                                         processor_notes):
        """ This function coordinates the steps of running the
        breakpad_stackdump process and analyzing the textual output for
        insertion into the database.

        returns:
          truncated - boolean: True - due to excessive length the frames of
                                      the crashing thread have been truncated.

        input parameters:
          crash_id - the unique string identifier for the crash report
          dump_pathname - the complete pathname for the =crash dump file
          is_hang - boolean, is this a hang crash?
          java_stack_trace - a source for java signatures info
          submitted_timestamp
          processor_notes
        """
        dump_analysis_line_iterator, subprocess_handle = \
            self._invoke_minidump_stackwalk(dump_pathname)
        dump_analysis_line_iterator.secondaryCacheMaximumSize = \
            self.config.crashing_thread_tail_frame_threshold + 1
        try:
            processed_crash_update = self._analyze_header(
                crash_id,
                dump_analysis_line_iterator,
                submitted_timestamp,
                processor_notes
            )
            crashed_thread = processed_crash_update.crashedThread
            try:
                make_modules_lowercase = \
                    processed_crash_update.os_name in ('Windows NT')
            except (KeyError, TypeError):
                make_modules_lowercase = True
            processed_crash_from_frames = self._analyze_frames(
                is_hang,
                java_stack_trace,
                make_modules_lowercase,
                dump_analysis_line_iterator,
                submitted_timestamp,
                crashed_thread,
                processor_notes
            )
            processed_crash_update.update(processed_crash_from_frames)
            for x in dump_analysis_line_iterator:
                pass  # need to spool out the rest of the stream so the
                        # cache doesn't get truncated
            pipe_dump_str = ('\n'.join(dump_analysis_line_iterator.cache))
            processed_crash_update.dump = pipe_dump_str
        finally:
            # this is really a handle to a file-like object - got to close it
            dump_analysis_line_iterator.theIterator.close()
        return_code = subprocess_handle.wait()
        if return_code is not None and return_code != 0:
            processor_notes.append(
                "%s failed with return code %s when processing dump %s" %
                (self.config.minidump_stackwalk_pathname,
                 subprocess_handle.returncode, crash_id)
            )
            processed_crash_update.success = False
            if processed_crash_update.signature.startswith("EMPTY"):
                processed_crash_update.signature += "; corrupt dump"
        return processed_crash_update

    #--------------------------------------------------------------------------
    def _analyze_header(self, crash_id, dump_analysis_line_iterator,
                        submitted_timestamp, processor_notes):
        """ Scan through the lines of the dump header:
            - extract data to update the record for this crash in 'reports',
              including the id of the crashing thread
            Returns: Dictionary of the various values that were updated in
                     the database
            Input parameters:
            - dump_analysis_line_iterator - an iterator object that feeds lines
                                            from crash dump data
            - submitted_timestamp
            - processor_notes
        """
        crashed_thread = None
        processed_crash_update = DotDict()
        # minimal update requirements
        processed_crash_update.success = True
        processed_crash_update.os_name = None
        processed_crash_update.os_version = None
        processed_crash_update.cpu_name = None
        processed_crash_update.cpu_info = None
        processed_crash_update.reason = None
        processed_crash_update.address = None

        header_lines_were_found = False
        flash_version = None
        for line in dump_analysis_line_iterator:
            line = line.strip()
            # empty line separates header data from thread data
            if line == '':
                break
            header_lines_were_found = True
            values = map(lambda x: x.strip(), line.split('|'))
            if len(values) < 3:
                processor_notes.append('Cannot parse header line "%s"'
                                       % line)
                continue
            values = map(emptyFilter, values)
            if values[0] == 'OS':
                name = self._truncate_or_none(values[1], 100)
                version = self._truncate_or_none(values[2], 100)
                processed_crash_update.os_name = name
                processed_crash_update.os_version = version
            elif values[0] == 'CPU':
                processed_crash_update.cpu_name = \
                    self._truncate_or_none(values[1], 100)
                processed_crash_update.cpu_info = \
                    self._truncate_or_none(values[2], 100)
                try:
                    processed_crash_update.cpu_info = ('%s | %s' % (
                      processed_crash_update.cpu_info,
                      self._get_truncate_or_none(values[3], 100)
                    ))
                except IndexError:
                    pass
            elif values[0] == 'Crash':
                processed_crash_update.reason = \
                    self._truncate_or_none(values[1], 255)
                try:
                    processed_crash_update.address = \
                        self._truncate_or_none(values[2], 20)
                except IndexError:
                    processed_crash_update.address = None
                try:
                    crashed_thread = int(values[3])
                except Exception:
                    crashed_thread = None
            elif values[0] == 'Module':
                # grab only the flash version, which is not quite as easy as
                # it looks
                if not flash_version:
                    flash_version = self._get_flash_version(values)
        if not header_lines_were_found:
            message = "%s returned no header lines for crash_id: %s" % \
                (self.config.minidump_stackwalk_pathname, crash_id)
            processor_notes.append(message)
            #self.config.logger.warning("%s", message)

        if crashed_thread is None:
            message = "No thread was identified as the cause of the crash"
            processor_notes.append(message)
            self.config.logger.info("%s", message)
        processed_crash_update.crashedThread = crashed_thread
        if not flash_version:
            flash_version = '[blank]'
        processed_crash_update.flash_version = flash_version
        #self.config.logger.debug(
        #  " updated values  %s",
        #  processed_crash_update
        #)
        return processed_crash_update

    #--------------------------------------------------------------------------
    flash_re = re.compile(r'NPSWF32_?(.*)\.dll|'
                          'FlashPlayerPlugin_?(.*)\.exe|'
                          'libflashplayer(.*)\.(.*)|'
                          'Flash ?Player-?(.*)')

    #--------------------------------------------------------------------------
    def _get_flash_version(self, moduleData):
        """If (we recognize this module as Flash and figure out a version):
        Returns version; else (None or '')"""
        try:
            module, filename, version, debugFilename, debugId = moduleData[:5]
        except ValueError:
            self.config.logger.debug("bad module line %s", moduleData)
            return None
        m = self.flash_re.match(filename)
        if m:
            if not version:
                groups = m.groups()
                if groups[0]:
                    version = groups[0].replace('_', '.')
                elif groups[1]:
                    version = groups[1].replace('_', '.')
                elif groups[2]:
                    version = groups[2]
                elif groups[4]:
                    version = groups[4]
                elif 'knownFlashDebugIdentifiers' in self.config:
                    version = (
                        self.config.knownFlashDebugIdentifiers
                        .get(debugId)
                    )
        else:
            version = None
        return version

    #--------------------------------------------------------------------------
    def _analyze_frames(self, hang_type, java_stack_trace,
                        make_modules_lower_case,
                        dump_analysis_line_iterator, submitted_timestamp,
                        crashed_thread,
                        processor_notes):
        """ After the header information, the dump file consists of just frame
        information.  This function cycles through the frame information
        looking for frames associated with the crashed thread (determined in
        analyzeHeader).  Each frame from that thread is written to the database
        until it has found a maximum of ten frames.

               returns:
                 a dictionary will various values to be used to update report
                 in the database, including:
                   truncated - boolean: True - due to excessive length the
                                               frames of the crashing thread
                                               may have been truncated.
                   signature - string: an overall signature calculated for this
                                       crash
                   processor_notes - string: any errors or warnings that
                                             happened during the processing

               input parameters:
                 hang_type -  0: if this is not a hang
                            -1: if "HangID" present in json,
                                   but "Hang" was not present
                            "Hang" value: if "Hang" present - probably 1
                 java_stack_trace - a source for java lang signature
                                    information
                 make_modules_lower_case - boolean, should modules be forced to
                                    lower case for signature generation?
                 dump_analysis_line_iterator - an iterator that cycles through
                                            lines from the crash dump
                 submitted_timestamp
                 crashed_thread - the number of the thread that crashed - we
                                 want frames only from the crashed thread
                 processor_notes
        """
        #logger.info("analyzeFrames")
        frame_counter = 0
        is_truncated = False
        frame_lines_were_found = False
        signature_generation_frames = []
        topmost_sourcefiles = []
        if hang_type == 1:
            thread_for_signature = 0
        else:
            thread_for_signature = crashed_thread
        max_topmost_sourcefiles = 1  # Bug 519703 calls for just one.
                                        # Lets build in some flex
        for line in dump_analysis_line_iterator:
            frame_lines_were_found = True
            #logger.debug("  %s", line)
            line = line.strip()
            if line == '':
                processor_notes.append("An unexpected blank line in "
                                       "this dump was ignored")
                continue  # ignore unexpected blank lines
            (thread_num, frame_num, module_name, function, source, source_line,
             instruction) = [emptyFilter(x) for x in line.split("|")]
            if len(topmost_sourcefiles) < max_topmost_sourcefiles and source:
                topmost_sourcefiles.append(source)
            if thread_for_signature == int(thread_num):
                if frame_counter < 30:
                    if make_modules_lower_case:
                        try:
                            module_name = module_name.lower()
                        except AttributeError:
                            pass
                    this_frame_signature = \
                        self.c_signature_tool.normalize_signature(
                            module_name,
                            function,
                            source,
                            source_line,
                            instruction
                        )
                    signature_generation_frames.append(this_frame_signature)
                if (
                    frame_counter ==
                    self.config.crashing_thread_frame_threshold
                    ):
                    processor_notes.append(
                        "This dump is too long and has triggered the automatic"
                        " truncation routine"
                    )
                    dump_analysis_line_iterator.useSecondaryCache()
                    is_truncated = True
                frame_counter += 1
            elif frame_counter:
                break
        dump_analysis_line_iterator.stopUsingSecondaryCache()
        signature = self._generate_signature(signature_generation_frames,
                                             java_stack_trace,
                                             hang_type,
                                             crashed_thread,
                                             processor_notes)
        if not frame_lines_were_found:
            message = "No frame data available"
            processor_notes.append(message)
            self.config.logger.info("%s", message)
        return DotDict({
            "signature": signature,
            "truncated": is_truncated,
            "topmost_filenames": topmost_sourcefiles,
        })

    #--------------------------------------------------------------------------
    def _generate_signature(self,
                            signature_list,
                            java_stack_trace,
                            hang_type,
                            crashed_thread,
                            processor_notes_list,
                            signature_max_len=255):
        if java_stack_trace:
            # generate a Java signature
            signature, signature_notes = self.java_signature_tool.generate(
                java_stack_trace,
                delimiter=' '
            )
            return signature
        else:
            # generate a C signature
            signature, signature_notes = self.c_signature_tool.generate(
                signature_list,
                hang_type,
                crashed_thread
            )
        if signature_notes:
            processor_notes_list.extend(signature_notes)

        return signature

    #--------------------------------------------------------------------------
    def _load_transform_rules(self):
        sql = (
            "select predicate, predicate_args, predicate_kwargs, "
            "       action, action_args, action_kwargs "
            "from transform_rules "
            "where "
            "  category = 'processor.json_rewrite'"
        )
        try:
            rules = self.transaction(
                execute_query_fetchall,
                sql
            )
        except Exception:
            self.config.logger.info(
                'Unable to load trasform rules from the database, falling back'
                ' to defaults',
                exc_info=True
            )
            rules = []
            #rules = [
                #(  # Version rewrite rule
                ## predicate function
                #'socorro.processor.transform_rules.equal_predicate',
                ## predicate function args
                #'',
                ## predicate function kwargs
                #'key="ReleaseChannel", value="esr"',
                ## action function
                #'socorro.processor.transform_rules.reformat_action',
                ## action function args
                #'',
                ## action function kwargs
                #'key="Version", format_str="%(Version)sesr"'
                #),
                #(  # Product rewrite rule
                #'socorro.processor.transform_rules.'
                    #'raw_crash_ProductID_predicate',
                #'',
                #'',
                #'socorro.processor.transform_rules.'
                    #'raw_crash_Product_rewrite_action',
                #'',
                #''
                #)
            #]

        self.raw_crash_transform_rule_system.load_rules(rules)
        self.config.logger.info(
            'done loading rules: %s',
            str(self.raw_crash_transform_rule_system.rules)
        )

    #--------------------------------------------------------------------------
    def _get_temp_dump_pathname(self, crash_id, raw_dump):
        base_path = self.config.temporary_file_system_storage_path
        dump_path = ("%s/%s.dump" % (base_path, crash_id)).replace('//', '/')
        with open(dump_path, "w") as f:
            f.write(raw_dump)
        return dump_path

    #--------------------------------------------------------------------------
    def _cleanup_temp_file(self, pathname):
        try:
            os.unlink(pathname)
        except IOError:
            self.config.logger.warning(
                'unable to delete %s. manual deletion is required.',
                pathname,
                exc_info=True
            )

    #--------------------------------------------------------------------------
    def __call__(self, raw_crash, raw_dump):
        self.convert_raw_crash_to_processed_crash(raw_crash, raw_dump)

    #--------------------------------------------------------------------------
    def _log_job_start(self, crash_id):
        self.config.logger.info("starting job: %s", crash_id)
        started_datetime = utc_now()
        self.transaction(
            execute_no_results,
            "update jobs set starteddatetime = %s where uuid = %s",
            (started_datetime, crash_id)
        )
        return started_datetime

    #--------------------------------------------------------------------------
    def _log_job_end(self, completed_datetime, success, crash_id):
        self.config.logger.info(
            "finishing %s job: %s",
            'successful' if success else 'failed',
            crash_id
        )
        # old behavior - processors just mark jobs in the postgres queue as
        # being done.  This is deprecated in favor of the processor cleaning
        # up after itself.
        #self.transaction(
            #execute_no_results,
            #"update jobs set completeddatetime = %s, success = %s "
            #"where uuid = %s",
            #(completed_datetime, success, crash_id)
        #)

        # new behavior - the processors delete completed jobs from the queue
        self.transaction(
            execute_no_results,
            "delete from jobs "
            "where uuid = %s",
            (crash_id,)
        )

    #--------------------------------------------------------------------------
    @staticmethod
    def _get_truncate_or_warn(a_mapping, key, notes_list,
                              default=None, max_length=10000):
        try:
            return a_mapping[key][:max_length]
        except KeyError:
            notes_list.append("WARNING: raw_crash missing %s" % key)
            return default
        except TypeError, x:
            notes_list.append(
                "WARNING: raw_crash [%s] contains unexpected value: %s" %
                (key, str(x))
            )
            return default

    #--------------------------------------------------------------------------
    @staticmethod
    def _get_truncate_or_none(a_mapping, key, maxLength=10000):
        try:
            return a_mapping[key][:maxLength]
        except (KeyError, IndexError, TypeError):
            return None

    #--------------------------------------------------------------------------
    @staticmethod
    def _truncate_or_none(a_string, maxLength=10000):
        try:
            return a_string[:maxLength]
        except TypeError:
            return None

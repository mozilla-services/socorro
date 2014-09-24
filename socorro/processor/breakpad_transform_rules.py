import re
import os
import subprocess
import threading
import ujson

from contextlib import contextmanager, closing
from collections import Mapping

from configman import Namespace

from socorro.lib.util import DotDict
from socorro.lib.transform_rules import Rule


#------------------------------------------------------------------------------
def _create_symbol_path_str(input_str):
    symbols_sans_commas = input_str.replace(',', ' ')
    quoted_symbols_list = ['"%s"' % x.strip()
                           for x in symbols_sans_commas.split()]
    return ' '.join(quoted_symbols_list)


#==============================================================================
class BreakpadStackwalkerRule(Rule):

    required_config = Namespace()
    required_config.add_option(
        'dump_field',
        doc='the default name of a dump',
        default='upload_file_minidump',
    )
    required_config.add_option(
        'stackwalk_command_line',
        doc='the template for the command to invoke stackwalker',
        default=(
            'timeout -s KILL 30 $minidump_stackwalk_pathname '
            '--raw-json $rawfilePathname $dumpfilePathname '
            '$processor_symbols_pathname_list 2>/dev/null'
        ),
    )
    required_config.add_option(
        'minidump_stackwalk_pathname',
        doc='the full pathname to the external program stackwalker '
        '(quote path with embedded spaces)',
        default='/data/socorro/stackwalk/bin/stackwalker',
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
        from_string_converter=_create_symbol_path_str
    )
    required_config.add_option(
        'temporary_file_system_storage_path',
        doc='a path where temporary files may be written',
        default='/tmp',
    )


    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(BreakpadStackwalkerRule, self).__init__(config)
        # the code in this section originally hales from 2008 ExternalProcessor
        # class.  It defines the template subsitution syntax used to spcecify
        # the shell command used to invoke the minidump stackwalker program.
        # The syntax was was requested to be of a Perl/shell style rather than
        # the original Pythonic syntax.  This code takes that foreign syntax
        # and converts it to a Pythonic syntax for later use.
        strip_parens_re = re.compile(r'\$(\()(\w+)(\))')
        convert_to_python_substitution_format_re = re.compile(r'\$(\w+)')

        # Canonical form of $(param) is $param. Convert any that are needed
        tmp = strip_parens_re.sub(
            r'$\2',
            config.stackwalk_command_line
        )
        # Convert canonical $dumpfilePathname and $rawfilePathname
        tmp = tmp.replace('$dumpfilePathname', 'DUMPFILEPATHNAME')
        tmp = tmp.replace('$rawfilePathname', 'RAWFILEPATHNAME')
        # finally, convert any remaining $param to pythonic %(param)s
        tmp = convert_to_python_substitution_format_re.sub(r'%(\1)s', tmp)
        self.mdsw_command_line = tmp % config

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    @contextmanager
    def _temp_raw_crash_json_file(self, raw_crash, crash_id):
        file_pathname = os.path.join(
            self.config.temporary_file_system_storage_path,
            "%s.%s.TEMPORARY.json" % (
                crash_id,
                threading.currentThread().getName()
            )
        )
        with open(file_pathname, "w") as f:
            ujson.dump(dict(raw_crash), f)
        try:
            yield file_pathname
        finally:
            os.unlink(file_pathname)

    #--------------------------------------------------------------------------
    @contextmanager
    def _temp_file_context(self, raw_dump_path):
        """this contextmanager implements conditionally deleting a pathname
        at the end of a context if the pathname indicates that it is a temp
        file by having the word 'TEMPORARY' embedded in it."""
        try:
            yield raw_dump_path
        finally:
            if 'TEMPORARY' in raw_dump_path:
                try:
                    os.unlink(raw_dump_path)
                except OSError:
                    self.config.logger.warning(
                        'unable to delete %s. manual deletion is required.',
                        raw_dump_path,
                        exc_info=True
                    )

    #--------------------------------------------------------------------------
    def _invoke_minidump_stackwalk(
        self,
        dump_name,
        dump_pathname,
        raw_crash_pathname,
        processor_notes
    ):
        """ This function invokes breakpad_stackdump as an external process
        capturing and returning the text output of stdout.  This version
        represses the stderr output.

              input parameters:
                dump_pathname: the complete pathname of the dumpfile to be
                                  analyzed
        """
        with self._temp_file_context(dump_pathname):
            command_line = self.mdsw_command_line.replace(
                "DUMPFILEPATHNAME",
                dump_pathname
            ).replace(
                "RAWFILEPATHNAME",
                raw_crash_pathname
            )

            if self.config.chatty:
                self.config.logger.debug(
                    "BreakpadStackwalkerRule: %s",
                    command_line
                )
            subprocess_handle = subprocess.Popen(
                command_line,
                shell=True,
                stdout=subprocess.PIPE
            )
            with closing(subprocess_handle.stdout):
                try:
                    stackwalker_output = ujson.load(subprocess_handle.stdout)
                except Exception, x:
                    processor_notes.append(
                        "MDSW output failed in json: %s" % x
                    )
                    stackwalker_output = {}

            return_code = subprocess_handle.wait()

        if not isinstance(stackwalker_output, Mapping):
            processor_notes.append(
                "MDSW produced unexpected output: %s..." %
                str(stackwalker_output)[:10]
            )
            stackwalker_output = {}

        stackwalker_data = DotDict()

        stackwalker_data.json_dump = stackwalker_output
        stackwalker_data.mdsw_return_code = return_code

        stackwalker_data.mdsw_status_string = stackwalker_output.get(
            'status',
            'unknown error'
        )
        stackwalker_data.success = stackwalker_data.mdsw_status_string == 'OK'

        if return_code == 124:
            processor_notes.append(
                "MDSW terminated with SIGKILL due to timeout"
            )
        elif return_code != 0 or not stackwalker_data.success:
            processor_notes.append(
                "MDSW failed on '%s': %s" % (
                    dump_name,
                    stackwalker_data.mdsw_status_string
                )
            )

        return stackwalker_data

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        if 'additional_minidumps' not in processed_crash:
            processed_crash.additional_minidumps = []
        with self._temp_raw_crash_json_file(
            raw_crash,
            raw_crash.uuid
        ) as raw_crash_pathname:
            for dump_name, dump_pathname in raw_dumps.iteritems():

                if processor_meta.quit_check:
                    processor_meta.quit_check()

                # this rule is only interested in dumps targeted for the
                # minidump stackwalker external program.  As of the writing
                # of this code, there is one other dump type.  The only way
                # to differentiate these dump types is by the name of the
                # dump.  All minidumps targeted for the stackwalker will have
                # a name with a prefix specified in configuration:
                if not dump_name.startswith(self.config.dump_field):
                    # dumps not intended for the stackwalker are ignored
                    continue

                if self.config.chatty:
                    self.config.logger.debug(
                        "BreakpadStackwalkerRule: %s, %s",
                        dump_name,
                        dump_pathname
                    )

                stackwalker_data = self._invoke_minidump_stackwalk(
                    dump_name,
                    dump_pathname,
                    raw_crash_pathname,
                    processor_meta.processor_notes
                )

                if dump_name == self.config.dump_field:
                    processed_crash.update(stackwalker_data)
                else:
                    processed_crash.additional_minidumps.append(dump_name)
                    processed_crash[dump_name] = stackwalker_data

        return True


#==============================================================================
class CrashingThreadRule(Rule):

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        try:
            processed_crash.crashedThread = (
                processed_crash['json_dump']['crash_info']['crashing_thread']
            )
        except KeyError:
            processed_crash.crashedThread = None
            processor_meta.processor_notes.append(
                'MDSW did not identify the crashing thread'
            )

        try:
            processed_crash.truncated = (
                processed_crash['json_dump']
                ['crashing_thread']['frames_truncated']
            )
        except KeyError:
            processed_crash.truncated = False

        try:
            processed_crash.address = (
                processed_crash['json_dump']
                ['crash_info']['address']
            )
        except KeyError:
            processed_crash.address = None

        try:
            processed_crash.reason = (
                processed_crash['json_dump']
                ['crash_info']['type']
            )
        except KeyError:
            processed_crash.reason = None

        return True




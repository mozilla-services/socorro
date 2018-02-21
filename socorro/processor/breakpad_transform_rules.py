import os
import subprocess
import threading
import ujson
import tempfile

from contextlib import contextmanager, closing
from collections import Mapping

from configman import Namespace
from configman.converters import str_to_list
from configman.dotdict import DotDict as ConfigmanDotDict

from socorro.lib.converters import change_default

from socorro.lib.util import DotDict
from socorro.lib.transform_rules import Rule


class CrashingThreadRule(Rule):

    def version(self):
        return '1.0'

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


class ExternalProcessRule(Rule):

    required_config = Namespace()
    required_config.add_option(
        'dump_field',
        doc='the default name of a dump',
        default='upload_file_minidump',
    )
    required_config.add_option(
        'command_line',
        doc=(
            'the template for the command to invoke the external program; uses Python format '
            'syntax'
        ),
        default=(
            'timeout -s KILL 30 {command_pathname} 2>/dev/null'
        ),
    )
    required_config.add_option(
        'command_pathname',
        doc='the full pathname to the external program to run '
        '(quote path with embedded spaces)',
        default='/data/socorro/stackwalk/bin/dumplookup',
    )
    required_config.add_option(
        'result_key',
        doc='the key where the external process result should be stored '
            'in the processed crash',
        default='%s_result' %
            required_config.command_pathname.default.split('/')[-1]
            .replace('-', ''),
    )
    required_config.add_option(
        'return_code_key',
        doc='the key where the external process return code should be stored '
            'in the processed crash',
        default='%s_return_code' %
            required_config.command_pathname.default.split('/')[-1],
    )

    def __init__(self, config):
        super(ExternalProcessRule, self).__init__(config)

    def version(self):
        return '1.0'

    def _interpret_external_command_output(self, fp, processor_meta):
        try:
            return ujson.load(fp)
        except Exception as x:
            processor_meta.processor_notes.append(
                "%s output failed in json: %s" % (
                    self.config.command_pathname,
                    x
                )
            )
            return {}

    def _execute_external_process(self, command_line, processor_meta):
        subprocess_handle = subprocess.Popen(
            command_line,
            shell=True,
            stdout=subprocess.PIPE
        )
        with closing(subprocess_handle.stdout):
            external_command_output = self._interpret_external_command_output(
                subprocess_handle.stdout,
                processor_meta
            )

        return_code = subprocess_handle.wait()
        return external_command_output, return_code

    @staticmethod
    def dot_save(a_mapping, key, value):
        if '.' not in key or isinstance(a_mapping, ConfigmanDotDict):
            a_mapping[key] = value
            return
        current_mapping = a_mapping
        key_parts = key.split('.')
        for key_fragment in key_parts[:-1]:
            try:
                current_mapping = current_mapping[key_fragment]
            except KeyError:
                current_mapping[key_fragment] = {}
                current_mapping = current_mapping[key_fragment]
        current_mapping[key_parts[-1]] = value

    def _save_results(
        self,
        external_command_output,
        return_code,
        raw_crash,
        processed_crash,
        processor_meta
    ):
        self.dot_save(
            processed_crash,
            self.config.result_key,
            external_command_output
        )
        self.dot_save(
            processed_crash,
            self.config.return_code_key,
            return_code
        )

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        command_parameters = dict(self.config)
        command_parameters['dump_file_pathname'] = raw_dumps[
            self.config['dump_field']
        ]
        command_line = self.config.command_line.format(**command_parameters)

        external_command_output, external_process_return_code = \
            self._execute_external_process(command_line, processor_meta)

        self._save_results(
            external_command_output,
            external_process_return_code,
            raw_crash,
            processed_crash,
            processor_meta
        )
        return True


class BreakpadStackwalkerRule2015(ExternalProcessRule):
    """Executes the minidump stackwalker external process and puts output in processed crash"""
    required_config = Namespace()
    required_config.add_option(
        name='symbols_urls',
        doc='comma delimited ordered list of urls for symbol lookup',
        default='https://localhost',
        from_string_converter=str_to_list,
        likely_to_be_changed=True
    )
    required_config.command_line = change_default(
        ExternalProcessRule,
        'command_line',
        'timeout -s KILL {kill_timeout} {command_pathname} '
        '--raw-json {raw_crash_pathname} '
        '{symbols_urls} '
        '--symbols-cache {symbol_cache_path} '
        '--symbols-tmp {symbol_tmp_path} '
        '{dump_file_pathname} '
        '2> /dev/null'
    )
    required_config.command_pathname = change_default(
        ExternalProcessRule,
        'command_pathname',
        # NOTE(willkg): This is the path for the RPM-based Socorro deploy. When
        # we switch to Docker, we should change this.
        '/data/socorro/stackwalk/bin/stackwalker',
    )
    required_config.add_option(
        'kill_timeout',
        doc='amount of time to let mdsw run before declaring it hung',
        default=600
    )
    required_config.add_option(
        'symbol_tmp_path',
        doc=(
            'directory to use as temp space for downloading symbols--must be on '
            'the same filesystem as symbols-cache'
        ),
        default=os.path.join(tempfile.gettempdir(), 'symbols-tmp'),
    ),
    required_config.add_option(
        'symbol_cache_path',
        doc=(
            'the path where the symbol cache is found, this location must be '
            'readable and writeable (quote path with embedded spaces)'
        ),
        default=os.path.join(tempfile.gettempdir(), 'symbols'),
    )
    required_config.add_option(
        'temporary_file_system_storage_path',
        doc='a path where temporary files may be written',
        default=tempfile.gettempdir(),
    )

    def version(self):
        return '1.0'

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
            ujson.dump(raw_crash, f)
        try:
            yield file_pathname
        finally:
            os.unlink(file_pathname)

    def _execute_external_process(self, command_line, processor_meta):
        stackwalker_output, return_code = super(
            BreakpadStackwalkerRule2015,
            self
        )._execute_external_process(command_line, processor_meta)

        if not isinstance(stackwalker_output, Mapping):
            processor_meta.processor_notes.append(
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
            processor_meta.processor_notes.append(
                "MDSW terminated with SIGKILL due to timeout"
            )
        elif return_code != 0 or not stackwalker_data.success:
            processor_meta.processor_notes.append(
                "MDSW failed on '%s': %s" % (
                    command_line,
                    stackwalker_data.mdsw_status_string
                )
            )

        return stackwalker_data, return_code

    def expand_commandline(self, dump_file_pathname, raw_crash_pathname):
        """Expands the command line parameters and returns the final command line"""
        # NOTE(willkg): If we ever add new configuration variables, we'll need
        # to add them here, too, otherwise they won't get expanded in the
        # command line.

        symbols_urls = ' '.join([
            '--symbols-url "%s"' % url.strip()
            for url in self.config.symbols_urls
        ])

        params = {
            # These come from config
            'kill_timeout': self.config.kill_timeout,
            'command_pathname': self.config.command_pathname,
            'symbol_cache_path': self.config.symbol_cache_path,
            'symbol_tmp_path': self.config.symbol_tmp_path,
            'symbols_urls': symbols_urls,

            # These are calculated
            'dump_file_pathname': dump_file_pathname,
            'raw_crash_pathname': raw_crash_pathname
        }
        return self.config.command_line.format(**params)

    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        if 'additional_minidumps' not in processed_crash:
            processed_crash.additional_minidumps = []
        with self._temp_raw_crash_json_file(
            raw_crash,
            raw_crash.uuid
        ) as raw_crash_pathname:
            for dump_name in raw_dumps.iterkeys():

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

                dump_file_pathname = raw_dumps[dump_name]

                command_line = self.expand_commandline(
                    dump_file_pathname=dump_file_pathname,
                    raw_crash_pathname=raw_crash_pathname
                )

                stackwalker_data, return_code = self._execute_external_process(
                    command_line,
                    processor_meta
                )

                if dump_name == self.config.dump_field:
                    processed_crash.update(stackwalker_data)
                else:
                    processed_crash.additional_minidumps.append(dump_name)
                    processed_crash[dump_name] = stackwalker_data

        return True


class JitCrashCategorizeRule(ExternalProcessRule):

    required_config = Namespace()
    required_config.command_line = change_default(
        ExternalProcessRule,
        'command_line',
        'timeout -s KILL 30 {command_pathname} '
        '{dump_file_pathname} '
        '2>/dev/null'
    )
    required_config.command_pathname = change_default(
        ExternalProcessRule,
        'command_pathname',
        '/data/socorro/stackwalk/bin/jit-crash-categorize',
    )
    required_config.result_key = change_default(
        ExternalProcessRule,
        'result_key',
        'classifications.jit.category',
    )
    required_config.return_code_key = change_default(
        ExternalProcessRule,
        'return_code_key',
        'classifications.jit.category_return_code',
    )

    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        if (
            processed_crash.product != 'Firefox' or
            not processed_crash.os_name.startswith('Windows') or
            processed_crash.cpu_name != 'x86'
        ):
            # we don't want any of these
            return False

        frames = processed_crash.get('json_dump', {}).get('crashing_thread', {}).get('frames', [])
        if frames and frames[0].get('module', False):
            # there is a module at the top of the stack, we don't want this
            return False

        return (
            processed_crash.signature.endswith('EnterBaseline') or
            processed_crash.signature.endswith('EnterIon') or
            processed_crash.signature.endswith('js::jit::FastInvoke') or
            processed_crash.signature.endswith('js::jit::IonCannon') or
            processed_crash.signature.endswith('js::irregexp::ExecuteCode<T>')
        )

    def _interpret_external_command_output(self, fp, processor_meta):
        try:
            result = fp.read()
        except IOError as x:
            processor_meta.processor_notes.append(
                "%s unable to read external command output: %s" % (
                    self.config.command_pathname,
                    x
                )
            )
            return ''
        try:
            return result.strip()
        except AttributeError as x:
            # there's no strip method
            return result

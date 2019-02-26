# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import Mapping
from contextlib import contextmanager, closing
import json
import os
import shlex
import subprocess
import threading
import tempfile

from configman import Namespace
from configman.converters import str_to_list
from configman.dotdict import DotDict
import markus

from socorro.lib.util import dotdict_to_dict
from socorro.processor.rules.base import Rule


class CrashingThreadRule(Rule):
    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
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
                processed_crash['json_dump']['crashing_thread']['frames_truncated']
            )
        except KeyError:
            processed_crash.truncated = False

        try:
            processed_crash.address = (
                processed_crash['json_dump']['crash_info']['address']
            )
        except KeyError:
            processed_crash.address = None

        try:
            processed_crash.reason = (
                processed_crash['json_dump']['crash_info']['type']
            )
        except KeyError:
            processed_crash.reason = None


class MinidumpSha256Rule(Rule):
    """Copy over MinidumpSha256Hash value if there is one"""
    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        return 'MinidumpSha256Hash' in raw_crash

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        processed_crash['minidump_sha256_hash'] = raw_crash['MinidumpSha256Hash']


class ExternalProcessRule(Rule):
    # FIXME(willkg): command_line and command_pathname are referenced in the
    # uplifted versions in Processor2015. The rest of these config values have
    # no effect on anything and are just here.
    required_config = Namespace()
    required_config.add_option(
        'dump_field',
        doc='the default name of a dump',
        default='upload_file_minidump',
    )
    required_config.add_option(
        'command_line',
        doc='template for the command to invoke the external program; uses Python format syntax',
        default='timeout -s KILL 30 {command_pathname}',
    )
    required_config.add_option(
        'command_pathname',
        doc='the full pathname to the external program to run (quote path with embedded spaces)',
        default='/data/socorro/stackwalk/bin/dumplookup',
    )
    required_config.add_option(
        'result_key',
        doc='where the external process result should be stored in the processed crash',
        default='%s_result' % (
            required_config.command_pathname.default.split('/')[-1].replace('-', '')
        ),
    )
    required_config.add_option(
        'return_code_key',
        doc='where the external process return code should be stored in the processed crash',
        default='%s_return_code' % required_config.command_pathname.default.split('/')[-1],
    )

    def __init__(self, config):
        super().__init__(config)

    def _interpret_external_command_output(self, fp, processor_meta):
        data = fp.read()
        try:
            return json.loads(data)
        except Exception as x:
            self.logger.error(
                '%s non-json output: "%s"' % (self.config.command_pathname, data[:100])
            )
            processor_meta.processor_notes.append(
                "%s output failed in json: %s" % (self.config.command_pathname, x)
            )
        return {}

    def _execute_external_process(self, command_line, processor_meta):
        # Tokenize the command line into args
        command_line_args = shlex.split(command_line, comments=False, posix=True)

        # Execute the command line sending stderr (debug logging) to devnull and
        # capturing stdout (JSON blob of output)
        subprocess_handle = subprocess.Popen(
            command_line_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
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
        if '.' not in key or isinstance(a_mapping, DotDict):
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
        # FIXME(willkg): we could replace this with glom
        self.dot_save(processed_crash, self.config.result_key, external_command_output)
        self.dot_save(processed_crash, self.config.return_code_key, return_code)

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        command_parameters = dict(self.config)
        command_parameters['dump_file_pathname'] = raw_dumps[self.config['dump_field']]
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


class BreakpadStackwalkerRule2015(ExternalProcessRule):
    """Executes the minidump stackwalker external process and puts output in processed crash"""
    # FIXME(willkg): command_line and command_pathname are referenced in the
    # uplifted versions in Processor2015. The rest of these config values have
    # no effect on anything and are just here.
    required_config = Namespace()
    required_config.add_option(
        name='symbols_urls',
        doc='comma delimited ordered list of urls for symbol lookup',
        default='https://localhost',
        from_string_converter=str_to_list,
        likely_to_be_changed=True
    )
    required_config.add_option(
        'command_line',
        doc='template for the command to invoke the external program; uses Python format syntax',
        default=(
            'timeout -s KILL {kill_timeout} {command_pathname} '
            '--raw-json {raw_crash_pathname} '
            '{symbols_urls} '
            '--symbols-cache {symbol_cache_path} '
            '--symbols-tmp {symbol_tmp_path} '
            '{dump_file_pathname} '
        )
    )
    required_config.add_option(
        'command_pathname',
        doc='the full pathname to the external program to run (quote path with embedded spaces)',
        # NOTE(willkg): This is the path for the RPM-based Socorro deploy. When
        # we switch to Docker, we should change this.
        default='/data/socorro/stackwalk/bin/stackwalker',
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = markus.get_metrics('processor.breakpadstackwalkerrule')

    @contextmanager
    def _temp_raw_crash_json_file(self, raw_crash, crash_id):
        file_pathname = os.path.join(
            self.config.temporary_file_system_storage_path,
            '%s.%s.TEMPORARY.json' % (crash_id, threading.currentThread().getName())
        )
        with open(file_pathname, "w") as f:
            json.dump(dotdict_to_dict(raw_crash), f)
        try:
            yield file_pathname
        finally:
            os.unlink(file_pathname)

    def _execute_external_process(self, command_line, processor_meta):
        stackwalker_output, return_code = (
            super()
            ._execute_external_process(command_line, processor_meta)
        )

        if not isinstance(stackwalker_output, Mapping):
            processor_meta.processor_notes.append(
                'MDSW produced unexpected output: %s...' % str(stackwalker_output)[:10]
            )
            stackwalker_output = {}

        stackwalker_data = DotDict()
        stackwalker_data.json_dump = stackwalker_output
        stackwalker_data.mdsw_return_code = return_code

        stackwalker_data.mdsw_status_string = stackwalker_output.get('status', 'unknown error')
        stackwalker_data.success = stackwalker_data.mdsw_status_string == 'OK'

        self.metrics.incr(
            'run',
            tags=[
                'outcome:%s' % ('success' if stackwalker_data.success else 'fail'),
                'exitcode:%s' % return_code,
            ]
        )

        if return_code == 124:
            msg = 'MDSW terminated with SIGKILL due to timeout'
            processor_meta.processor_notes.append(msg)
            self.logger.warning(msg)

        elif return_code != 0 or not stackwalker_data.success:
            msg = 'MDSW failed with %s: %s' % (return_code, stackwalker_data.mdsw_status_string)
            processor_meta.processor_notes.append(msg)
            self.logger.warning(msg)

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

    def action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        if 'additional_minidumps' not in processed_crash:
            processed_crash.additional_minidumps = []

        with self._temp_raw_crash_json_file(raw_crash, raw_crash.uuid) as raw_crash_pathname:
            for dump_name in raw_dumps.keys():
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


class JitCrashCategorizeRule(ExternalProcessRule):
    # FIXME(willkg): command_line and command_pathname are referenced in the
    # uplifted versions in Processor2015. The rest of these config values have
    # no effect on anything and are just here.
    required_config = Namespace()
    required_config.add_option(
        'command_line',
        doc='template for the command to invoke the external program; uses Python format syntax',
        default='timeout -s KILL 30 {command_pathname} {dump_file_pathname} '
    )
    required_config.add_option(
        'command_pathname',
        doc='the full pathname to the external program to run (quote path with embedded spaces)',
        default='/data/socorro/stackwalk/bin/jit-crash-categorize',
    )
    required_config.add_option(
        'result_key',
        doc='where the external process result should be stored in the processed crash',
        default='classifications.jit.category',
    )
    required_config.add_option(
        'return_code_key',
        doc='where the external process return code should be stored in the processed crash',
        default='classifications.jit.category_return_code',
    )

    def predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
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
        except AttributeError:
            # there's no strip method
            return result

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import Mapping
from contextlib import contextmanager, closing
import json
import logging
import os
import shlex
import subprocess
import threading

import glom
import markus

from socorro.lib.util import dotdict_to_dict
from socorro.processor.rules.base import Rule


LOGGER = logging.getLogger(__name__)


class CrashingThreadInfoRule(Rule):
    """Captures information about the crashing thread

    Fills in:

    * crashing_thread (int or None): index of the crashing thread
    * truncated (bool): whether or not the crashing thread frames were truncated
    * address (str or None): the address of the crash
    * type (str): the crash reason

    """

    def predicate(self, raw_crash, dumps, processed_crash, proc_meta):
        return bool(processed_crash.get("json_dump", None))

    def action(self, raw_crash, dumps, processed_crash, processor_meta):
        processed_crash["crashing_thread"] = glom.glom(
            processed_crash, "json_dump.crash_info.crashing_thread", default=None
        )
        if processed_crash["crashing_thread"] is None:
            processor_meta["processor_notes"].append(
                "mdsw did not identify the crashing thread"
            )

        processed_crash["truncated"] = glom.glom(
            processed_crash, "json_dump.crashing_thread.frames_truncated", default=False
        )

        processed_crash["address"] = glom.glom(
            processed_crash, "json_dump.crash_info.address", default=None
        )

        processed_crash["reason"] = glom.glom(
            processed_crash, "json_dump.crash_info.type", default=""
        )


class MinidumpSha256Rule(Rule):
    """Copy over MinidumpSha256Hash value if there is one"""

    def predicate(self, raw_crash, dumps, processed_crash, proc_meta):
        return "MinidumpSha256Hash" in raw_crash

    def action(self, raw_crash, dumps, processed_crash, processor_meta):
        processed_crash["minidump_sha256_hash"] = raw_crash["MinidumpSha256Hash"]


@contextmanager
def tmp_raw_crash_file(tmp_path, raw_crash, crash_id):
    """Saves JSON data to file, returns path, and deletes file when done.

    :param tmp_path: str path to temp storage
    :param raw_crash: dotdict or dict of raw crash data
    :param crash_id: crash id for this crash report

    :yields: absolute path to temp file

    """

    path = os.path.join(
        tmp_path, f"{crash_id}.{threading.currentThread().getName()}.TEMPORARY.json"
    )
    with open(path, "w") as fp:
        json.dump(dotdict_to_dict(raw_crash), fp)

    try:
        yield path
    finally:
        os.unlink(path)


def execute_process(command_line):
    """Executes process and returns output and return_code.

    :param command_line: the complete command line to run

    :returns: (output, return_code)

    """
    # Tokenize the command line into args
    command_line_args = shlex.split(command_line, comments=False, posix=True)

    # Execute the command line sending stderr (debug logging) to devnull and
    # capturing stdout (JSON blob of output)
    subprocess_handle = subprocess.Popen(
        command_line_args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    with closing(subprocess_handle.stdout):
        data = subprocess_handle.stdout.read()

    return_code = subprocess_handle.wait()
    return data, return_code


class CommandError(Exception):
    pass


class MinidumpStackwalkRule(Rule):
    """Runs minidump-stackwalk (rust) on minidump and puts output in processed crash.

    This uses the rust-minidump minidump-stackwalk.

    Produces:

    * json_dump: output from minidump_stackwalk run
    * mdsw_exit_code: process exit code
    * mdsw_status_string: string of json_dump["status"]
    * mdsw_success: bool
    * additional_minidumps: list of minidump names that aren't dump_field value

    Also adds processor notes.

    Emits:

    * processor.minidumpstackwalk.*

    """

    def __init__(
        self,
        dump_field="upload_file_minidump",
        symbols_urls=None,
        command_path="/stackwalk-rust/minidump-stackwalk",
        command_line=(
            "timeout --signal KILL {kill_timeout} {command_path} "
            "--raw-json {raw_crash_path} "
            "{symbols_urls} "
            "--symbols-cache {symbol_cache_path} "
            "--symbols-tmp {symbol_tmp_path} "
            "{dump_file_path}"
        ),
        kill_timeout=600,
        symbol_tmp_path="/tmp/symbols-tmp",
        symbol_cache_path="/tmp/symbols",
        tmp_path="/tmp/",
    ):
        super().__init__()
        self.dump_field = dump_field
        self.symbols_urls = symbols_urls or []
        self.command_path = command_path
        self.command_line = command_line
        self.kill_timeout = kill_timeout
        self.symbol_tmp_path = symbol_tmp_path
        self.symbol_cache_path = symbol_cache_path
        self.tmp_path = tmp_path

        self.stackwalk_version = self.get_version()
        self.build_directories()

        self.metrics = markus.get_metrics("processor.minidumpstackwalk")

    def __repr__(self):
        keys = (
            "dump_field",
            "symbols_urls",
            "command_path",
            "command_line",
            "kill_timeout",
            "symbol_tmp_path",
            "symbol_cache_path",
            "tmp_path",
        )
        return self.generate_repr(keys=keys)

    def get_version(self):
        command_line = f"{self.command_path} --version"
        output, return_code = execute_process(command_line)
        if return_code != 0:
            raise CommandError(
                "MinidumpStackwalkRule: unknown error when getting version: "
                + f"{return_code} {output}"
            )
        return output.decode("utf-8").strip()

    def build_directories(self):
        os.makedirs(self.symbol_tmp_path, exist_ok=True)
        os.makedirs(self.symbol_cache_path, exist_ok=True)

    def expand_commandline(self, dump_file_path, raw_crash_path):
        """Expands the command line parameters and returns the final command line

        :param dump_file_path: the absolute path to the dump file to parse
        :param raw_crash_path: the absolute path to the crash annotations file

        :returns: command line as a string

        """
        # NOTE(willkg): If we ever add new configuration variables, we'll need
        # to add them here, too, otherwise they won't get expanded in the
        # command line.

        symbols_urls = " ".join(
            ['--symbols-url "%s"' % url.strip() for url in self.symbols_urls]
        )

        params = {
            # These come from config
            "kill_timeout": self.kill_timeout,
            "command_path": self.command_path,
            "symbol_cache_path": self.symbol_cache_path,
            "symbol_tmp_path": self.symbol_tmp_path,
            "symbols_urls": symbols_urls,
            # These are calculated
            "dump_file_path": dump_file_path,
            "raw_crash_path": raw_crash_path,
        }
        return self.command_line.format(**params)

    def run_stackwalker(self, crash_id, command_path, command_line, processor_meta):
        stdout, return_code = execute_process(command_line)

        try:
            output = json.loads(stdout)
        except Exception as exc:
            msg = f"{command_path}: non-json output: {exc}"
            self.logger.debug(
                f"MinidumpStackwalkRule: {command_path}: non-json output: {stdout[:1000]}"
            )
            self.logger.error(msg)
            processor_meta["processor_notes"].append(msg)
            output = {}

        if not isinstance(output, Mapping):
            msg = (
                "MinidumpStackwalkRule: minidump-stackwalk produced unexpected "
                + f"output: {output[:20]}"
            )
            processor_meta["processor_notes"].append(msg)
            self.logger.warning(f"{msg} ({crash_id})")
            output = {}

        # Add the stackwalk_version to the stackwalk output
        output["stackwalk_version"] = self.stackwalk_version

        stackwalker_data = {
            "json_dump": output,
            "mdsw_return_code": return_code,
            "mdsw_status_string": output.get("status", "unknown error"),
            "success": output.get("status", "") == "OK",
        }

        self.metrics.incr(
            "run",
            tags=[
                "outcome:%s" % ("success" if stackwalker_data["success"] else "fail"),
                "exitcode:%s" % return_code,
            ],
        )

        if return_code == 124:
            msg = "MinidumpStackwalkRule: minidump-stackwalk: timeout (SIGKILL)"
            processor_meta["processor_notes"].append(msg)
            self.logger.warning(f"{msg} ({crash_id})")

        elif return_code != 0 or not stackwalker_data["success"]:
            msg = (
                "MinidumpStackwalkRule: minidump-stackwalk: failed with "
                + f"{return_code}: {stackwalker_data['mdsw_status_string']}"
            )
            # subprocess.Popen with shell=False returns negative exit codes
            # where the number is the signal that got kicked up
            if return_code == -6:
                msg = msg + " (SIGABRT)"

            processor_meta["processor_notes"].append(msg)
            self.logger.warning(f"{msg} ({crash_id})")

        return stackwalker_data, return_code

    def action(self, raw_crash, dumps, processed_crash, processor_meta):
        crash_id = raw_crash["uuid"]

        processed_crash.setdefault("additional_minidumps", [])

        with tmp_raw_crash_file(self.tmp_path, raw_crash, crash_id) as raw_crash_path:
            for dump_name, dump_file_path in dumps.items():
                # This rule only works on minidumps which the crash reporter prefixes
                # with the value of dump_field (defaults to "upload_file_minidump")
                if not dump_name.startswith(self.dump_field):
                    continue

                # If the dump file is empty (0-bytes), then we don't want to run
                file_size = os.path.getsize(dump_file_path)
                if file_size == 0:
                    # This is a bad case, so we want to add a note.
                    processor_meta["processor_notes"].append(
                        f"MinidumpStackwalkRule: {dump_name} is empty--skipping "
                        + "minidump processing"
                    )
                    continue

                command_line = self.expand_commandline(
                    dump_file_path=dump_file_path,
                    raw_crash_path=raw_crash_path,
                )

                stackwalker_data, return_code = self.run_stackwalker(
                    crash_id=crash_id,
                    command_path=self.command_path,
                    command_line=command_line,
                    processor_meta=processor_meta,
                )

                if dump_name == self.dump_field:
                    processed_crash.update(stackwalker_data)

                else:
                    if dump_name not in processed_crash["additional_minidumps"]:
                        processed_crash["additional_minidumps"].append(dump_name)
                    processed_crash.setdefault(dump_name, {})
                    processed_crash[dump_name].update(stackwalker_data)


class BreakpadStackwalkerRule2015(Rule):
    """Executes minidump-stackwalker and puts output in processed crash."""

    def __init__(
        self,
        dump_field,
        symbols_urls,
        command_path,
        command_line,
        kill_timeout,
        symbol_tmp_path,
        symbol_cache_path,
        tmp_path,
    ):
        super().__init__()
        self.dump_field = dump_field
        self.symbols_urls = symbols_urls
        self.command_path = command_path
        self.command_line = command_line
        self.kill_timeout = kill_timeout
        self.symbol_tmp_path = symbol_tmp_path
        self.symbol_cache_path = symbol_cache_path
        self.tmp_path = tmp_path

        # NOTE(willkg): we can't get a version from the binary without a lot of work
        # which we're not going to do now because this is not long for this world
        self.stackwalk_version = "stackwalker unknown"

        self.metrics = markus.get_metrics("processor.breakpadstackwalkerrule")

    def __repr__(self):
        keys = (
            "dump_field",
            "symbols_urls",
            "command_path",
            "command_line",
            "kill_timeout",
            "symbol_tmp_path",
            "symbol_cache_path",
            "tmp_path",
        )
        return self.generate_repr(keys=keys)

    def expand_commandline(self, dump_file_path, raw_crash_path):
        """Expands the command line parameters and returns the final command line"""
        # NOTE(willkg): If we ever add new configuration variables, we'll need
        # to add them here, too, otherwise they won't get expanded in the
        # command line.

        symbols_urls = " ".join(
            ['--symbols-url "%s"' % url.strip() for url in self.symbols_urls]
        )

        params = {
            # These come from config
            "kill_timeout": self.kill_timeout,
            "command_path": self.command_path,
            "symbol_cache_path": self.symbol_cache_path,
            "symbol_tmp_path": self.symbol_tmp_path,
            "symbols_urls": symbols_urls,
            # These are calculated
            "dump_file_path": dump_file_path,
            "raw_crash_path": raw_crash_path,
        }
        return self.command_line.format(**params)

    def run_stackwalker(self, crash_id, command_path, command_line, processor_meta):
        stdout, return_code = execute_process(command_line)

        try:
            output = json.loads(stdout)
        except Exception as exc:
            msg = f"{command_path}: non-json output: {exc}"
            self.logger.debug(f"{command_path}: non-json output: {stdout[:1000]}")
            self.logger.error(msg)
            processor_meta["processor_notes"].append(msg)
            output = {}

        if not isinstance(output, Mapping):
            msg = "MDSW produced unexpected output: %s (%s)" % str(output)[:20]
            processor_meta["processor_notes"].append(msg)
            self.logger.warning(msg + " (%s)" % crash_id)
            output = {}

        # Add the stackwalk_version to the stackwalk output
        output["stackwalk_version"] = self.stackwalk_version

        stackwalker_data = {
            "json_dump": output,
            "mdsw_return_code": return_code,
            "mdsw_status_string": output.get("status", "unknown error"),
            "success": output.get("status", "") == "OK",
        }

        self.metrics.incr(
            "run",
            tags=[
                "outcome:%s" % ("success" if stackwalker_data["success"] else "fail"),
                "exitcode:%s" % return_code,
            ],
        )

        if return_code == 124:
            msg = "MDSW timeout (SIGKILL)"
            processor_meta["processor_notes"].append(msg)
            self.logger.warning(msg + " (%s)" % crash_id)

        elif return_code != 0 or not stackwalker_data["success"]:
            msg = "MDSW failed with %s: %s" % (
                return_code,
                stackwalker_data["mdsw_status_string"],
            )
            # subprocess.Popen with shell=False returns negative exit codes
            # where the number is the signal that got kicked up
            if return_code == -6:
                msg = msg + " (SIGABRT)"

            processor_meta["processor_notes"].append(msg)
            self.logger.warning(msg + " (%s)" % crash_id)

        return stackwalker_data, return_code

    def action(self, raw_crash, dumps, processed_crash, processor_meta):
        crash_id = raw_crash["uuid"]

        processed_crash.setdefault("additional_minidumps", [])

        with tmp_raw_crash_file(self.tmp_path, raw_crash, crash_id) as raw_crash_path:
            for dump_name in dumps.keys():
                # this rule is only interested in dumps targeted for the
                # minidump stackwalker external program.  As of the writing
                # of this code, there is one other dump type.  The only way
                # to differentiate these dump types is by the name of the
                # dump.  All minidumps targeted for the stackwalker will have
                # a name with a prefix specified in configuration:
                if not dump_name.startswith(self.dump_field):
                    # dumps not intended for the stackwalker are ignored
                    continue

                dump_file_path = dumps[dump_name]

                command_line = self.expand_commandline(
                    dump_file_path=dump_file_path,
                    raw_crash_path=raw_crash_path,
                )

                stackwalker_data, return_code = self.run_stackwalker(
                    crash_id=crash_id,
                    command_path=self.command_path,
                    command_line=command_line,
                    processor_meta=processor_meta,
                )

                if dump_name == self.dump_field:
                    processed_crash.update(stackwalker_data)
                else:
                    if dump_name not in processed_crash["additional_minidumps"]:
                        processed_crash["additional_minidumps"].append(dump_name)
                    processed_crash.setdefault(dump_name, {})
                    processed_crash[dump_name].update(stackwalker_data)


class JitCrashCategorizeRule(Rule):
    """Categorizes JIT crashes.

    NOTE(willkg): This needs to run after BreakpadStackwalkerRule2015 and
    SignatureGenerationRule.

    """

    def __init__(self, dump_field, command_path, command_line, kill_timeout):
        super().__init__()
        self.dump_field = dump_field
        self.command_path = command_path
        self.command_line = command_line
        self.kill_timeout = kill_timeout

    def __repr__(self):
        keys = ("dump_field", "command_path", "command_line", "kill_timeout")
        return self.generate_repr(keys=keys)

    def predicate(self, raw_crash, dumps, processed_crash, proc_meta):
        if (
            processed_crash.get("product", "") != "Firefox"
            or not processed_crash.get("os_name", "").startswith("Windows")
            or processed_crash.get("cpu_arch", "") != "x86"
        ):
            # we don't want any of these
            return False

        frames = glom.glom(
            processed_crash, "json_dump.crashing_thread.frames", default=[]
        )
        if frames and frames[0].get("module", False):
            # there is a module at the top of the stack, we don't want this
            return False

        signature = processed_crash.get("signature", "")
        return (
            signature.endswith("EnterBaseline")
            or signature.endswith("EnterIon")
            or signature.endswith("js::jit::FastInvoke")
            or signature.endswith("js::jit::IonCannon")
            or signature.endswith("js::irregexp::ExecuteCode<T>")
        )

    def action(self, raw_crash, dumps, processed_crash, processor_meta):
        params = {
            "command_path": self.command_path,
            "kill_timeout": self.kill_timeout,
            "dump_file_path": dumps[self.dump_field],
        }
        command_line = self.command_line.format(**params)

        stdout, return_code = execute_process(command_line)
        output = stdout
        if output:
            output = output.strip()

        glom.assign(
            processed_crash, "classifications.jit.category", val=output, missing=dict
        )
        glom.assign(
            processed_crash,
            "classifications.jit.category_return_code",
            val=return_code,
            missing=dict,
        )

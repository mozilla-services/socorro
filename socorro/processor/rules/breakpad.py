# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections.abc import Mapping
from contextlib import contextmanager
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
    * address (str or None): the address of the crash
    * type (str): the crash reason

    """

    def predicate(self, raw_crash, dumps, processed_crash, proc_meta):
        return processed_crash.get("json_dump", None) is not None

    def action(self, raw_crash, dumps, processed_crash, processor_meta):
        processed_crash["crashing_thread"] = glom.glom(
            processed_crash, "json_dump.crash_info.crashing_thread", default=None
        )
        if processed_crash["crashing_thread"] is None:
            processor_meta["processor_notes"].append(
                "mdsw did not identify the crashing thread"
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
    """Executes process and returns completed process data.

    :param command_line: the complete command line to run

    :returns: dict with stdout, stderr, and returncode keys

    """
    # Tokenize the command line into args
    args = shlex.split(command_line, comments=False, posix=True)
    completed = subprocess.run(args, capture_output=True)
    ret = {
        # NOTE(willkg) stdout and stderr here are bytes
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }
    return ret


class CommandError(Exception):
    pass


class MinidumpStackwalkRule(Rule):
    """Runs minidump-stackwalk (rust) on minidump and puts output in processed crash.

    This uses the rust-minidump minidump-stackwalk.

    Produces:

    * json_dump: output from minidump_stackwalk run
    * mdsw_exit_code: process exit code
    * mdsw_status_string:

      * value of json_dump["status"]
      * error code derived from mdsw_stderr

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
            "timeout --signal KILL {kill_timeout} "
            "{command_path} "
            "--raw-json={raw_crash_path} "
            "--symbols-cache={symbol_cache_path} "
            "--symbols-tmp={symbol_tmp_path} "
            "{symbols_urls} "
            "--json "
            "--verbose=error "
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
        ret = execute_process(command_line)
        if ret["returncode"] != 0:
            raise CommandError(
                "MinidumpStackwalkRule: unknown error when getting version: "
                + f"{ret['returncode']} {ret['stdout']}"
            )
        version = ret["stdout"].decode("utf-8").strip()

        # If there's a JSON file, then that has version information about the
        # minidump-stackwalk that we installed, so tack that information on
        shafile = self.command_path + ".version.json"
        if os.path.exists(shafile):
            with open(shafile, "r") as fp:
                data = json.load(fp)
            if data:
                rev = data["sha"][:8]
                revdate = data["date"]
                version = f"{version} ({revdate} {rev})"
        return version

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
            ['--symbols-url="%s"' % url.strip() for url in self.symbols_urls]
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
        ret = execute_process(command_line)
        returncode = ret["returncode"]
        stdout = ret["stdout"]
        stderr = ret["stderr"]

        # Decode stderr and truncate to 10 lines
        stderr = stderr.decode("utf-8") if stderr else ""
        if stderr.count("\n") > 10:
            stderr = "\n".join(["..."] + stderr.splitlines()[-10:])
        output = {}

        if returncode == 0:
            try:
                output = json.loads(ret["stdout"])

            except Exception as exc:
                msg = f"{command_path}: non-json output: {exc}"
                self.logger.debug(
                    f"MinidumpStackwalkRule: {command_path}: non-json output: "
                    f"{stdout[:1000]}"
                )
                self.logger.error(msg)
                processor_meta["processor_notes"].append(msg)

            if output and not isinstance(output, Mapping):
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
            "mdsw_return_code": returncode,
            "mdsw_status_string": output.get("status", "unknown error"),
            "success": output.get("status", "") == "OK",
            # Note: this may contain proected data
            "mdsw_stderr": stderr,
        }

        if returncode == 124:
            msg = "MinidumpStackwalkRule: minidump-stackwalk: timeout (SIGKILL)"
            processor_meta["processor_notes"].append(msg)
            self.logger.warning(f"{msg} ({crash_id})")

        elif returncode != 0 or not stackwalker_data["success"]:
            msg = (
                "MinidumpStackwalkRule: minidump-stackwalk: failed with "
                + f"{returncode}: {stackwalker_data['mdsw_status_string']}"
            )
            # subprocess.Popen with shell=False returns negative exit codes
            # where the number is the signal that got kicked up
            if returncode == -6:
                msg = msg + " (SIGABRT)"

            processor_meta["processor_notes"].append(msg)
            self.logger.warning(f"{msg} ({crash_id})")

        self.metrics.incr(
            "run",
            tags=[
                "outcome:%s" % ("success" if stackwalker_data["success"] else "fail"),
                "exitcode:%s" % returncode,
            ],
        )

        return stackwalker_data

    def action(self, raw_crash, dumps, processed_crash, processor_meta):
        crash_id = raw_crash["uuid"]

        processed_crash.setdefault("additional_minidumps", [])

        with tmp_raw_crash_file(self.tmp_path, raw_crash, crash_id) as raw_crash_path:
            for dump_name, dump_file_path in dumps.items():
                # This rule only works on minidumps which the crash reporter prefixes
                # with the value of dump_field (defaults to "upload_file_minidump")
                if not dump_name.startswith(self.dump_field):
                    continue

                file_size = os.path.getsize(dump_file_path)
                if file_size == 0:
                    # If the dump file is empty (0-bytes), then we don't want to bother
                    # running minidump-stackwalker.
                    #
                    # This is a bad case, so we want to add a note. However, since this
                    # is a shortcut, we also include some stackwalker_data.
                    stackwalker_data = {
                        "mdsw_status_string": "EmptyMinidump",
                        "mdsw_stderr": "Shortcut for 0-bytes minidump.",
                    }

                    processor_meta["processor_notes"].append(
                        f"MinidumpStackwalkRule: {dump_name} is empty--skipping "
                        + "minidump processing"
                    )

                else:
                    command_line = self.expand_commandline(
                        dump_file_path=dump_file_path,
                        raw_crash_path=raw_crash_path,
                    )

                    stackwalker_data = self.run_stackwalker(
                        crash_id=crash_id,
                        command_path=self.command_path,
                        command_line=command_line,
                        processor_meta=processor_meta,
                    )

                    stderr = stackwalker_data.get("mdsw_stderr", "").strip()
                    if stderr:
                        if stderr.startswith("[ERROR]"):
                            indicator = stderr.split(" ")[1]
                        else:
                            indicator = ""

                        status_string = stackwalker_data.get("mdsw_status_string", "")
                        if indicator and status_string in ["OK", "unknown error"]:
                            stackwalker_data["mdsw_status_string"] = indicator
                            processor_meta["processor_notes"].append(
                                f"MinidumpStackwalkRule: processing {dump_name} had error; "
                                + "stomped on mdsw_status_string"
                            )

                if dump_name == self.dump_field:
                    processed_crash.update(stackwalker_data)

                else:
                    if dump_name not in processed_crash["additional_minidumps"]:
                        processed_crash["additional_minidumps"].append(dump_name)
                    processed_crash.setdefault(dump_name, {})
                    processed_crash[dump_name].update(stackwalker_data)

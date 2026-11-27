# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import logging
import os
import shlex
import subprocess
from collections.abc import Mapping

from glom import glom

from socorro.libmarkus import METRICS
from socorro.processor.rules.base import Rule

LOGGER = logging.getLogger(__name__)


class CrashingThreadInfoRule(Rule):
    """Captures information about the crashing thread

    Fills in:

    * crashing_thread (int or None): index of the crashing thread
    * crashing_thread_name (str or None): name of crashing thread
    * address (str or None): the address of the crash
    * type (str): the crash reason
    * last_error_value (str): the last_error_value if any

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return processed_crash.get("json_dump", None) is not None

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        crash_info = glom(processed_crash, "json_dump.crash_info", default={})

        crashing_thread = crash_info.get("crashing_thread")
        processed_crash["crashing_thread"] = crashing_thread
        if crashing_thread is None:
            status.add_note("mdsw did not identify the crashing thread")

        processed_crash["crashing_thread_name"] = glom(
            processed_crash,
            "json_dump.crashing_thread.thread_name",
            default=None,
        )
        processed_crash["reason"] = crash_info.get("type", "")

        # If the crash_info.adjusted_address is not present or is null then the crashing
        # address is crash_info.address.
        #
        # If crash_info.adjusted_address is present and if the
        # crash_info.adjusted_address.kind field is null-pointer then consider
        # crash_info.address to be NULL (either 0x00000000 or 0x0000000000000000
        # depending on the pointer size).
        #
        # If crash_info.adjusted_address is present and if the
        # crash_info.adjusted_address.kind field is non-canonical then use
        # crash_info.adjusted_address.address instead of crash_info.address for the
        # crashing address.
        address = crash_info.get("address")
        adjusted_address = crash_info.get("adjusted_address")

        if adjusted_address is not None:
            kind = adjusted_address.get("kind")
            if kind == "null-pointer":
                # Infer the width from the previous address value
                if address and len(address) == 18:
                    address = "0x0000000000000000"
                else:
                    address = "0x00000000"

            elif kind == "non-canonical" and adjusted_address.get("address"):
                address = adjusted_address["address"]

        processed_crash["address"] = address

        last_error_value = glom(
            processed_crash,
            "json_dump.crashing_thread.last_error_value",
            default=None,
        )
        if isinstance(last_error_value, str):
            processed_crash["last_error_value"] = last_error_value


class CrashInconsistenciesRule(Rule):
    """Copy crash_inconsistencies values if there are any

    Fills in:

    * crash_inconsistencies (list[str]): A list of inconsistencies detected by comparing
      crash reason/crash address with crashing instruction and memory information

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        return processed_crash.get("json_dump", None) is not None

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        crash_info = glom(processed_crash, "json_dump.crash_info", default={})

        crash_inconsistencies = crash_info.get("crash_inconsistencies")
        processed_crash["crash_inconsistencies"] = crash_inconsistencies


class MinidumpSha256HashRule(Rule):
    """Copy sha256 hash of upload_file_minidump value if there is one

    Fills in:

    * minidump_sha256_hash (str): hash of upload_file_minidump

    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        checksums = raw_crash.get("metadata", {}).get("dump_checksums", {})
        processed_crash["minidump_sha256_hash"] = checksums.get(
            "upload_file_minidump", ""
        )


class PossibleBitFlipsRule(Rule):
    """Compute possible_bit_flips_max_confidence value

    Fills in:

    * possible_bit_flips_max_confidence (int): maximum confidence value of possible bit
      flips; range 0 to 100

    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        bit_flips = glom(
            processed_crash, "json_dump.crash_info.possible_bit_flips", default=None
        )
        if bit_flips is None:
            return

        confidences = [item.get("confidence", 0.0) for item in bit_flips]

        if not confidences:
            return

        # NOTE(willkg): The confidence value ranges from 0.0 to 1.0, but that doesn't
        # work with Elasticsearch histogram intervals which round to whole numbers. So
        # we make this 0 to 100.
        processed_crash["possible_bit_flips_max_confidence"] = int(
            max(confidences) * 100
        )


class HasGuardPageAccessRule(Rule):
    """Compute has_guard_page_access value

    Fills in:

    * has_guard_page_access (bool): whether there are "is_likely_guard_page=True"
      in json_dump.crash_info.memory_accesses structures

    """

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        accesses = glom(
            processed_crash, "json_dump.crash_info.memory_accesses", default=None
        )
        if accesses is None:
            return

        # is_likely_guard_page is True iff at least one of the memory_accesses values is
        # true
        has_guard_page_access = any(
            data.get("is_likely_guard_page", False) for data in accesses
        )

        # Only set the property if it's True
        if has_guard_page_access:
            processed_crash["has_guard_page_access"] = True


class TruncateStacksRule(Rule):
    """Truncate stacks that are too large

    This rule truncates stacks that are greater than MAX_FRAMES. It truncates the stacks
    in the middle with the thinking that the beginning and end of the stack are the most
    interesting.

    """

    MAX_FRAMES = 500
    HALF_MAX_FRAMES = int(MAX_FRAMES / 2)

    def truncation_frame(self, truncated_frames):
        return {"truncated": {"msg": f"{len(truncated_frames):,} frames truncated"}}

    def truncate(self, frames):
        """Truncates a single stack if it's too big

        :arg frames: the list of frame structures to truncate

        :returns: truncated list of frame structures with a truncation
            frame in the middle

        """
        METRICS.gauge("processor.truncatestackrule.stack_size", len(frames))
        METRICS.incr("processor.truncatestackrule.truncated")

        first_frames = frames[: self.HALF_MAX_FRAMES]
        truncated_frames = frames[self.HALF_MAX_FRAMES : -self.HALF_MAX_FRAMES]
        last_frames = frames[-self.HALF_MAX_FRAMES + 1 :]

        return first_frames + [self.truncation_frame(truncated_frames)] + last_frames

    def truncate_stacks(self, json_dump, path, status):
        """Truncate all the stacks found in stackwalker output"""
        thread = json_dump.get("crashing_thread")
        if thread:
            frames = thread.get("frames", [])
            if len(frames) > self.MAX_FRAMES:
                frames_path = f"{path}.crashing_thread.frames"
                truncated_frames = self.truncate(frames)
                thread["frames"] = truncated_frames
                thread["truncated"] = True
                status.add_note(
                    f"TruncateStacksRule: truncated {frames_path}: "
                    + f"{len(frames)} -> {len(truncated_frames)}"
                )

        for i, thread in enumerate(json_dump.get("threads", [])):
            frames = thread.get("frames", [])
            if len(frames) > self.MAX_FRAMES:
                frames_path = f"{path}.threads[{i}].frames"
                truncated_frames = self.truncate(frames)
                thread["frames"] = truncated_frames
                thread["truncated"] = True
                status.add_note(
                    f"TruncateStacksRule: truncated {frames_path}: "
                    + f"{len(frames)} > {len(truncated_frames)}"
                )

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # Traverse processed_crash for "json_dump" sections. Each one of these has
        # multiple stacks in it.
        for key, value in processed_crash.items():
            if key == "json_dump":
                self.truncate_stacks(value, "json_dump", status)

            elif isinstance(value, dict):
                if "json_dump" in value:
                    self.truncate_stacks(value["json_dump"], f"{key}.json_dump", status)


def execute_process(command_line, timeout=120):
    """Executes process and returns completed process data.

    :param command_line: the complete command line to run
    :param timeout: the timeout in seconds for the command to complete before it's
        killed; defaults to 120 seconds

    :returns: dict with stdout (bytes), stderr (bytes), and returncode (signed smallint)
        keys

    """
    # Tokenize the command line into args
    args = shlex.split(command_line, comments=False, posix=True)
    try:
        completed = subprocess.run(args, timeout=timeout, capture_output=True)
        ret = {
            # NOTE(willkg) stdout and stderr here are bytes
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }

    except subprocess.TimeoutExpired as timeout_exc:
        ret = {
            # NOTE(willkg) stdout and stderr here are bytes
            "stdout": timeout_exc.stdout or b"",
            "stderr": timeout_exc.stderr or b"",
            # NOTE(willkg): if the timeout expired, then the child process was killed
            # and the returncode should be -9
            "returncode": -9,
        }
    return ret


def get_version_json_suffix(command_path):
    """Returns "(<date> <sha>)" from <command_path>.version.json, or "" if unavailable.

    The socorro-stackwalk release tarball includes a <binary>.version.json file
    next to each binary with the revision and date it was built from.

    :param command_path: the absolute path to the binary

    :returns: version suffix string; e.g. "(2025-06-20 v0.26.0)"

    """
    shafile = command_path + ".version.json"
    if not os.path.exists(shafile):
        return ""
    with open(shafile, "r") as fp:
        data = json.load(fp)
    if not data:
        return ""
    rev = data["sha"][:8]
    revdate = data["date"]
    return f"({revdate} {rev})"


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
        # NOTE(willkg): this is the location it gets put in the Docker image
        command_path="/stackwalk-rust/minidump-stackwalk",
        command_line=(
            "{command_path} "
            + "--evil-json={raw_crash_path} "
            + "--symbols-cache={symbol_cache_path} "
            + "--symbols-tmp={symbol_tmp_path} "
            + "--no-color "
            + "--output-file={output_path} "
            + "--log-file={log_path} "
            + "{symbols_urls} "
            + "--json "
            + "--verbose=error "
            + "{dump_file_path}"
        ),
        kill_timeout=600,
        symbol_tmp_path="/tmp/symbols-tmp",
        symbol_cache_path="/tmp/symbols",
    ):
        super().__init__()

        # If kill_timeout is None, set it to 600--the default
        if kill_timeout is None:
            kill_timeout = 600

        self.dump_field = dump_field
        self.symbols_urls = symbols_urls or []
        self.command_path = command_path
        self.command_line = command_line
        self.kill_timeout = kill_timeout
        self.symbol_tmp_path = symbol_tmp_path
        self.symbol_cache_path = symbol_cache_path

        self.stackwalk_version = self.get_version()
        self.build_directories()

    def __repr__(self):
        keys = (
            "dump_field",
            "symbols_urls",
            "command_path",
            "command_line",
            "kill_timeout",
            "symbol_tmp_path",
            "symbol_cache_path",
        )
        return self.generate_repr(keys=keys)

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # Crash pings have no minidump; SymbolicateRule handles them
        return processed_crash.get("submission_type") != "ping"

    def get_version(self):
        command_line = f"{self.command_path} --version"
        ret = execute_process(command_line, timeout=self.kill_timeout)
        if ret["returncode"] != 0:
            raise CommandError(
                "MinidumpStackwalkRule: unknown error when getting version: "
                + f"{ret['returncode']} {ret['stdout']}"
            )
        version = ret["stdout"].decode("utf-8").strip()

        # If there's a JSON file, then that has version information about the
        # minidump-stackwalk that we installed, so tack that information on
        suffix = get_version_json_suffix(self.command_path)
        return f"{version} {suffix}" if suffix else version

    def build_directories(self):
        os.makedirs(self.symbol_tmp_path, exist_ok=True)
        os.makedirs(self.symbol_cache_path, exist_ok=True)

    def expand_commandline(self, dump_file_path, raw_crash_path, output_path, log_path):
        """Expands the command line parameters and returns the final command line

        :param dump_file_path: the absolute path to the dump file to parse
        :param raw_crash_path: the absolute path to the crash annotations file
        :param output_path: the absolute path to where the output will go
        :param log_path: the absolute path to where logging output will go

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
            "command_path": self.command_path,
            "symbol_cache_path": self.symbol_cache_path,
            "symbol_tmp_path": self.symbol_tmp_path,
            "symbols_urls": symbols_urls,
            # These are calculated
            "dump_file_path": dump_file_path,
            "raw_crash_path": raw_crash_path,
            "output_path": output_path,
            "log_path": log_path,
        }
        return self.command_line.format(**params)

    def run_stackwalker(
        self, crash_id, command_path, command_line, output_path, log_path, status
    ):
        ret = execute_process(command_line, timeout=self.kill_timeout)
        returncode = ret["returncode"]

        # Grab any log data
        if os.path.exists(log_path):
            with open(log_path, "r") as fp:
                log_data = fp.read()
        else:
            log_data = ""

        # Decode stderr and truncate to 10 lines
        if log_data.count("\n") > 10:
            log_data = "\n".join(["..."] + log_data.splitlines()[-10:])

        output = {}
        if returncode == 0:
            if os.path.exists(output_path):
                with open(output_path, "r") as fp:
                    output_raw = fp.read()

                try:
                    output = json.loads(output_raw)
                except Exception as exc:
                    msg = f"{command_path}: non-json output: {exc}"
                    self.logger.debug(
                        "MinidumpStackwalkRule: %s: non-json output: %s",
                        command_path,
                        output_raw[:1000],
                    )
                    self.logger.error(msg)
                    status.add_note(msg)

                if output and not isinstance(output, Mapping):
                    msg = (
                        "MinidumpStackwalkRule: minidump-stackwalk produced unexpected "
                        + f"output: {str(output)[:200]}"
                    )
                    status.add_note(msg)
                    self.logger.warning("%s (%s)", msg, crash_id)
                    output = {}

        status_line = output.get("status", "unknown error")
        stackwalker_data = {
            "json_dump": output,
            "mdsw_return_code": returncode,
            "mdsw_status_string": status_line,
            "success": status_line == "OK",
            "stackwalk_version": self.stackwalk_version,
            # NOTE(willkg): this may contain proected data
            "mdsw_stderr": log_data,
        }

        # subprocess.Popen with shell=False returns negative exit codes where the number
        # is the signal that got kicked up
        if returncode != 0 or not stackwalker_data["success"]:
            if returncode == -6:
                msg = "MinidumpStackwalkRule: minidump-stackwalk: timeout (SIGABRT)"

            elif returncode == -9:
                msg = "MinidumpStackwalkRule: minidump-stackwalk: timeout (SIGKILL)"

            else:
                status_string = stackwalker_data["mdsw_status_string"]
                msg = (
                    "MinidumpStackwalkRule: minidump-stackwalk: failed: "
                    + f"{returncode}: {status_string}"
                )

            status.add_note(msg)
            self.logger.warning("%s (%s)", msg, crash_id)

        METRICS.incr(
            "processor.minidumpstackwalk.run",
            tags=[
                "outcome:%s" % ("success" if stackwalker_data["success"] else "fail"),
                "exitcode:%s" % returncode,
            ],
        )

        return stackwalker_data

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        crash_id = raw_crash["uuid"]

        processed_crash.setdefault("additional_minidumps", [])

        # Save crash annotations to disk for stackwalker to look at
        raw_crash_path = os.path.join(tmpdir, f"{crash_id}.json")
        with open(raw_crash_path, "w") as fp:
            json.dump(raw_crash, fp)

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

                status.add_note(
                    f"MinidumpStackwalkRule: {dump_name} is empty--skipping "
                    + "minidump processing"
                )

            else:
                log_path = os.path.join(tmpdir, f"{crash_id}.{dump_name}.log")
                output_path = os.path.join(tmpdir, f"{crash_id}.{dump_name}.json")
                command_line = self.expand_commandline(
                    dump_file_path=dump_file_path,
                    raw_crash_path=raw_crash_path,
                    output_path=output_path,
                    log_path=log_path,
                )

                stackwalker_data = self.run_stackwalker(
                    crash_id=crash_id,
                    command_path=self.command_path,
                    command_line=command_line,
                    output_path=output_path,
                    log_path=log_path,
                    status=status,
                )

                stderr = stackwalker_data.get("mdsw_stderr", "").strip()
                if stderr:
                    if stderr.startswith("ERROR"):
                        indicator = stderr.split(" ")[1]
                    else:
                        indicator = ""

                    status_string = stackwalker_data.get("mdsw_status_string", "")
                    if indicator and status_string in ["OK", "unknown error"]:
                        stackwalker_data["mdsw_status_string"] = indicator
                        status.add_note(
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


class SymbolicateRule(Rule):
    """Runs symbolicate-stacks (Rust) and puts output in processed crash.

    Produces:

    * json_dump: symbolicate-stacks output converted to the json_dump structure
    * symbolicate_exit_code: process exit code
    * symbolicate_status_string:

      * "OK" if symbolicate-stacks exited 0 and produced a JSON object
      * "unknown error" otherwise; details are in the processor notes

    * symbolicate_success: bool
    * symbolicate_version: version of symbolicate-stacks
    * symbolicate_stderr: last 10 lines of symbolicate-stacks stderr

    Also adds processor notes.

    Emits:

    * processor.symbolicate.*

    """

    def __init__(
        self,
        symbols_urls=None,
        # This is the location it gets put in the Docker image
        command_path="/stackwalk-rust/symbolicate-stacks",
        command_line=(
            "{command_path} "
            + "--input-file={raw_crash_path} "
            + "--output-file={output_path} "
            + "'symbol_servers.breakpad = {symbols_urls}' "
            + "'symbol_servers.windows = {symbols_urls}' "
            + "'cache.directory = {symbol_cache_path}'"
        ),
        kill_timeout=600,
        symbol_cache_path="/tmp/symbols/symbolicate-stacks",
    ):
        super().__init__()

        # If kill_timeout is None, set it to 600--the default
        if kill_timeout is None:
            kill_timeout = 600

        self.symbols_urls = symbols_urls or []
        self.command_path = command_path
        self.command_line = command_line
        self.kill_timeout = kill_timeout
        self.symbol_cache_path = symbol_cache_path

        self.symbolicate_version = self.get_version()
        self.build_directories()

    def __repr__(self):
        keys = (
            "symbols_urls",
            "command_path",
            "command_line",
            "kill_timeout",
            "symbol_cache_path",
        )
        return self.generate_repr(keys=keys)

    def get_version(self):
        # symbolicate-stacks doesn't support --version yet, so run --help to make sure
        # the binary runs (to fail early at startup like MinidumpStackwalkRule does) and
        # get the version from the version.json file.
        # TODO: Update to match MinidumpStackwalkRule.get_version once it does. See
        # https://github.com/mozilla-services/socorro-stackwalk/pull/25#discussion_r4672118024
        command_line = f"{self.command_path} --help"
        ret = execute_process(command_line, timeout=self.kill_timeout)
        if ret["returncode"] != 0:
            raise CommandError(
                "SymbolicateRule: unknown error when getting version: "
                + f"{ret['returncode']} {ret['stdout']}"
            )

        name = os.path.basename(self.command_path)
        suffix = get_version_json_suffix(self.command_path)
        if not suffix:
            return f"{name} (unknown version)"
        # The version.json "sha" is the release tag, so use it as the version number too,
        # e.g. "symbolicate-stacks 0.4.0 (2026-11-20 0.4.0)".
        with open(self.command_path + ".version.json") as fp:
            sha = json.load(fp)["sha"]
        return f"{name} {sha} {suffix}"

    def build_directories(self):
        os.makedirs(self.symbol_cache_path, exist_ok=True)

    def expand_commandline(self, raw_crash_path, output_path):
        """Expands the command line parameters and returns the final command line

        :param raw_crash_path: the absolute path to the crash annotations file
        :param output_path: the absolute path to where the output will go

        :returns: command line as a string

        """
        # NOTE: If we ever add new configuration variables, we'll need
        # to add them here, too, otherwise they won't get expanded in the
        # command line.

        symbols_urls = json.dumps([url.strip() for url in self.symbols_urls])

        params = {
            # These come from config
            "command_path": self.command_path,
            "symbol_cache_path": json.dumps(self.symbol_cache_path),
            "symbols_urls": symbols_urls,
            # These are calculated
            "raw_crash_path": raw_crash_path,
            "output_path": output_path,
        }
        return self.command_line.format(**params)

    def run_symbolicate(self, crash_id, command_path, command_line, output_path, status):
        ret = execute_process(command_line, timeout=self.kill_timeout)
        returncode = ret["returncode"]

        # symbolicate-stacks logs to stderr rather than a log file
        log_data = ret["stderr"].decode("utf-8", errors="replace")

        # Truncate to 10 lines
        if log_data.count("\n") > 10:
            log_data = "\n".join(["..."] + log_data.splitlines()[-10:])

        # symbolicate-stacks output has no status field, so determine whether it
        # failed from the return code and whether the output is a JSON object
        output = {}
        failure_reason = None
        if returncode == 0:
            if os.path.exists(output_path):
                with open(output_path, "r") as fp:
                    output_raw = fp.read()

                try:
                    output = json.loads(output_raw)
                except Exception as exc:
                    failure_reason = f"non-json output: {exc}"
                    self.logger.debug(
                        "SymbolicateRule: %s: non-json output: %s",
                        command_path,
                        output_raw[:1000],
                    )

                if failure_reason is None and not isinstance(output, Mapping):
                    failure_reason = f"unexpected output: {str(output)[:200]}"
                    output = {}
            else:
                failure_reason = "missing output"

        # subprocess.run returns negative exit codes where the number is the signal
        # that killed the process; execute_process returns -9 on timeout
        elif returncode == -9:
            failure_reason = "timeout (SIGKILL)"
        elif returncode < 0:
            failure_reason = f"killed by signal {-returncode}"
        else:
            # 1 = symbolication failed, 101 = panic; details are in stderr
            failure_reason = f"failed: {returncode}"

        # Like MinidumpStackwalkRule, the status string is "OK" or "unknown error";
        # failure details only go in the processor note
        success = failure_reason is None
        status_string = "OK" if success else "unknown error"
        symbolicate_data = {
            # Raw symbolicate-stacks output; mapped into json_dump separately
            "output": output,
            "symbolicate_exit_code": returncode,
            "symbolicate_status_string": status_string,
            "symbolicate_success": success,
            "symbolicate_version": self.symbolicate_version,
            # NOTE: this may contain protected data
            "symbolicate_stderr": log_data,
        }

        if not success:
            msg = f"SymbolicateRule: symbolicate-stacks: {failure_reason}"
            status.add_note(msg)
            self.logger.warning("%s (%s)", msg, crash_id)

        METRICS.incr(
            "processor.symbolicate.run",
            tags=[
                "outcome:%s" % ("success" if success else "fail"),
                "exitcode:%s" % returncode,
            ],
        )

        return symbolicate_data

    def convert_to_json_dump(self, output):
        """Converts symbolicate-stacks output into the json_dump structure.

        symbolicate-stacks outputs data in the signature generation crash data schema.
        This moves the parts that signature generation and downstream rules read into
        the json_dump paths they read them from (json_dump is structured like
        minidump-stackwalk output). Keys missing from the output are omitted rather
        than included empty.

        :param output: parsed symbolicate-stacks output

        :returns: json_dump dict

        """
        json_dump = {}

        crash_info = {}
        if "reason" in output:
            crash_info["type"] = output["reason"]
        if "crashing_thread" in output:
            crash_info["crashing_thread"] = output["crashing_thread"]
        if crash_info:
            json_dump["crash_info"] = crash_info

        if "threads" in output:
            json_dump["threads"] = output["threads"]

        if "os" in output:
            json_dump["system_info"] = {"os": output["os"]}

        return json_dump

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        # Only crash pings for now; crash reports will be handled by
        # MinidumpStackwalkRule until CRINGE-456
        if processed_crash.get("submission_type") != "ping":
            return False

        stack_traces = raw_crash.get("StackTraces")
        if not stack_traces:
            # Java crashes don't have StackTraces, so only add a note for native
            # crashes
            is_java_crash = raw_crash.get("JavaException") or raw_crash.get(
                "JavaStackTrace"
            )
            if not is_java_crash:
                status.add_note("SymbolicateRule: StackTraces is missing")
            return False

        # symbolicate-stacks treats malformed StackTraces as empty and exits 0, so
        # check it's usable here
        try:
            parsed = json.loads(stack_traces)
        except (TypeError, ValueError) as exc:
            status.add_note(f"SymbolicateRule: StackTraces is not valid JSON: {exc}")
            return False

        if not isinstance(parsed, Mapping):
            status.add_note("SymbolicateRule: StackTraces is not a JSON object")
            return False

        return True

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        crash_id = raw_crash["uuid"]

        # Save crash annotations (which include StackTraces) to disk for
        # symbolicate-stacks to read
        raw_crash_path = os.path.join(tmpdir, f"{crash_id}.json")
        with open(raw_crash_path, "w") as fp:
            json.dump(raw_crash, fp)

        output_path = os.path.join(tmpdir, f"{crash_id}.symbolicate.json")
        command_line = self.expand_commandline(
            raw_crash_path=raw_crash_path,
            output_path=output_path,
        )

        symbolicate_data = self.run_symbolicate(
            crash_id=crash_id,
            command_path=self.command_path,
            command_line=command_line,
            output_path=output_path,
            status=status,
        )

        # The raw output is in the signature generation schema (see
        # https://github.com/mozilla/symbolicate-stacks/blob/029fef6b64c50912e7d98ae90b1c63f00234b808/README.md#output),
        # so convert it to json_dump rather than storing it as is. Like
        # MinidumpStackwalkRule, this sets json_dump even if symbolicate-stacks failed
        # (in which case it's {}).
        output = symbolicate_data.pop("output")
        processed_crash["json_dump"] = self.convert_to_json_dump(output)

        processed_crash.update(symbolicate_data)


class ThreadCountRule(Rule):
    """Copies thread_count from minidump-stackwalk output to processed crash"""

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        processed_crash["thread_count"] = glom(
            processed_crash, "json_dump.thread_count", default=None
        )

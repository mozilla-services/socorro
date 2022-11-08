# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import partial
from itertools import islice
import json
import re

from glom import glom

from .siglists_utils import get_signature_list_content
from .utils import (
    collapse,
    drop_bad_characters,
    drop_prefix_and_return_type,
    get_crashing_thread,
    override_values,
    parse_source_file,
    strip_leading_zeros,
)


SIGNATURE_MAX_LENGTH = 255
MAXIMUM_FRAMES_TO_CONSIDER = 40


def join_ignore_empty(delimiter, list_of_strings):
    return delimiter.join(x for x in list_of_strings if x)


class Rule:
    """Base class for Signature generation rules"""

    @property
    def name(self):
        # NOTE(willkg): In order for this to work in siggen and in Socorro, we can't
        # include the Python module path
        return self.__class__.__name__

    def predicate(self, crash_data, result):
        """Whether or not to run this rule

        :arg dict crash_data: the data to use to generate the signature
        :arg dict result: the current signature generation result

        :returns: True or False

        """
        return True

    def action(self, crash_data, result):
        """Runs the rule against the data

        .. Note::

           This modifies ``result`` in place.

        :arg dict crash_data: the data to use to generate the signature
        :arg dict result: the current signature generation result

        :returns: True

        """
        return True


class CSignatureTool:
    """Generates signature from C/C++/Rust stacks.

    This is the class for signature generation tools that work on C/C++/Rust stacks. It
    normalizes frames and then runs them through the siglists to determine which frames
    should be part of the signature.

    """

    hang_prefixes = {-1: "hang", 1: "chromehang"}

    def __init__(self, datadir=None):
        """
        :param datadir: the directory holding signature lists to use or ``None`` to
            use included signature lists
        """
        super().__init__()

        self.datadir = datadir
        if datadir is not None:
            get_contents = partial(get_signature_list_content, source=datadir)
        else:
            get_contents = get_signature_list_content

        self.irrelevant_signature_re = self.build_re(
            get_contents("irrelevant_signature_re")
        )
        self.prefix_signature_re = self.build_re(get_contents("prefix_signature_re"))
        self.signatures_with_line_numbers_re = self.build_re(
            get_contents("signatures_with_line_numbers_re")
        )
        self.signature_sentinels = get_contents("signature_sentinels")

        self.collapse_arguments = True

        self.fixup_space = re.compile(r" (?=[\*&,])")
        self.fixup_comma = re.compile(r",(?! )")
        self.fixup_hash = re.compile(r"::h[0-9a-fA-F]+$")
        self.fixup_lambda_numbers = re.compile(r"::\$_\d+::")

    def build_re(self, lines):
        return re.compile("|".join(lines))

    def normalize_rust_function(self, function, line):
        """Normalizes a single Rust frame with a function."""
        # Drop the prefix and return type if there is any
        function = drop_prefix_and_return_type(function)

        # Collapse types
        function = collapse(
            function,
            open_string="<",
            close_string=">",
            replacement="<T>",
            exceptions=(" as ",),
        )

        # Collapse arguments
        if self.collapse_arguments:
            function = collapse(
                function, open_string="(", close_string=")", replacement=""
            )

        if self.signatures_with_line_numbers_re.match(function):
            function = f"{function}:{line}"

        # Remove spaces before all stars, ampersands, and commas
        function = self.fixup_space.sub("", function)

        # Ensure a space after commas
        function = self.fixup_comma.sub(", ", function)

        # Remove rust-generated uniqueness hashes
        function = self.fixup_hash.sub("", function)

        return function

    def normalize_cpp_function(self, function, line):
        """Normalizes a single cpp frame with a function"""
        # Drop member function cv/ref qualifiers like const, const&, &, and &&
        for ref in ("const", "const&", "&&", "&"):
            if function.endswith(ref):
                function = function[: -len(ref)].strip()

        # Convert `anonymous namespace' to (anonymous namespace)

        # Drop the prefix and return type if there is any if it's not operator
        # overloading--operator overloading syntax doesn't have the things
        # we're dropping here and can look curious, so don't try
        if "::operator" not in function:
            function = drop_prefix_and_return_type(function)

        # Normalize `anonymous namespace' to (anonymous namespace). bug #1672847
        function = function.replace("`anonymous namespace'", "(anonymous namespace)")

        # Remove lambda number from frames. bug #1688249
        function = self.fixup_lambda_numbers.sub("::$::", function)

        # Collapse types
        #
        # NOTE(willkg): The " in " is for handling "<unknown in foobar.dll>". bug
        # #1685178
        function = collapse(
            function,
            open_string="<",
            close_string=">",
            replacement="<T>",
            exceptions=("name omitted", "IPC::ParamTraits", " in "),
        )

        # Collapse arguments
        if self.collapse_arguments:
            function = collapse(
                function,
                open_string="(",
                close_string=")",
                replacement="",
                exceptions=("anonymous namespace", "operator"),
            )

        # Remove PGO cold block labels like "[clone .cold.222]". bug #1397926
        if "clone .cold" in function:
            function = collapse(
                function, open_string="[", close_string="]", replacement=""
            )

        if self.signatures_with_line_numbers_re.match(function):
            function = f"{function}:{line}"

        # Remove spaces before all stars, ampersands, and commas
        function = self.fixup_space.sub("", function)

        # Ensure a space after commas
        function = self.fixup_comma.sub(", ", function)

        return function

    def normalize_frame(
        self,
        module=None,
        function=None,
        file=None,
        line=None,
        module_offset=None,
        offset=None,
        unloaded_modules=None,
    ):
        """Normalizes a single frame

        Returns a structured conglomeration of the input parameters to serve as a
        signature. The parameter names of this function reflect the exact names of the
        fields from the JSON MDSW frame output. This allows this function to be invoked
        by passing a frame as ``**a_frame``.

        """
        if function:
            # If there's a filename and it ends in .rs, then normalize using
            # Rust rules
            if file and (parse_source_file(file) or "").endswith(".rs"):
                return self.normalize_rust_function(function=function, line=line)

            # Otherwise normalize it with C/C++ rules
            return self.normalize_cpp_function(function=function, line=line)

        # If there's a file and line number, use that
        if file and line:
            filename = file.rstrip("/\\")
            if "\\" in filename:
                file = filename.rsplit("\\")[-1]
            else:
                file = filename.rsplit("/")[-1]
            return f"{file}#{line}"

        # If there's an offset and no module/module_offset, use that
        if not module and not module_offset:
            if unloaded_modules:
                # Use the first unloaded module and the offset or "0"
                unloaded_module = unloaded_modules[0]
                unloaded_module_module = unloaded_module.get("module")
                unloaded_module_offsets = unloaded_module.get("offsets")
                if unloaded_module_module and unloaded_module_offsets:
                    return "(unloaded {}@{})".format(
                        unloaded_module_module,
                        strip_leading_zeros(unloaded_module_offsets[0]),
                    )
                elif unloaded_module_module:
                    return "(unloaded {})".format(unloaded_module_module)

            if offset:
                return f"@{strip_leading_zeros(offset)}"

        # Return module/module_offset
        return "{}@{}".format(module or "", strip_leading_zeros(module_offset))

    def frame_generator(self, frames):
        """Yields frames one at a time from a list of frames

        Note: this treats inlines as individual frames and yields those when they're
        available.

        :arg frames: list of frame dicts

        :returns: generator of frame data for normalization

        """
        for frame in frames:
            inlines = frame.get("inlines") or []
            for inline in inlines:
                yield {
                    "module": frame.get("module"),
                    "function": inline.get("function"),
                    "file": inline.get("file"),
                    "line": inline.get("line"),
                    "module_offset": frame.get("module_offset"),
                    "offset": frame.get("offset"),
                }

            yield {
                "module": frame.get("module"),
                "function": frame.get("function"),
                "file": frame.get("file"),
                "line": frame.get("line"),
                "module_offset": frame.get("module_offset"),
                "offset": frame.get("offset"),
                # NOTE(gsvelto): unloaded modules can only appear in non-inlined frames
                "unloaded_modules": frame.get("unloaded_modules"),
            }

    def create_frame_list(self, thread_data, make_modules_lower_case=False):
        """Takes thread data and builds a list of frames

        Note: this treats inlines as individual frames.

        :arg thread_data: dict of thread data
        :arg make_modules_lower_case: whether or not to lowercase module

        :returns: list of normalized frames

        """
        normalized_frames = []
        frames = thread_data.get("frames", [])
        for frame in islice(self.frame_generator(frames), MAXIMUM_FRAMES_TO_CONSIDER):
            # Bug #1544246. In Rust 1.34, the panic symbols are missing the module in
            # symbols files. This fixes that by adding the module.
            frame = fix_missing_module(frame)

            if make_modules_lower_case and frame.get("module"):
                frame["module"] = frame["module"].lower()

            normalized_frame = self.normalize_frame(**frame)
            normalized_frames.append(normalized_frame)
        return normalized_frames

    def generate(self, source_list, crashed_thread=None, delimiter=" | "):
        """Iterate over frames in the crash stack and generate a signature.

        First, we look for a sentinel frame and if we find one, we start with that.
        Otherwise we start at the beginning.

        Then each frame in the stack is handled like this:

        * a prefix of a relevant frame: Append this element to the signature
        * a relevant frame: Append this element and stop looking
        * irrelevant: Append this element only after seeing a prefix frame

        The signature is a ' | ' separated string of normalized frame names.

        """
        notes = []
        debug_notes = []

        if self.datadir is None:
            debug_notes.append("using included signature lists")
        else:
            debug_notes.append(f"using signature lists from {self.datadir}")

        # Shorten source_list to the first sentinel found
        sentinel_locations = []
        for a_sentinel in self.signature_sentinels:
            if type(a_sentinel) == tuple:
                a_sentinel, condition_fn = a_sentinel
                if not condition_fn(source_list):
                    continue
            try:
                sentinel_locations.append(source_list.index(a_sentinel))
            except ValueError:
                pass

        if sentinel_locations:
            min_index = min(sentinel_locations)
            debug_notes.append(
                'sentinel; starting at "{}" index {}'.format(
                    source_list[min_index], min_index
                )
            )
            source_list = source_list[min_index:]

        # Get all the relevant frame signatures. Note that these function signatures
        # have already been normalized at this point.
        new_signature_list = []
        for a_signature in source_list:
            # If the signature matches the irrelevant signatures regex, skip to the next frame.
            if self.irrelevant_signature_re.match(a_signature):
                debug_notes.append(f'irrelevant; ignoring: "{a_signature}"')
                continue

            # If the frame signature is a dll, remove the @xxxxx part.
            if (
                not a_signature.startswith("(unloaded")
                and ".dll" in a_signature.lower()
            ):
                a_signature = a_signature.split("@")[0]

                # If this trimmed DLL signature is the same as the previous frame's, skip it.
                if new_signature_list and a_signature == new_signature_list[-1]:
                    continue

            new_signature_list.append(a_signature)

            # If the signature does not match the prefix signatures regex, then it is the last
            # one we add to the list.
            if not self.prefix_signature_re.match(a_signature):
                debug_notes.append(f'not a prefix; stop: "{a_signature}"')
                break

            debug_notes.append(f'prefix; continue iterating: "{a_signature}"')

        signature = delimiter.join(new_signature_list)

        # Handle empty signatures to explain why we failed generating them.
        if signature == "" or signature is None:
            if crashed_thread is None:
                notes.append("CSignatureTool: no crashing thread identified")
                signature = "EMPTY: no crashing thread identified"

            else:
                notes.append(
                    f"CSignatureTool: no frame data for crashing thread ({crashed_thread})"
                )
                if source_list:
                    # The frames were probably all irrelevant, so pick the first one.
                    signature = source_list[0]
                else:
                    # There wasn't any frame data to look at.
                    signature = "EMPTY: no frame data available"

        return signature, notes, debug_notes


class JavaSignatureTool:
    """This is the signature generation class for Java signatures."""

    # The max length of a java exception description--if it's longer than this,
    # drop it
    DESCRIPTION_MAX_LENGTH = 255

    java_line_number_killer = re.compile(r"\.java\:\d+\)$")
    java_hex_addr_killer = re.compile(r"@[0-9a-f]{8}")

    def generate(self, source, delimiter=": "):
        if not isinstance(source, str):
            return (
                "EMPTY: Java stack trace not in expected format",
                ["JavaSignatureTool: stack trace not in expected format"],
                [],
            )

        source_list = [x.strip() for x in source.splitlines()]
        if not source_list:
            return (
                "EMPTY: Java stack trace not in expected format",
                ["JavaSignatureTool: stack trace not in expected format"],
                [],
            )

        notes = []
        debug_notes = []

        try:
            java_exception_class, description = source_list[0].split(":", 1)
            java_exception_class = java_exception_class.strip()

            description = self.java_hex_addr_killer.sub("@<addr>", description)
            description = description.strip()

        except ValueError:
            # It throws a ValueError if the first line doesn't have a ":"
            java_exception_class = source_list[0]
            description = ""
            notes.append(
                "JavaSignatureTool: stack trace line 1 is not in the expected format"
            )

        try:
            java_method = self.java_line_number_killer.sub(".java)", source_list[1])
            if not java_method:
                notes.append("JavaSignatureTool: stack trace line 2 is empty")
        except IndexError:
            notes.append("JavaSignatureTool: stack trace line 2 is missing")
            java_method = ""

        # An error in an earlier version of this code resulted in the colon
        # being left out of the division between the description and the
        # java_method if the description didn't end with "<addr>". This code
        # perpetuates that error while correcting the "<addr>" placement when
        # it is not at the end of the description. See Bug 865142 for a
        # discussion of the issues.
        if description.endswith("<addr>"):
            # at which time the colon placement error is to be corrected
            # just use the following line as the replacement for this entire
            # if/else block
            signature = join_ignore_empty(
                delimiter, (java_exception_class, description, java_method)
            )
        else:
            description_java_method_phrase = join_ignore_empty(
                " ", (description, java_method)
            )
            signature = join_ignore_empty(
                delimiter, (java_exception_class, description_java_method_phrase)
            )

        if len(signature) > self.DESCRIPTION_MAX_LENGTH:
            signature = delimiter.join((java_exception_class, java_method))
            notes.append(
                "JavaSignatureTool: dropped Java exception description due to length"
            )

        return signature, notes, debug_notes


# Map of (file, function) -> fixed function for Rust 1.34 symbols that are
# missing module.
FILE_FUNCTION_TO_FUNCTION = {
    (
        "src/liballoc/raw_vec.rs",
        "capacity_overflow",
    ): "alloc::raw_vec::capacity_overflow",
    ("src/libcore/option.rs", "expect_failed"): "core::option::expect_failed",
    (
        "src/libcore/panicking.rs",
        "panic_bounds_check",
    ): "core::panicking::panic_bounds_check",
    ("src/libcore/panicking.rs", "panic_fmt"): "core::panicking::panic_fmt",
    ("src/libcore/panicking.rs", "panic"): "core::panicking::panic",
    (
        "src/libcore/slice/mod.rs",
        "slice_index_order_fail",
    ): "core::slice::slice_index_order_fail",
    ("src/libstd/panicking.rs", "begin_panic_fmt"): "std::panicking::begin_panic_fmt",
    (
        "src/libstd/panicking.rs",
        "continue_panic_fmt",
    ): "std::panicking::continue_panic_fmt",
    (
        "src/libstd/panicking.rs",
        "rust_panic_with_hook",
    ): "std::panicking::rust_panic_with_hook",
}


def fix_missing_module(frame):
    """Fixes the module for panic symbols generated by Rust 1.34.

    For example, this turns "panic" into "core::panicking::panic". This allows
    signature sentinels to work.

    See bug #1544246

    """
    if "file" not in frame or "function" not in frame:
        return frame
    fn = parse_source_file(frame.get("file", ""))
    fixed_function = FILE_FUNCTION_TO_FUNCTION.get((fn, frame["function"]))
    if fixed_function:
        frame["function"] = fixed_function

    return frame


class SignatureGenerationRule(Rule):
    """Generates a signature based on stack frames.

    For Java crashes, this generates a basic signature using stack frames.

    For C/C++/Rust crashes, this generates a more robust signature using
    normalized versions of stack frames augmented by the contents of the
    signature lists.

    Rough signature list rules (there are more details in the siglists README):

    1. Walk the frames looking for a "signature sentinel" which becomes the
       first item in the signature.
    2. Continue walking frames.

       1. If the frame is in the "irrelevant" list, ignore it and
          continue.
       2. If the frame is in the "prefix" list, add it to the signature
          and continue.
       3. If the frame isn't in either list, stop walking frames.

    3. Signature is generated by joining those frames with " | " between
       them.

    If it's a C/C++/Rust signature, this rule also adds to ``result.extra``:

    * ``normalized_frames``: the list of normalized frames
    * ``proto_signature``: a ``" | "`` delimited string of the normalized
      frames

    :param signature_list_dir: path to the directory with the signature lists to use or
        ``None`` if you want to use the included ones

    """

    def __init__(self, signature_list_dir=None):
        super().__init__()
        self.java_signature_tool = JavaSignatureTool()
        self.c_signature_tool = CSignatureTool(datadir=signature_list_dir)

    def action(self, crash_data, result):
        # If this is a Java crash, then generate a Java signature
        if crash_data.get("java_stack_trace"):
            result.debug(self.name, "using JavaSignatureTool")
            signature, notes, debug_notes = self.java_signature_tool.generate(
                crash_data["java_stack_trace"], delimiter=": "
            )
            for note in notes:
                result.info(self.name, note)
            for note in debug_notes:
                result.debug(self.name, note)
            result.set_signature(self.name, signature)
            return True

        result.debug(self.name, "using CSignatureTool")
        try:
            crashing_thread = get_crashing_thread(crash_data)

            # If we have a thread to look at, pull the frames for that.
            # Otherwise we don't have frames to use.
            if crashing_thread is not None:
                signature_list = self.c_signature_tool.create_frame_list(
                    glom(crash_data, "threads.%d" % crashing_thread, default={}),
                    crash_data.get("os") == "Windows NT",
                )

            else:
                signature_list = []

        except (KeyError, IndexError) as exc:
            result.note("No crashing frames found because of %s", exc)
            signature_list = []

        signature, notes, debug_notes = self.c_signature_tool.generate(
            signature_list,
            crashing_thread,
        )

        if signature_list:
            # Capture the proto_signature which gets indexed in Elasticsearch
            # and is searchable
            result.extra["proto_signature"] = " | ".join(signature_list)
            # Capture the normalized_frames for users of signature generation
            result.extra["normalized_frames"] = signature_list
        for note in notes:
            result.info(self.name, note)
        for note in debug_notes:
            result.debug(self.name, note)
        if signature:
            result.set_signature(self.name, signature)

        return True


class StackOverflowSignature(Rule):
    """Prepends ``stackoverflow``

    See bug #1796389.

    """

    # These reason values indicate a stackoverflow
    stackoverflow_reason = [
        "EXCEPTION_STACK_OVERFLOW",
    ]

    def predicate(self, crash_data, result):
        # Check the reason to see if it's one of a few values that indicate a
        # stackoverflow
        reason = crash_data.get("reason", None)
        if reason in self.stackoverflow_reason:
            return True

        return False

    def action(self, crash_data, result):
        result.set_signature(self.name, f"stackoverflow | {result.signature}")
        return True


class OOMSignature(Rule):
    """Prepends ``OOM | <size>`` to signatures for OOM crashes.

    See bug #1007530.

    """

    # Fragments that are in the signature that indicate this is an OOM
    signature_fragments = (
        "NS_ABORT_OOM",
        "mozalloc_handle_oom",
        "CrashAtUnhandlableOOM",
        "AutoEnterOOMUnsafeRegion",
        "alloc::oom::oom",
    )

    # These reason values indicate an OOM
    oom_reason = [
        "STATUS_FATAL_MEMORY_EXHAUSTION",
        "STATUS_NO_MEMORY",
    ]

    # These last_error_value values indicate an OOM
    oom_last_error_value = [
        "ERROR_COMMITMENT_LIMIT",
        "ERROR_NOT_ENOUGH_MEMORY",
    ]

    def predicate(self, crash_data, result):
        if crash_data.get("oom_allocation_size"):
            return True

        signature = result.signature
        if not signature:
            return False

        for a_signature_fragment in self.signature_fragments:
            if a_signature_fragment in signature:
                return True

        # Check the last_error_value of the crashing thread to see if it's
        # ERROR_COMMITMENT_LIMIT which indicates this is an OOM
        crashing_thread = get_crashing_thread(crash_data)
        thread = glom(crash_data, "threads.%d" % crashing_thread, default={})
        if thread:
            last_error_value = thread.get("last_error_value", "")
            if last_error_value in self.oom_last_error_value:
                return True

        # Check the reason to see if it's one of a few values that indicate an OOM
        reason = crash_data.get("reason", None)
        if reason in self.oom_reason:
            return True

        return False

    def action(self, crash_data, result):
        try:
            size = int(crash_data.get("oom_allocation_size"))
        except (TypeError, AttributeError, KeyError):
            result.set_signature(self.name, f"OOM | unknown | {result.signature}")
            return True

        if size <= 262144:  # 256K
            result.set_signature(self.name, "OOM | small")
        else:
            result.set_signature(self.name, f"OOM | large | {result.signature}")
        return True


class BadHardware(Rule):
    """Prepends ``bad hardware`` to signatures that are from bad hardware.

    See bug #1733904.

    """

    # These reason value substrings indicate an error caused by bad hardware
    bad_hardware_reason = [
        "STATUS_DEVICE_DATA_ERROR",
    ]

    def predicate(self, crash_data, result):
        reason = crash_data.get("reason", None)
        if not reason:
            return False

        for possibility in self.bad_hardware_reason:
            if possibility in reason:
                return True

        return False

    def action(self, crash_data, result):
        result.set_signature(self.name, f"bad hardware | {result.signature}")
        return True


class AbortSignature(Rule):
    """Prepends abort message to signature.

    See bug #803779.

    """

    def predicate(self, crash_data, result):
        return bool(crash_data.get("abort_message"))

    def action(self, crash_data, result):
        abort_message = crash_data["abort_message"]

        if "###!!! ABORT: file " in abort_message:
            # This is an abort message that contains no interesting
            # information. We just want to put the "Abort" marker in the
            # signature.
            result.set_signature(self.name, f"Abort | {result.signature}")
            return True

        if "###!!! ABORT:" in abort_message:
            # Recent crash reports added some irrelevant information at the
            # beginning of the abort message. We want to remove that and keep
            # just the actual abort message.
            abort_message = abort_message.split("###!!! ABORT:", 1)[1]

        if ": file " in abort_message:
            # Abort messages contain a file name and a line number. Since
            # those are very likely to change between builds, we want to
            # remove those parts from the signature.
            abort_message = abort_message.split(": file ", 1)[0]

        if "unable to find a usable font" in abort_message:
            # "unable to find a usable font" messages include a parenthesized localized message. We
            # want to remove that. Bug #1385966
            open_paren = abort_message.find("(")
            if open_paren != -1:
                end_paren = abort_message.rfind(")")
                if end_paren != -1:
                    abort_message = (
                        abort_message[:open_paren] + abort_message[end_paren + 1 :]
                    )

        abort_message = drop_bad_characters(abort_message).strip()

        if len(abort_message) > 80:
            abort_message = abort_message[:77] + "..."

        result.set_signature(self.name, f"Abort | {abort_message} | {result.signature}")
        return True


class SigFixWhitespace(Rule):
    """Fix whitespace in signatures.

    This does the following:

    * trims leading and trailing whitespace
    * converts all non-space whitespace characters to space
    * reduce consecutive spaces to a single space

    """

    WHITESPACE_RE = re.compile(r"\s")
    CONSECUTIVE_WHITESPACE_RE = re.compile(r"\s\s+")

    def action(self, crash_data, result):
        original_sig = result.signature

        # Trim leading and trailing whitespace
        sig = original_sig.strip()

        # Convert all non-space whitespace characters into spaces
        sig = self.WHITESPACE_RE.sub(" ", sig)

        # Reduce consecutive spaces to a single space
        sig = self.CONSECUTIVE_WHITESPACE_RE.sub(" ", sig)

        if sig != original_sig:
            result.set_signature(self.name, sig)
        return True


class SigTruncate(Rule):
    """Truncates signatures down to SIGNATURE_MAX_LENGTH characters."""

    def predicate(self, crash_data, result):
        return len(result.signature) > SIGNATURE_MAX_LENGTH

    def action(self, crash_data, result):
        max_length = SIGNATURE_MAX_LENGTH - 3
        result.set_signature(self.name, "{}...".format(result.signature[:max_length]))
        result.info(self.name, "SigTrunc: signature truncated due to length")
        return True


class StackwalkerErrorSignatureRule(Rule):
    """Appends minidump-stackwalker error to signature."""

    def predicate(self, crash_data, result):
        return bool(
            result.signature.startswith("EMPTY")
            and crash_data.get("mdsw_status_string")
        )

    def action(self, crash_data, result):
        result.set_signature(
            self.name,
            "{}; {}".format(result.signature, crash_data["mdsw_status_string"]),
        )
        return True


class SignatureRunWatchDog(Rule):
    """Prepends "shutdownhang" to signature for shutdown hang crashes."""

    def __init__(self):
        super().__init__()
        self.signature_generation_rule = SignatureGenerationRule()

    def predicate(self, crash_data, result):
        return "RunWatchdog" in result.signature

    def action(self, crash_data, result):
        # For shutdownhang crashes, we need to use thread 0 instead of the crashing
        # thread. The reason is because those crashes happen artificially when thread 0
        # gets stuck. So whatever the crashing thread is, we don't care about it and
        # only want to know what was happening in thread 0 when it got stuck.
        with override_values(crash_data, {"crashing_thread": 0}) as crash_data:
            ret = self.signature_generation_rule.action(crash_data, result)

        result.set_signature(self.name, f"shutdownhang | {result.signature}")
        return ret


class SignatureShutdownTimeout(Rule):
    """Replaces signature with async_shutdown_timeout message.

    This supports AsyncShutdownTimeout annotation values with the following structure::

        {
            "phase": <str>,
            "conditions": [
                {
                    "name": <str>,
                    ...
                }
            ]
        }


    """

    def predicate(self, crash_data, result):
        return bool(crash_data.get("async_shutdown_timeout"))

    def action(self, crash_data, result):
        parts = ["AsyncShutdownTimeout"]
        try:
            shutdown_data = json.loads(crash_data["async_shutdown_timeout"])
            if isinstance(shutdown_data.get("phase"), str):
                parts.append(shutdown_data["phase"])
            else:
                parts.append("(unknown)")

            conditions = [
                # NOTE(willkg): The AsyncShutdownTimeout notation condition can either
                # be a string that looks like a "name" or a dict with a "name" in it.
                #
                # This handles both variations.
                c["name"] if isinstance(c, dict) else c
                for c in shutdown_data.get("conditions") or []
            ]
            if conditions:
                conditions.sort()
                parts.append(",".join(conditions))
            else:
                parts.append("(none)")
        except (ValueError, KeyError) as exc:
            parts.append("UNKNOWN")
            result.info(self.name, "Error parsing AsyncShutdownTimeout: %s", exc)

        new_sig = " | ".join(parts)
        result.info(
            self.name,
            'Signature replaced with a Shutdown Timeout signature, was: "%s"',
            result.signature,
        )
        result.set_signature(self.name, new_sig)
        return True


class SignatureIPCChannelError(Rule):
    """Stomps on signature with shutdownkill signature

    Either "IPCError-browser | ShutDownKill" or "IPCError-content | ShutDownKill".

    """

    def predicate(self, crash_data, result):
        return bool(crash_data.get("ipc_channel_error"))

    def action(self, crash_data, result):
        minidumps = crash_data.get("additional_minidumps") or []
        if "upload_file_minidump_browser" in minidumps:
            new_sig = "IPCError-browser | {}"
        else:
            new_sig = "IPCError-content | {}"
        new_sig = new_sig.format(crash_data["ipc_channel_error"][:100])
        result.info(self.name, "IPC Channel Error stomped on signature")
        result.set_signature(self.name, new_sig)
        return True


class SignatureIPCMessageName(Rule):
    """Appends ipc_message_name to signature."""

    def predicate(self, crash_data, result):
        return bool(crash_data.get("ipc_message_name"))

    def action(self, crash_data, result):
        result.set_signature(
            self.name,
            "{} | IPC_Message_Name={}".format(
                result.signature, crash_data["ipc_message_name"]
            ),
        )
        return True


class SignatureParentIDNotEqualsChildID(Rule):
    """Stomp on the signature if moz_crash_reason is ``parentBuildID != childBuildID``.

    In the case where the assertion fails, then the parent buildid and the child buildid are
    different. This causes a lot of strangeness particularly in symbolification, so the signatures
    end up as junk. Instead, we want to bucket all these together so we replace the signature.

    """

    def predicate(self, crash_data, result):
        value = "MOZ_RELEASE_ASSERT(parentBuildID == childBuildID)"
        return crash_data.get("moz_crash_reason") == value

    def action(self, crash_data, result):
        result.info(
            self.name,
            'Signature replaced with MOZ_RELEASE_ASSERT, was: "%s"',
            result.signature,
        )

        # The MozCrashReason lists the assertion that failed, so we put "!=" in the signature
        result.set_signature(self.name, "parentBuildID != childBuildID")
        return True

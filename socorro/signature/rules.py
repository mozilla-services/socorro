# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from itertools import islice
import re

from glom import glom
import six
import ujson

from . import siglists_utils
from .utils import (
    collapse,
    drop_bad_characters,
    drop_prefix_and_return_type,
    parse_source_file,
)


SIGNATURE_MAX_LENGTH = 255
MAXIMUM_FRAMES_TO_CONSIDER = 40


class Rule(object):
    """Base class for Signature generation rules"""
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


class SignatureTool(object):
    """Stack walking signature generator base class

    This defines the interface for classes that take a stack and generate a
    signature from it.

    Subclasses should implement the ``_do_generate`` method.

    """

    def __init__(self, quit_check_callback=None):
        self.quit_check_callback = quit_check_callback

    def generate(self, source_list, hang_type=0, crashed_thread=None, delimiter=' | '):
        signature, signature_notes = self._do_generate(
            source_list,
            hang_type,
            crashed_thread,
            delimiter
        )

        return signature, signature_notes

    def _do_generate(self, source_list, hang_type, crashed_thread, delimiter):
        raise NotImplementedError


class CSignatureTool(SignatureTool):
    """Generates signature from C/C++/Rust stacks.

    This is the class for signature generation tools that work on breakpad
    C/C++ stacks. It normalizes frames and then runs them through the siglists
    to determine which frames should be part of the signature.

    """

    hang_prefixes = {
        -1: "hang",
        1: "chromehang"
    }

    def __init__(self, quit_check_callback=None):
        super(CSignatureTool, self).__init__(quit_check_callback)

        self.irrelevant_signature_re = re.compile(
            '|'.join(siglists_utils.IRRELEVANT_SIGNATURE_RE)
        )
        self.prefix_signature_re = re.compile(
            '|'.join(siglists_utils.PREFIX_SIGNATURE_RE)
        )
        self.signatures_with_line_numbers_re = re.compile(
            '|'.join(siglists_utils.SIGNATURES_WITH_LINE_NUMBERS_RE)
        )
        self.trim_dll_signature_re = re.compile(
            '|'.join(siglists_utils.TRIM_DLL_SIGNATURE_RE)
        )
        self.signature_sentinels = siglists_utils.SIGNATURE_SENTINELS

        self.collapse_arguments = True

        self.fixup_space = re.compile(r' (?=[\*&,])')
        self.fixup_comma = re.compile(r',(?! )')
        self.fixup_hash = re.compile(r'::h[0-9a-fA-F]+$')

    def normalize_rust_function(self, function, line):
        """Normalizes a single rust frame with a function"""
        # Drop the prefix and return type if there is any
        function = drop_prefix_and_return_type(function)

        # Collapse types
        function = collapse(
            function,
            open_string='<',
            close_string='>',
            replacement='<T>',
            exceptions=(' as ',)
        )

        # Collapse arguments
        if self.collapse_arguments:
            function = collapse(
                function,
                open_string='(',
                close_string=')',
                replacement=''
            )

        if self.signatures_with_line_numbers_re.match(function):
            function = "%s:%s" % (function, line)

        # Remove spaces before all stars, ampersands, and commas
        function = self.fixup_space.sub('', function)

        # Ensure a space after commas
        function = self.fixup_comma.sub(', ', function)

        # Remove rust-generated uniqueness hashes
        function = self.fixup_hash.sub('', function)

        return function

    def normalize_cpp_function(self, function, line):
        """Normalizes a single cpp frame with a function"""
        # If the function ends in "const", drop that
        if function.endswith(' const'):
            function = function[:-6]

        # Drop the prefix and return type if there is any
        function = drop_prefix_and_return_type(function)

        # Collapse types
        function = collapse(
            function,
            open_string='<',
            close_string='>',
            replacement='<T>',
            exceptions=('name omitted', 'IPC::ParamTraits')
        )

        # Collapse arguments
        if self.collapse_arguments:
            function = collapse(
                function,
                open_string='(',
                close_string=')',
                replacement='',
                exceptions=('anonymous namespace', 'operator')
            )
        # Remove PGO cold block labels like "[clone .cold.222]". bug #1397926
        if 'clone .cold' in function:
            function = collapse(
                function,
                open_string='[',
                close_string=']',
                replacement=''
            )
        if self.signatures_with_line_numbers_re.match(function):
            function = "%s:%s" % (function, line)

        # Remove spaces before all stars, ampersands, and commas
        function = self.fixup_space.sub('', function)

        # Ensure a space after commas
        function = self.fixup_comma.sub(', ', function)

        return function

    def normalize_frame(
        self,
        module=None,
        function=None,
        file=None,
        line=None,
        module_offset=None,
        offset=None,
        normalized=None,
        **kwargs  # eat any extra kwargs passed in
    ):
        """Normalizes a single frame

        Returns a structured conglomeration of the input parameters to serve as
        a signature. The parameter names of this function reflect the exact
        names of the fields from the jsonMDSW frame output. This allows this
        function to be invoked by passing a frame as ``**a_frame``.

        Sometimes, a frame may already have a normalized version cached. If
        that exists, return it instead.

        """
        # If there's a cached normalized value, use that so we don't spend time
        # figuring it out again
        if normalized is not None:
            return normalized

        if function:
            # If there's a filename and it ends in .rs, then normalize using
            # Rust rules
            if file and (parse_source_file(file) or '').endswith('.rs'):
                return self.normalize_rust_function(
                    function=function,
                    line=line
                )

            # Otherwise normalize it with C/C++ rules
            return self.normalize_cpp_function(
                function=function,
                line=line
            )

        # If there's a file and line number, use that
        if file and line:
            filename = file.rstrip('/\\')
            if '\\' in filename:
                file = filename.rsplit('\\')[-1]
            else:
                file = filename.rsplit('/')[-1]
            return '%s#%s' % (file, line)

        # If there's an offset and no module/module_offset, use that
        if not module and not module_offset and offset:
            return "@%s" % offset

        # Return module/module_offset
        return '%s@%s' % (module or '', module_offset)

    def _do_generate(self, source_list, hang_type, crashed_thread, delimiter=' | '):
        """
        each element of signatureList names a frame in the crash stack; and is:
          - a prefix of a relevant frame: Append this element to the signature
          - a relevant frame: Append this element and stop looking
          - irrelevant: Append this element only after seeing a prefix frame
        The signature is a ' | ' separated string of frame names.
        """
        signature_notes = []

        # shorten source_list to the first signatureSentinel
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
            source_list = source_list[min(sentinel_locations):]

        # Get all the relevant frame signatures. Note that these function signatures
        # have already been normalized at this point.
        new_signature_list = []
        for a_signature in source_list:
            # If the signature matches the irrelevant signatures regex, skip to the next frame.
            if self.irrelevant_signature_re.match(a_signature):
                continue

            # If the signature matches the trim dll signatures regex, rewrite it to remove all but
            # the module name.
            if self.trim_dll_signature_re.match(a_signature):
                a_signature = a_signature.split('@')[0]

                # If this trimmed DLL signature is the same as the previous frame's, we do not want
                # to add it.
                if new_signature_list and a_signature == new_signature_list[-1]:
                    continue

            new_signature_list.append(a_signature)

            # If the signature does not match the prefix signatures regex, then it is the last
            # one we add to the list.
            if not self.prefix_signature_re.match(a_signature):
                break

        # Add a special marker for hang crash reports.
        if hang_type:
            new_signature_list.insert(0, self.hang_prefixes[hang_type])

        signature = delimiter.join(new_signature_list)

        # Handle empty signatures to explain why we failed generating them.
        if signature == '' or signature is None:
            if crashed_thread is None:
                signature_notes.append(
                    "CSignatureTool: No signature could be created because we do not know which "
                    "thread crashed"
                )
                signature = "EMPTY: no crashing thread identified"
            else:
                signature_notes.append(
                    "CSignatureTool: No proper signature could be created because no good data "
                    "for the crashing thread (%s) was found" % crashed_thread
                )
                try:
                    signature = source_list[0]
                except IndexError:
                    signature = "EMPTY: no frame data available"

        return signature, signature_notes


class JavaSignatureTool(SignatureTool):
    """This is the signature generation class for Java signatures."""

    # The max length of a java exception description--if it's longer than this,
    # drop it
    DESCRIPTION_MAX_LENGTH = 255

    java_line_number_killer = re.compile(r'\.java\:\d+\)$')
    java_hex_addr_killer = re.compile(r'@[0-9a-f]{8}')

    @staticmethod
    def join_ignore_empty(delimiter, list_of_strings):
        return delimiter.join(x for x in list_of_strings if x)

    def _do_generate(self, source, hang_type_unused=0, crashed_thread_unused=None, delimiter=': '):
        signature_notes = []
        try:
            source_list = [x.strip() for x in source.splitlines()]
        except AttributeError:
            signature_notes.append('JavaSignatureTool: stack trace not in expected format')
            return (
                "EMPTY: Java stack trace not in expected format",
                signature_notes
            )

        try:
            java_exception_class, description = source_list[0].split(':', 1)
            java_exception_class = java_exception_class.strip()
            # relace all hex addresses in the description by the string <addr>
            description = self.java_hex_addr_killer.sub(
                r'@<addr>',
                description
            ).strip()
        except ValueError:
            java_exception_class = source_list[0]
            description = ''
            signature_notes.append(
                'JavaSignatureTool: stack trace line 1 is not in the expected format'
            )

        try:
            java_method = re.sub(
                self.java_line_number_killer,
                '.java)',
                source_list[1]
            )
            if not java_method:
                signature_notes.append('JavaSignatureTool: stack trace line 2 is empty')
        except IndexError:
            signature_notes.append('JavaSignatureTool: stack trace line 2 is missing')
            java_method = ''

        # An error in an earlier version of this code resulted in the colon
        # being left out of the division between the description and the
        # java_method if the description didn't end with "<addr>". This code
        # perpetuates that error while correcting the "<addr>" placement when
        # it is not at the end of the description. See Bug 865142 for a
        # discussion of the issues.
        if description.endswith('<addr>'):
            # at which time the colon placement error is to be corrected
            # just use the following line as the replacement for this entire
            # if/else block
            signature = self.join_ignore_empty(
                delimiter,
                (java_exception_class, description, java_method)
            )
        else:
            description_java_method_phrase = self.join_ignore_empty(
                ' ',
                (description, java_method)
            )
            signature = self.join_ignore_empty(
                delimiter,
                (java_exception_class, description_java_method_phrase)
            )

        if len(signature) > self.DESCRIPTION_MAX_LENGTH:
            signature = delimiter.join(
                (java_exception_class, java_method)
            )
            signature_notes.append(
                'JavaSignatureTool: dropped Java exception description due to length'
            )

        return signature, signature_notes


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

    This rule also generates the proto_signature which is the complete list
    of normalized frames.

    """
    def __init__(self):
        super(SignatureGenerationRule, self).__init__()
        self.java_signature_tool = JavaSignatureTool()
        self.c_signature_tool = CSignatureTool()

    def _create_frame_list(self, crashing_thread_mapping, make_modules_lower_case=False):
        frame_signatures_list = []
        for a_frame in islice(
            crashing_thread_mapping.get('frames', []),
            MAXIMUM_FRAMES_TO_CONSIDER
        ):
            if make_modules_lower_case and 'module' in a_frame:
                a_frame['module'] = a_frame['module'].lower()

            normalized_frame = self.c_signature_tool.normalize_frame(**a_frame)
            a_frame['normalized'] = normalized_frame
            frame_signatures_list.append(normalized_frame)
        return frame_signatures_list

    def _get_crashing_thread(self, crash_data):
        return crash_data.get('crashing_thread', 0)

    def action(self, crash_data, result):
        # If this is a Java crash, then generate a Java signature
        if crash_data.get('java_stack_trace'):
            signature, signature_notes = self.java_signature_tool.generate(
                crash_data['java_stack_trace'],
                delimiter=': '
            )
            result['signature'] = signature
            result['notes'].extend(signature_notes)
            return True

        try:
            # First, we need to figure out which thread to look at. If it's a
            # chrome hang (1), then use thread 0. Otherwise, use the crashing
            # thread specified in the crash data.
            if crash_data.get('hang_type', None) == 1:
                crashing_thread = 0
            else:
                crashing_thread = self._get_crashing_thread(crash_data)

            # If we have a thread to look at, pull the frames for that.
            # Otherwise we don't have frames to use.
            if crashing_thread is not None:
                signature_list = self._create_frame_list(
                    glom(crash_data, 'threads.%d' % crashing_thread, default={}),
                    crash_data.get('os') == 'Windows NT'
                )

            else:
                signature_list = []

        except (KeyError, IndexError) as exc:
            signature_notes.append('No crashing frames found because of %s' % exc)
            signature_list = []

        signature, signature_notes = self.c_signature_tool.generate(
            signature_list,
            crash_data.get('hang_type'),
            crash_data.get('crashing_thread')
        )

        if signature_list:
            result['proto_signature'] = ' | '.join(signature_list)
        result['signature'] = signature
        result['notes'].extend(signature_notes)

        return True


class OOMSignature(Rule):
    """Prepends ``OOM | <size>`` to signatures for OOM crashes.

    See bug #1007530.

    """
    signature_fragments = (
        'NS_ABORT_OOM',
        'mozalloc_handle_oom',
        'CrashAtUnhandlableOOM',
        'AutoEnterOOMUnsafeRegion',
        'alloc::oom::oom',
    )

    def predicate(self, crash_data, result):
        if crash_data.get('oom_allocation_size'):
            return True

        signature = result['signature']
        if not signature:
            return False

        for a_signature_fragment in self.signature_fragments:
            if a_signature_fragment in signature:
                return True

        return False

    def action(self, crash_data, result):
        try:
            size = int(crash_data.get('oom_allocation_size'))
        except (TypeError, AttributeError, KeyError):
            result['signature'] = 'OOM | unknown | ' + result['signature']
            return True

        if size <= 262144:  # 256K
            result['signature'] = 'OOM | small'
        else:
            result['signature'] = 'OOM | large | ' + result['signature']
        return True


class AbortSignature(Rule):
    """Prepends abort message to signature.

    See bug #803779.

    """

    def predicate(self, crash_data, result):
        return bool(crash_data.get('abort_message'))

    def action(self, crash_data, result):
        abort_message = crash_data['abort_message']

        if '###!!! ABORT: file ' in abort_message:
            # This is an abort message that contains no interesting
            # information. We just want to put the "Abort" marker in the
            # signature.
            result['signature'] = 'Abort | ' + result['signature']
            return True

        if '###!!! ABORT:' in abort_message:
            # Recent crash reports added some irrelevant information at the
            # beginning of the abort message. We want to remove that and keep
            # just the actual abort message.
            abort_message = abort_message.split('###!!! ABORT:', 1)[1]

        if ': file ' in abort_message:
            # Abort messages contain a file name and a line number. Since
            # those are very likely to change between builds, we want to
            # remove those parts from the signature.
            abort_message = abort_message.split(': file ', 1)[0]

        if 'unable to find a usable font' in abort_message:
            # "unable to find a usable font" messages include a parenthesized localized message. We
            # want to remove that. Bug #1385966
            open_paren = abort_message.find('(')
            if open_paren != -1:
                end_paren = abort_message.rfind(')')
                if end_paren != -1:
                    abort_message = abort_message[:open_paren] + abort_message[end_paren + 1:]

        abort_message = drop_bad_characters(abort_message).strip()

        if len(abort_message) > 80:
            abort_message = abort_message[:77] + '...'

        result['signature'] = 'Abort | %s | %s' % (abort_message, result['signature'])
        return True


class SigFixWhitespace(Rule):
    """Fix whitespace in signatures.

    This does the following:

    * trims leading and trailing whitespace
    * converts all non-space whitespace characters to space
    * reduce consecutive spaces to a single space

    """

    WHITESPACE_RE = re.compile('\s')
    CONSECUTIVE_WHITESPACE_RE = re.compile('\s\s+')

    def predicate(self, crash_data, result):
        return isinstance(result.get('signature'), six.string_types)

    def action(self, crash_data, result):
        sig = result['signature']

        # Trim leading and trailing whitespace
        sig = sig.strip()

        # Convert all non-space whitespace characters into spaces
        sig = self.WHITESPACE_RE.sub(' ', sig)

        # Reduce consecutive spaces to a single space
        sig = self.CONSECUTIVE_WHITESPACE_RE.sub(' ', sig)

        result['signature'] = sig
        return True


class SigTruncate(Rule):
    """Truncates signatures down to SIGNATURE_MAX_LENGTH characters."""

    def predicate(self, crash_data, result):
        return len(result['signature']) > SIGNATURE_MAX_LENGTH

    def action(self, crash_data, result):
        max_length = SIGNATURE_MAX_LENGTH - 3
        result['signature'] = "%s..." % result['signature'][:max_length]
        result['notes'].append('SigTrunc: signature truncated due to length')
        return True


class StackwalkerErrorSignatureRule(Rule):
    """Appends minidump-stackwalker error to signature."""

    def predicate(self, crash_data, result):
        return bool(
            result['signature'].startswith('EMPTY') and
            crash_data.get('mdsw_status_string')
        )

    def action(self, crash_data, result):
        result['signature'] = "%s; %s" % (
            result['signature'],
            crash_data['mdsw_status_string']
        )
        return True


class SignatureRunWatchDog(SignatureGenerationRule):
    """Prepends "shutdownhang" to signature for shutdown hang crashes."""

    def predicate(self, crash_data, result):
        return 'RunWatchdog' in result['signature']

    def _get_crashing_thread(self, crash_data):
        # Always use thread 0 in this case, because that's the thread that
        # was hanging when the software was artificially crashed.
        return 0

    def action(self, crash_data, result):
        # For shutdownhang crashes, we need to use thread 0 instead of the
        # crashing thread. The reason is because those crashes happen
        # artificially when thread 0 gets stuck. So whatever the crashing
        # thread is, we don't care about it and only want to know what was
        # happening in thread 0 when it got stuck.
        ret = super(SignatureRunWatchDog, self).action(crash_data, result)
        result['signature'] = (
            "shutdownhang | %s" % result['signature']
        )
        return ret


class SignatureShutdownTimeout(Rule):
    """Replaces signature with async_shutdown_timeout message."""

    def predicate(self, crash_data, result):
        return bool(crash_data.get('async_shutdown_timeout'))

    def action(self, crash_data, result):
        parts = ['AsyncShutdownTimeout']
        try:
            shutdown_data = ujson.loads(crash_data['async_shutdown_timeout'])
            parts.append(shutdown_data['phase'])
            conditions = [
                # NOTE(willkg): The AsyncShutdownTimeout notation condition can either be a string
                # that looks like a "name" or a dict with a "name" in it.
                #
                # This handles both variations.
                c['name'] if isinstance(c, dict) else c
                for c in shutdown_data['conditions']
            ]
            if conditions:
                conditions.sort()
                parts.append(','.join(conditions))
            else:
                parts.append("(none)")
        except (ValueError, KeyError) as exc:
            parts.append("UNKNOWN")
            result['notes'].append('Error parsing AsyncShutdownTimeout: {}'.format(exc))

        new_sig = ' | '.join(parts)
        result['notes'].append(
            'Signature replaced with a Shutdown Timeout signature, '
            'was: "{}"'.format(result['signature'])
        )
        result['signature'] = new_sig

        return True


class SignatureJitCategory(Rule):
    """Replaces signature with JIT classification."""

    def predicate(self, crash_data, result):
        return bool(crash_data.get('jit_category'))

    def action(self, crash_data, result):
        result['notes'].append(
            'Signature replaced with a JIT Crash Category, '
            'was: "{}"'.format(result['signature'])
        )
        result['signature'] = "jit | {}".format(crash_data['jit_category'])
        return True


class SignatureIPCChannelError(Rule):
    """Replaces the signature with IPC channel error."""

    def predicate(self, crash_data, result):
        return bool(crash_data.get('ipc_channel_error'))

    def action(self, crash_data, result):
        if crash_data.get('additional_minidumps') == 'browser':
            new_sig = 'IPCError-browser | {}'
        else:
            new_sig = 'IPCError-content | {}'
        new_sig = new_sig.format(crash_data['ipc_channel_error'][:100])

        result['notes'].append(
            'Signature replaced with an IPC Channel Error, '
            'was: "{}"'.format(result['signature'])
        )
        result['signature'] = new_sig

        return True


class SignatureIPCMessageName(Rule):
    """Appends ipc_message_name to signature."""

    def predicate(self, crash_data, result):
        return bool(crash_data.get('ipc_message_name'))

    def action(self, crash_data, result):
        result['signature'] = '{} | IPC_Message_Name={}'.format(
            result['signature'],
            crash_data['ipc_message_name']
        )
        return True


class SignatureParentIDNotEqualsChildID(Rule):
    """Stomp on the signature if MozCrashReason is ``parentBuildID != childBuildID``.

    In the case where the assertion fails, then the parent buildid and the child buildid are
    different. This causes a lot of strangeness particularly in symbolification, so the signatures
    end up as junk. Instead, we want to bucket all these together so we replace the signature.

    """

    def predicate(self, crash_data, result):
        value = 'MOZ_RELEASE_ASSERT(parentBuildID == childBuildID)'
        return crash_data.get('moz_crash_reason') == value

    def action(self, crash_data, result):
        result['notes'].append(
            'Signature replaced with MozCrashAssert, was: "%s"' % result['signature']
        )

        # The MozCrashReason lists the assertion that failed, so we put "!=" in the signature
        result['signature'] = 'parentBuildID != childBuildID'

        return True

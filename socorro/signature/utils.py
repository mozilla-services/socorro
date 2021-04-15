# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import re
from urllib.parse import urlparse

from glom import glom


def int_or_none(data):
    try:
        return int(data)
    except (TypeError, ValueError):
        return None


def convert_to_crash_data(raw_crash, processed_crash):
    """
    Takes a raw crash and a processed crash (these are Socorro-centric
    data structures) and converts them to a crash data structure used
    by signature generation.

    :arg raw_crash: raw crash data from Socorro
    :arg processed_crash: processed crash data from Socorro

    :returns: crash data structure that conforms to the schema

    """
    crash_data = {
        # JavaStackTrace or None
        "java_stack_trace": glom(processed_crash, "java_stack_trace", default=None),
        # int or None
        "crashing_thread": glom(
            processed_crash, "json_dump.crash_info.crashing_thread", default=None
        ),
        # list of CStackTrace or None
        "threads": glom(processed_crash, "json_dump.threads", default=None),
        # int or None
        "hang_type": glom(processed_crash, "hang_type", default=None),
        # text or None
        "os": glom(processed_crash, "json_dump.system_info.os", default=None),
        # int or None
        "oom_allocation_size": int_or_none(
            glom(raw_crash, "OOMAllocationSize", default=None)
        ),
        # text or None
        "abort_message": glom(raw_crash, "AbortMessage", default=None),
        # text or None
        "mdsw_status_string": glom(processed_crash, "mdsw_status_string", default=None),
        # text json with "phase", "conditions" (complicated--see code) or None
        "async_shutdown_timeout": glom(raw_crash, "AsyncShutdownTimeout", default=None),
        # text or None
        "jit_category": glom(
            processed_crash, "classifications.jit.category", default=None
        ),
        # text or None
        "ipc_channel_error": glom(raw_crash, "ipc_channel_error", default=None),
        # text or None
        "ipc_message_name": glom(raw_crash, "IPCMessageName", default=None),
        # text
        "moz_crash_reason": glom(processed_crash, "moz_crash_reason", default=None),
        # text; comma-delimited e.g. "browser,flash1,flash2"
        "additional_minidumps": glom(raw_crash, "additional_minidumps", default=""),
        # pull out the original signature if there was one
        "original_signature": glom(processed_crash, "signature", default=""),
    }
    return crash_data


#: List of allowed characters: ascii, printable, and non-whitespace except space
ALLOWED_CHARS = [chr(c) for c in range(32, 127)]


def drop_bad_characters(text):
    """Takes a text and drops all non-printable and non-ascii characters and
    also any whitespace characters that aren't space.

    :arg str text: the text to fix

    :returns: text with all bad characters dropped

    """
    # Strip all non-ascii and non-printable characters
    text = "".join([c for c in text if c in ALLOWED_CHARS])
    return text


def parse_source_file(source_file):
    """Parses a source file thing and returns the file name

    Example:

    >>> parse_file('hg:hg.mozilla.org/releases/mozilla-esr52:js/src/jit/MIR.h:755067c14b06')
    'js/src/jit/MIR.h'

    :arg str source_file: the source file ("file") from a stack frame

    :returns: the filename or ``None`` if it couldn't determine one

    """
    if not source_file:
        return None

    vcsinfo = source_file.split(":")
    if len(vcsinfo) == 4:
        # These are repositories or cloud file systems (e.g. hg, git, s3)
        vcstype, root, vcs_source_file, revision = vcsinfo
        return vcs_source_file

    if len(vcsinfo) == 2:
        # These are directories on someone's Windows computer and vcstype is a
        # file system (e.g. "c:", "d:", "f:")
        vcstype, vcs_source_file = vcsinfo
        return vcs_source_file

    if source_file.startswith("/"):
        # These are directories on OSX or Linux
        return source_file

    # We have no idea what this is, so return None
    return None


def _is_exception(exceptions, before_token, after_token, token):
    """Predicate for whether the open token is in an exception context

    :arg exceptions: list of strings or None
    :arg before_token: the text of the function up to the token delimiter
    :arg after_token: the text of the function after the token delimiter
    :arg token: the token (only if we're looking at a close delimiter

    :returns: bool

    """
    if not exceptions:
        return False
    for s in exceptions:
        if before_token.endswith(s):
            return True
        if s in token:
            return True
    return False


def collapse(function, open_string, close_string, replacement="", exceptions=None):
    """Collapses the text between two delimiters in a frame function value

    This collapses the text between two delimiters and either removes the text
    altogether or replaces it with a replacement string.

    There are certain contexts in which we might not want to collapse the text
    between two delimiters. These are denoted as "exceptions" and collapse will
    check for those exception strings occuring before the token to be replaced
    or inside the token to be replaced.

    Before::

        IPC::ParamTraits<nsTSubstring<char> >::Write(IPC::Message *,nsTSubstring<char> const &)
               ^        ^ open token
               exception string occurring before open token

    Inside::

        <rayon_core::job::HeapJob<BODY> as rayon_core::job::Job>::execute
        ^                              ^^^^ exception string inside token
        open token

    :arg function: the function value from a frame to collapse tokens in
    :arg open_string: the open delimiter; e.g. ``(``
    :arg close_string: the close delimiter; e.g. ``)``
    :arg replacement: what to replace the token with; e.g. ``<T>``
    :arg exceptions: list of strings denoting exceptions where we don't want
        to collapse the token

    :returns: new function string with tokens collapsed

    """
    collapsed = []
    open_count = 0
    open_token = []

    for i, char in enumerate(function):
        if not open_count:
            if char == open_string and not _is_exception(
                exceptions, function[:i], function[i + 1 :], ""
            ):
                open_count += 1
                open_token = [char]
            else:
                collapsed.append(char)

        else:
            if char == open_string:
                open_count += 1
                open_token.append(char)

            elif char == close_string:
                open_count -= 1
                open_token.append(char)

                if open_count == 0:
                    token = "".join(open_token)
                    if _is_exception(
                        exceptions, function[:i], function[i + 1 :], token
                    ):
                        collapsed.append("".join(open_token))
                    else:
                        collapsed.append(replacement)
                    open_token = []
            else:
                open_token.append(char)

    if open_count:
        token = "".join(open_token)
        if _is_exception(exceptions, function[:i], function[i + 1 :], token):
            collapsed.append("".join(open_token))
        else:
            collapsed.append(replacement)

    return "".join(collapsed)


def drop_prefix_and_return_type(function):
    """Takes the function value from a frame and drops prefix and return type

    For example::

        static void * Allocator<MozJemallocBase>::malloc(unsigned __int64)
        ^      ^^^^^^ return type
        prefix

    This gets changes to this::

        Allocator<MozJemallocBase>::malloc(unsigned __int64)

    This tokenizes on space, but takes into account types, generics, traits,
    function arguments, and other parts of the function signature delimited by
    things like `', <>, {}, [], and () for both C/C++ and Rust.

    After tokenizing, this returns the last token since that's comprised of the
    function name and its arguments.

    :arg function: the function value in a frame to drop bits from

    :returns: adjusted function value

    """
    DELIMITERS = {"(": ")", "{": "}", "[": "]", "<": ">", "`": "'"}
    OPEN = DELIMITERS.keys()
    CLOSE = DELIMITERS.values()

    # The list of tokens accumulated so far
    tokens = []

    # Keeps track of open delimiters so we can match and close them
    levels = []

    # The current token we're building
    current = []

    for i, char in enumerate(function):
        if char in OPEN:
            levels.append(char)
            current.append(char)
        elif char in CLOSE:
            if levels and DELIMITERS[levels[-1]] == char:
                levels.pop()
                current.append(char)
            else:
                # This is an unmatched close.
                current.append(char)
        elif levels:
            current.append(char)
        elif char == " ":
            tokens.append("".join(current))
            current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current))

    while len(tokens) > 1 and tokens[-1].startswith(("(", "[clone")):
        # It's possible for the function signature to have a space between
        # the function name and the parenthesized arguments or [clone ...]
        # thing. If that's the case, we join the last two tokens. We keep doing
        # that until the last token is nice.
        #
        # Example:
        #
        #     somefunc (int arg1, int arg2)
        #             ^
        #     somefunc(int arg1, int arg2) [clone .cold.111]
        #                                 ^
        #     somefunc(int arg1, int arg2) [clone .cold.111] [clone .cold.222]
        #                                 ^                 ^
        tokens = tokens[:-2] + [" ".join(tokens[-2:])]

    return tokens[-1]


CRASH_ID_RE = re.compile(
    r"""
    ^
    [a-f0-9]{8}-
    [a-f0-9]{4}-
    [a-f0-9]{4}-
    [a-f0-9]{4}-
    [a-f0-9]{6}
    [0-9]{6}      # date in YYMMDD
    $
""",
    re.VERBOSE,
)


def is_crash_id_valid(crash_id):
    """Returns whether this is a valid crash id

    :arg str crash_id: the crash id in question

    :returns: True if it's valid, False if not

    """
    return bool(CRASH_ID_RE.match(crash_id))


def parse_crashid(item):
    """Returns a crashid from a number of formats.

    This handles the following three forms of crashids:

    * CRASHID
    * bp-CRASHID
    * http[s]://HOST[:PORT]/report/index/CRASHID

    :arg str item: the thing to parse a crash id from

    :returns: crashid as str or None

    """
    if is_crash_id_valid(item):
        return item

    if item.startswith("bp-") and is_crash_id_valid(item[3:]):
        return item[3:]

    if item.startswith("http"):
        parsed = urlparse(item)
        path = parsed.path
        if path.startswith("/report/index"):
            crash_id = path.split("/")[-1]
            if is_crash_id_valid(crash_id):
                return crash_id

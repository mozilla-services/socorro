# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re

from pkg_resources import resource_stream


# This is a hack because sentinels can be a tuple, with the second item being
# a function to verify if the sentinel applies. It's quite hard to express
# that in a .txt file, so this special value is here. This list should not
# grow much, and if it does, we should find a better solution for handling
# these special values.
_SPECIAL_EXTENDED_VALUES = {
    "signature_sentinels": [
        (
            "mozilla::ipc::RPCChannel::Call(IPC::Message*, IPC::Message*)",
            lambda x: "CrashReporter::CreatePairedMinidumps(void*, unsigned long, nsAString_internal*, nsILocalFile**, nsILocalFile**)"
            in x,  # noqa
        )
    ]
}


class BadRegularExpressionLineError(Exception):
    """Raised when a file contains an invalid regular expression."""


def _get_file_content(source):
    """Return a tuple, each value being a line of the source file.

    Remove empty lines and comments (lines starting with a '#').

    """
    filepath = os.path.join("siglists", source + ".txt")

    lines = []
    with resource_stream(__name__, filepath) as f:
        for i, line in enumerate(f):
            line = line.decode("utf-8", "strict").strip()
            if not line or line.startswith("#"):
                continue

            try:
                re.compile(line)
            except Exception as ex:
                raise BadRegularExpressionLineError(
                    "Regex error: {} in file {} at line {}".format(str(ex), filepath, i)
                )

            lines.append(line)

    if source in _SPECIAL_EXTENDED_VALUES:
        lines = lines + _SPECIAL_EXTENDED_VALUES[source]

    return tuple(lines)


IRRELEVANT_SIGNATURE_RE = _get_file_content("irrelevant_signature_re")
PREFIX_SIGNATURE_RE = _get_file_content("prefix_signature_re")
SIGNATURE_SENTINELS = _get_file_content("signature_sentinels")
SIGNATURES_WITH_LINE_NUMBERS_RE = _get_file_content("signatures_with_line_numbers_re")

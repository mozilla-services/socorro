# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from pathlib import Path
import re

import importlib_resources


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


class _PackageSource:
    def __repr__(self):
        return "PACKAGE"

    def __str__(self):
        return "PACKAGE"


PACKAGE = _PackageSource()


def get_filepath(name, source=PACKAGE):
    """Build a file path from the

    :param name: the signature list name
    :param source: where to look for the specified signature list file: ``PACKAGE`` to
        look at included signature list files or the directory on the file system
        as a Path or string

    :returns: Path to file in package

    """
    if source is PACKAGE:
        package_name = ".".join(__name__.split(".")[0:-1])
        return importlib_resources.files(package_name).joinpath(f"siglists/{name}.txt")

    source = Path(source)
    return source / f"{name}.txt"


def get_signature_list_content(name, source=PACKAGE):
    """Return a tuple, each value being a line of the source file.

    Remove empty lines and comments (lines starting with a '#').

    :param name: the signature list name
    :param source: where to look for the specified signature list file: ``PACKAGE`` to
        look at included signature list files or the directory on the file system
        as a Path or string

    :returns: tuple of lines from file

    """
    filepath = get_filepath(name, source=source)
    lines = []

    with filepath.open("rb") as fp:
        for i, line in enumerate(fp):
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

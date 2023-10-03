#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This script checks files for license headers.

This requires Python 3 to run.

See https://github.com/willkg/socorro-release/#readme for details.

repo: https://github.com/willkg/socorro-release/
sha: 036f7078ba7991200f7f4fc85742a6ed3dc97b6f

"""

import argparse
import pathlib
import subprocess
import sys


DESCRIPTION = (
    "Checks files in specified directory for license headers. "
    + "If you don't specify a target, it'll check all files in \"git ls-files\"."
)

# From https://www.mozilla.org/en-US/MPL/2.0/
MPLV2 = [
    "This Source Code Form is subject to the terms of the Mozilla Public",
    "License, v. 2.0. If a copy of the MPL was not distributed with this",
    "file, You can obtain one at https://mozilla.org/MPL/2.0/.",
]


LANGUAGE_DATA = {".py": {"comment": ("#",)}}


def is_code_file(path: pathlib.Path):
    """Determines whether the file is a code file we need to check.

    :param path: the Path for the file

    :returns: True if it's a code file to check, False otherwise.

    """
    if not path.is_file():
        return False
    ending: pathlib.Path = path.suffix
    return ending in LANGUAGE_DATA


def has_license_header(path: pathlib.Path):
    """Determines if file at path has an MPLv2 license header.

    :param path: the Path for the file

    :returns: True if it does, False if it doesn't.

    """
    ending: pathlib.Path = path.suffix
    comment_indicators = LANGUAGE_DATA[ending]["comment"]

    header = []
    with open(path, "r") as fp:
        firstline = True
        for line in fp.readlines():
            if firstline and line.startswith("#!"):
                firstline = False
                continue

            line = line.strip()
            # NOTE(willkg): this doesn't handle multiline comments like in C++
            for indicator in comment_indicators:
                line = line.strip(indicator)
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            header.append(line)
            if len(header) == len(MPLV2):
                if header[: len(MPLV2)] == MPLV2:
                    return True
                else:
                    break

    return False


def main(args):
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "-l", "--file-only", action="store_true", help="print files only"
    )
    parser.add_argument("--verbose", action="store_true", help="verbose output")
    parser.add_argument("target", help="file or directory tree to check", nargs="?")

    parsed = parser.parse_args(args)

    if parsed.target:
        target = pathlib.Path(parsed.target)
        if not target.exists():
            if not parsed.file_only:
                print(f"Not a valid file or directory: {target}")
            return 1

        if target.is_file():
            targets = [target]

        elif target.is_dir():
            targets = list(target.rglob("*"))

    else:
        ret = subprocess.check_output(["git", "ls-files"])
        targets = [
            pathlib.Path(target.strip()) for target in ret.decode("utf-8").splitlines()
        ]

    missing_headers = 0

    # Iterate through all the files in this target directory
    for path in targets:
        if parsed.verbose:
            print(f"Checking {path}")
        if is_code_file(path) and not has_license_header(path):
            missing_headers += 1
            if parsed.file_only:
                print(str(path))
            else:
                print(f"File {path} does not have license header.")

    if missing_headers > 0:
        if not parsed.file_only:
            print(f"Files with missing headers: {missing_headers}")
            print("")
            print("Add this:")
            print("")
            print("\n".join(MPLV2))
        return 1

    if not parsed.file_only:
        print("No files missing headers.")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

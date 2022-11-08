#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import os
import os.path
import shutil
import subprocess
import sys


DESCRIPTION = """
Updates socorro-siggen extracted library with files from Socorro's signature generation.
"""


#: List of files in socorro/signature/ to ignore and not copy over
IGNORE = ["__init__.py", "README.rst", "siglists/README.rst"]


#: Name of the file that has the socorro sha in it--this helps us
#: determine what's changed since the last update.
SOCORRO_SHA_FILE = "socorro_sha.txt"


def main(argv=None):
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("dest", help="location of siggen code")

    # Figure out destination directory
    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    dest_dir = args.dest.rstrip(os.sep)

    if os.path.exists(os.path.join(dest_dir, "siggen")):
        dest_dir = os.path.join(dest_dir, "siggen")

    # Get git sha of destination
    dest_sha_file = os.path.join(dest_dir, SOCORRO_SHA_FILE)
    if os.path.exists(dest_sha_file):
        dest_sha = open(dest_sha_file).read().strip()
    else:
        dest_sha = ""

    # Get git sha of source
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()
    source_sha = source_sha.decode("utf-8")

    print("Dest sha:   %s" % dest_sha)
    print("Source sha: %s" % source_sha)
    if dest_sha:
        git_log = subprocess.check_output(
            [
                "git",
                "log",
                "%s..%s" % (dest_sha, source_sha),
                "--oneline",
                "socorro/signature",
            ]
        )
        # Generate log of old sha -> new sha
        if git_log:
            for line in git_log.splitlines():
                print(line.decode("utf-8"))
        else:
            print("No differences.")
            return 0
    else:
        print("No previous sha to determine git commits.")

    confirm = input("Continue to copy? [y/N]: ")
    if confirm.strip().lower() != "y":
        print("Exiting...")
        return 1

    # Copy the files from source to destination
    source_dir = os.path.join(
        os.path.dirname(__file__), os.pardir, "socorro", "signature"
    )
    for dirpath, dirnames, filenames in os.walk(source_dir):
        relative_dirpath = dirpath[len(source_dir) :].lstrip(os.sep)

        for fn in filenames:
            if fn.startswith("."):
                continue

            # Figure out the filename relative to the source directory
            fn = os.path.join(relative_dirpath, fn)
            if fn in IGNORE:
                continue

            # Figure out source and dest filenames
            source = os.path.join(source_dir, fn)
            dest = os.path.join(dest_dir, fn)

            # Copy the files
            print("Copy: %s -> %s" % (source, dest))
            shutil.copyfile(source, dest)

    # Update sha in destination
    print("Generating socorro_sha file")
    with open(dest_sha_file, "w") as fp:
        fp.write(source_sha)

    print("Done!")


if __name__ == "__main__":
    sys.exit(main())

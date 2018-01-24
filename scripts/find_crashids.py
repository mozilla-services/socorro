#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Finds all the raw crash files in a directory tree and prints crash ids one per line

Usage:

    find_crashes.py [DIR]

"""

import os
import sys

from socorro.lib.ooid import is_crash_id_valid


USAGE = 'find_crashes.py [DIR]'


def main(argv):
    if not argv:
        print(USAGE)
        return 1

    crashids = set()

    for dirpath, dirnames, filenames in os.walk(argv[0]):
        for fn in filenames:
            if is_crash_id_valid(fn):
                crashids.add(fn)

    for crashid in crashids:
        print(crashid)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

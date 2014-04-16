#!/usr/bin/env python
"""
Use like this:

    find somedir | xargs check.py | python linting.py

or:

    check.py somedir | python linting.py

or:

    git ls-files somedir | python linting.py

"""

import os
import sys


# Enter any part of a warning that we deem OK.
# It can be a pep8 warning error code or any other part of a string.
#
# NOTE! Be as specific as you possibly can!
# Only blanket whole files if you desperately have to
#
EXCEPTIONS = (
    # has a exceptional use of `...import *`
    'settings/base.py:4:',

    # has a well known `...import *` trick that we like
    'settings/__init__.py',

    # all downloaded libs to be ignored
    '/js/lib/',
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=997270
    '/js/jquery/',
    '/js/flot',
    '/js/timeago/',
    'jquery.tablesorter.min.js',
    'async-local-storage-with-Promise.min.js',
    'underscore-min.js',
    'moment.min.js',
    'jquery.metadata.js',

)

EXTENSIONS_ONLY = (
    '.py',
    # commented out until we clean up our .js files
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=997272
    # '.js'
)


def main():
    errors = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        _, ext = os.path.splitext(line.split(':')[0])
        if ext not in EXTENSIONS_ONLY:
            continue
        if [f for f in EXCEPTIONS if f in line]:
            continue
        errors += 1
        sys.stderr.write(line)
    return errors


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Makes sure all docs/*.rst files are properly right-stripped of whitespace

By: peterbe
"""

import os
from glob import glob
DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'docs'))
assert glob(os.path.join(DIR, '*.rst'))

def main(*args):

    changed = set()
    for f in glob(os.path.join(DIR, '*.rst')):
        new = []
        for line in file(f):
            if line.rstrip() != line.rstrip('\n'):
                if f not in changed:
                    print f
                    changed.add(f)
            new.append(line.rstrip())
        if not new[-1] == '':
            new.append('')
        open(f, 'w').write('\n'.join(new))

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[:1]))

#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# See socorro/scripts/reprocess.py

import sys

from socorro.scripts import reprocess


if __name__ == '__main__':
    sys.exit(reprocess.main(sys.argv[1:]))

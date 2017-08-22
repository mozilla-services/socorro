#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# See socorro/scripts/fetch_crash_data.py

import sys

from socorro.scripts import fetch_crash_data


if __name__ == '__main__':
    sys.exit(fetch_crash_data.main(sys.argv[1:]))

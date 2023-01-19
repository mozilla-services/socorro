# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import contextlib
import sys


@contextlib.contextmanager
def with_scriptname(scriptname):
    """Overrides the sys.argv[0] with specified scriptname"""
    old_scriptname = sys.argv[0]
    sys.argv[0] = scriptname
    try:
        yield
    finally:
        sys.argv[0] = old_scriptname

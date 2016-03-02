# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from contextlib import contextmanager
from socorrolib.lib.util import FakeLogger


#--------------------------------------------------------------------------
@contextmanager
def temp_file_context(raw_dump_path, logger=None):
    """this contextmanager implements conditionally deleting a pathname
    at the end of a context if the pathname indicates that it is a temp
    file by having the word 'TEMPORARY' embedded in it."""
    try:
        yield raw_dump_path
    finally:
        if 'TEMPORARY' in raw_dump_path:
            try:
                os.unlink(raw_dump_path)
            except OSError:
                if logger is None:
                    logger = FakeLogger()
                logger.warning(
                    'unable to delete %s. manual deletion is required.',
                    raw_dump_path,
                    exc_info=True
                )

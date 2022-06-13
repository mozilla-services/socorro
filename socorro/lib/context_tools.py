# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import os

from contextlib import contextmanager


@contextmanager
def temp_file_context(raw_dump_path, logger=None):
    """this contextmanager implements conditionally deleting a pathname
    at the end of a context if the pathname indicates that it is a temp
    file by having the word 'TEMPORARY' embedded in it."""
    logger = logger or logging.getLogger(__name__)

    try:
        yield raw_dump_path
    finally:
        if "TEMPORARY" in raw_dump_path:
            try:
                os.unlink(raw_dump_path)
            except OSError:
                logger.warning(
                    "unable to delete %s. manual deletion is required.",
                    raw_dump_path,
                    exc_info=True,
                )

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
from functools import total_ordering
import logging
import mock


@total_ordering
class EqualAnything(object):
    def __eq__(self, other):
        return True

    def __lt__(self, other):
        return True


#: Sentinel that is equal to anything; simplifies assertions in cases where
#: part of the value changes from test to test
WHATEVER = EqualAnything()


@contextlib.contextmanager
def mock_logging(logger_name, fun_name):
    logger = logging.getLogger(logger_name)
    with mock.patch.object(logger, fun_name) as mock_logging_fun:
        yield mock_logging_fun

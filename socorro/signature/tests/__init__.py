# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# NOTE(willkg): This is a duplicate of Socorro's WHATEVER, but it allows
# the signature generation code to stand alone.

from functools import total_ordering


@total_ordering
class EqualAnything(object):
    def __eq__(self, other):
        return True

    def __lt__(self, other):
        return True


#: Sentinel that is equal to anything; simplifies assertions in cases where
#: part of the value changes from test to test
WHATEVER = EqualAnything()

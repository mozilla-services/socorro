# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function

import collections

from itertools import islice
import six


def chunkify(iterable, n):
    """Split iterable into chunks of length n

    If ``len(iterable) % n != 0``, then the last chunk will have length less than n.

    Example:

    >>> chunkify([1, 2, 3, 4, 5], 2)
    [(1, 2), (3, 4), (5,)]

    :arg iterable: the iterable
    :arg n: the chunk length

    :returns: generator of chunks from the iterable

    """
    iterable = iter(iterable)
    while 1:
        t = tuple(islice(iterable, n))
        if t:
            yield t
        else:
            return


# utilities

def backoff_seconds_generator():
    seconds = [10, 30, 60, 120, 300]
    for x in seconds:
        yield x
    while True:
        yield seconds[-1]


def dotdict_to_dict(sdotdict):
    """Takes a DotDict and returns a dict

    This does a complete object traversal converting all instances of the
    things named DotDict to dict so it's deep-copyable.

    """
    def _dictify(thing):
        if isinstance(thing, collections.Mapping):
            return dict([(key, _dictify(val)) for key, val in thing.items()])
        elif isinstance(thing, six.string_types):
            # NOTE(willkg): Need to do this because strings are sequences but
            # we don't want to convert them into lists in the next clause
            return thing
        elif isinstance(thing, collections.Sequence):
            return [_dictify(item) for item in thing]
        return thing

    return _dictify(sdotdict)

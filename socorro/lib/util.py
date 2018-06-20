# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function
import six

from itertools import islice


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


def drop_unicode(text):
    """Takes a text and drops all unicode characters

    :arg str/unicode text: the text to fix

    :returns: text with all unicode characters dropped

    """
    if six.PY2:
        if isinstance(text, str):
            # Convert ascii to unicode in python 2
            text = text.decode('unicode_escape')
        # Convert it back to a acsii string and drop any non-ascii characters
        return text.encode('ascii', 'ignore')

    # Python 3 ONLY, strip non ascii characters
    ALLOWED_CHARS = [chr(c) for c in range(32, 127)]
    text = ''.join([c for c in text if c in ALLOWED_CHARS])

    return text


# utilities

def backoff_seconds_generator():
    seconds = [10, 30, 60, 120, 300]
    for x in seconds:
        yield x
    while True:
        yield seconds[-1]


class DotDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

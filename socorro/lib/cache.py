# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
In-memory caching utilities.
"""

from collections import MutableMapping, OrderedDict
import datetime
import threading

import isodate


UTC = isodate.UTC


#: Default time-to-live for keys in seconds
DEFAULT_TTL = 600


def _utc_now():
    return datetime.datetime.now(UTC)


class ExpiringCache(MutableMapping):
    """In-memory cache that drops data older than a specified ttl

    This will do bookkeeping periodically when setting values. If you
    want to explicitly remove all expired data, call ``.flush()``.

    Example of usage:

    >>> cache = ExpiringCache(max_size=1000, ttl=5 * 60)
    >>> cache['key1'] = 'something'
    >>> cache['key1']
    'something'
    >>> # wait 5 minutes
    >>> cache['key1']
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    KeyError: 'key1'

    """
    def __init__(self, max_size=128, ttl=600):
        """
        :arg max_size: maximum number of items in the cache
        :arg ttl: ttl for items in the cache in seconds

        """
        if max_size <= 0:
            raise ValueError('max_size must be greater than 0')
        if ttl <= 0:
            raise ValueError('ttl must be greater than 0')
        self._max_size = max_size
        self._ttl = datetime.timedelta(seconds=ttl)
        # Map of key -> (expire time, value)
        self._data = OrderedDict()
        self._lock = threading.RLock()

    def flush(self):
        """Removes all expired keys"""
        with self._lock:
            NOW = _utc_now()

            for key, value_record in self._data.items():
                if value_record[0] < NOW:
                    del self._data[key]

    def __getitem__(self, key):
        with self._lock:
            value_record = self._data[key]

            if value_record[0] < _utc_now():
                del self._data[key]
                raise KeyError()

            return value_record[1]

    def __setitem__(self, key, value):
        self._data[key] = [_utc_now() + self._ttl, value]

        # If we've exceeded the max size, remove the oldest one
        if len(self._data) > self._max_size:
            del self._data[self._data.keys()[0]]

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        raise len(self._data)

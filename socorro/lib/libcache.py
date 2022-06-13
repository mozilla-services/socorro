# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
In-memory caching utilities.
"""

from collections import OrderedDict
from collections.abc import MutableMapping
import datetime
import threading

from socorro.lib.libdatetime import utc_now


#: Default time-to-live for keys in seconds
DEFAULT_TTL = 600


class ExpiringCache(MutableMapping):
    """In-memory cache that drops data older than a specified ttl

    This will do bookkeeping periodically when setting values. If you
    want to explicitly remove all expired data, call ``.flush()``.

    Example of usage:

    >>> cache = ExpiringCache(max_size=1000, default_ttl=5 * 60)
    >>> cache['key1'] = 'something'
    >>> cache['key1']
    'something'
    >>> # wait 5 minutes
    >>> cache['key1']
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    KeyError: 'key1'

    ExpiringCache also supports different ttls for different keys:

    >>> cache = ExpiringCache(max_size=1000, default_ttl=5 * 60)
    >>> cache['short_key'] = 'something'
    >>> cache.set('long_key', value='something', ttl=60 * 60)
    >>> # wait 5 minutes
    >>> cache['short_key']
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    KeyError: 'short_key'
    >>> cache['long_key']
    'something'

    """

    def __init__(self, max_size=128, default_ttl=DEFAULT_TTL):
        """
        :arg max_size: maximum number of items in the cache
        :arg ttl: ttl for items in the cache in seconds

        """
        if max_size <= 0:
            raise ValueError("max_size must be greater than 0")
        if default_ttl <= 0:
            raise ValueError("ttl must be greater than 0")
        self._max_size = max_size
        self._default_ttl = datetime.timedelta(seconds=default_ttl)
        # Map of key -> (expire time, value)
        self._data = OrderedDict()
        self._lock = threading.RLock()

    def flush(self):
        """Removes all expired keys"""
        with self._lock:
            NOW = utc_now()

            for key, value_record in list(self._data.items()):
                if value_record[0] < NOW:
                    del self._data[key]

    def __getitem__(self, key):
        with self._lock:
            value_record = self._data[key]

            if value_record[0] < utc_now():
                del self._data[key]
                raise KeyError()

            return value_record[1]

    def __setitem__(self, key, value):
        self.set(key, value, ttl=self._default_ttl)

    def set(self, key, value, ttl=None):
        ttl = ttl if ttl is not None else self._default_ttl
        if isinstance(ttl, int):
            ttl = datetime.timedelta(seconds=ttl)

        self._data[key] = [utc_now() + ttl, value]

        # If we've exceeded the max size, remove the oldest one
        if len(self._data) > self._max_size:
            self._data.popitem(last=False)

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from unittest import mock

import pytest

from socorro.lib.libcache import ExpiringCache
from socorro.lib.libdatetime import utc_now


class TestExpiringCache:
    def test_get_set(self):
        cache = ExpiringCache(default_ttl=600)
        with pytest.raises(KeyError):
            cache["foo"]

        cache["foo"] = "bar"
        assert cache["foo"] == "bar"

    @mock.patch("socorro.lib.libcache.utc_now")
    def test_expiration(self, mock_utc_now):
        # Mock utc_now to return the current time so we can set the expiry for
        # the key
        now = utc_now()
        mock_utc_now.return_value = now

        cache = ExpiringCache(default_ttl=100)
        cache["foo"] = "bar"
        assert len(cache) == 1
        cache.set("long_foo", value="bar2", ttl=1000)
        assert len(cache) == 2

        # default ttl is 100, so 99 seconds into the future, we should get back
        # both cached values
        mock_utc_now.return_value = now + datetime.timedelta(seconds=99)
        assert cache["foo"] == "bar"
        assert cache["long_foo"] == "bar2"
        assert len(cache) == 2

        # ttl is 100, so 101 seconds into the future, we should get a KeyError
        # for one cached key and the other should be fine
        mock_utc_now.return_value = now + datetime.timedelta(seconds=101)
        with pytest.raises(KeyError):
            cache["foo"]
        assert cache["long_foo"] == "bar2"
        assert len(cache) == 1

    def test_max_size(self):
        cache = ExpiringCache(max_size=5)
        cache["foo1"] = 1
        cache["foo2"] = 1
        cache["foo3"] = 1
        cache["foo4"] = 1
        cache["foo5"] = 1

        assert list(cache.keys()) == ["foo1", "foo2", "foo3", "foo4", "foo5"]

        cache["foo6"] = 1

        assert list(cache.keys()) == ["foo2", "foo3", "foo4", "foo5", "foo6"]

    @mock.patch("socorro.lib.libcache.utc_now")
    def test_flush(self, mock_utc_now):
        now = utc_now()
        now_plus_10 = now + datetime.timedelta(seconds=10)
        now_plus_20 = now + datetime.timedelta(seconds=20)

        mock_utc_now.return_value = now
        cache = ExpiringCache(default_ttl=100)

        # At time now
        cache["foo"] = "bar"

        # At time now + 10
        mock_utc_now.return_value = now_plus_10
        cache["foo10"] = "bar"

        # At time now + 20
        mock_utc_now.return_value = now_plus_20
        cache["foo20"] = "bar"

        assert cache._data == {
            "foo": [now + cache._default_ttl, "bar"],
            "foo10": [now_plus_10 + cache._default_ttl, "bar"],
            "foo20": [now_plus_20 + cache._default_ttl, "bar"],
        }

        # Set to now + 105 which expires the first, but not the other two
        mock_utc_now.return_value = now + datetime.timedelta(seconds=105)
        cache.flush()

        # We don't want to trigger eviction or anything like that, so check
        # the contents of the internal data structure directly
        assert cache._data == {
            "foo10": [now_plus_10 + cache._default_ttl, "bar"],
            "foo20": [now_plus_20 + cache._default_ttl, "bar"],
        }

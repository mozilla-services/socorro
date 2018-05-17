# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import mock
import pytest

from socorro.lib.cache import ExpiringCache, UTC


class TestExpiringCache:
    def test_get_set(self):
        cache = ExpiringCache(ttl=600)
        with pytest.raises(KeyError):
            cache['foo']

        cache['foo'] = 'bar'
        assert cache['foo'] == 'bar'

    @mock.patch('socorro.lib.cache._utc_now')
    def test_expiration(self, mock_utc_now):
        NOW = datetime.datetime.now(UTC)
        # Mock _utc_now to return the current time so we can set the expiry for
        # the key
        mock_utc_now.return_value = NOW
        cache = ExpiringCache(ttl=100)
        cache['foo'] = 'bar'
        assert len(cache._data) == 1

        # ttl is 100, so 99 seconds into the future, we should get back the
        # cached value
        mock_utc_now.return_value = NOW + datetime.timedelta(seconds=99)
        assert cache['foo'] == 'bar'
        assert len(cache._data) == 1

        # ttl is 100, so 101 seconds into the future, we should get a KeyError
        # and the key should be removed from the dict
        mock_utc_now.return_value = NOW + datetime.timedelta(seconds=101)
        with pytest.raises(KeyError):
            cache['foo']
        assert len(cache._data) == 0

    def test_max_size(self):
        cache = ExpiringCache(max_size=5)
        cache['foo1'] = 1
        cache['foo2'] = 1
        cache['foo3'] = 1
        cache['foo4'] = 1
        cache['foo5'] = 1

        assert cache.keys() == ['foo1', 'foo2', 'foo3', 'foo4', 'foo5']

        cache['foo6'] = 1

        assert cache.keys() == ['foo2', 'foo3', 'foo4', 'foo5', 'foo6']

    @mock.patch('socorro.lib.cache._utc_now')
    def test_flush(self, mock_utc_now):
        NOW = datetime.datetime.now(UTC)
        NOW_PLUS_10 = NOW + datetime.timedelta(seconds=10)
        NOW_PLUS_20 = NOW + datetime.timedelta(seconds=20)

        mock_utc_now.return_value = NOW
        cache = ExpiringCache(ttl=100)

        # At time NOW
        cache['foo'] = 'bar'

        # At time NOW + 10
        mock_utc_now.return_value = NOW_PLUS_10
        cache['foo10'] = 'bar'

        # At time NOW + 20
        mock_utc_now.return_value = NOW_PLUS_20
        cache['foo20'] = 'bar'

        assert (
            cache._data == {
                'foo': [NOW + cache._ttl, 'bar'],
                'foo10': [NOW_PLUS_10 + cache._ttl, 'bar'],
                'foo20': [NOW_PLUS_20 + cache._ttl, 'bar'],
            }
        )

        # Set to NOW + 105 which expires the first, but not the other two
        mock_utc_now.return_value = NOW + datetime.timedelta(seconds=105)
        cache.flush()

        assert (
            cache._data == {
                'foo10': [NOW_PLUS_10 + cache._ttl, 'bar'],
                'foo20': [NOW_PLUS_20 + cache._ttl, 'bar'],
            }
        )

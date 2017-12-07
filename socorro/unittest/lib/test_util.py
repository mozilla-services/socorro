# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib.util import chunkify, drop_unicode


@pytest.mark.parametrize('text, expected', [
    ('', ''),
    (u'', ''),

    ('123', '123'),
    (u'123', '123'),

    # Drop any unicode characters
    ('1\xc6\x8a23', '123'),
    (u'1\u018a23', '123'),
])
def test_drop_unicode(text, expected):
    assert drop_unicode(text) == expected


def test_chunkify():
    # chunking nothing yields nothing.
    assert list(chunkify([], 1)) == []

    # chunking list where len(list) < n
    assert list(chunkify([1], 10)) == [(1,)]

    # chunking a list where len(list) == n
    assert list(chunkify([1, 2], 2)) == [(1, 2)]

    # chunking list where len(list) > n
    assert list(chunkify([1, 2, 3, 4, 5], 2)) == [(1, 2), (3, 4), (5,)]

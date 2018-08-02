# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from ..utils import drop_bad_characters


@pytest.mark.parametrize('text, expected', [
    ('', ''),
    (u'', ''),

    ('123', '123'),
    (u'123', '123'),

    # Drop non-ascii characters
    ('1\xc6\x8a23', '123'),
    (u'1\u018a23', '123'),

    # Drop non-space whitespace characters
    ('\r\n\t1 23', '1 23'),
    (u'\r\n\t1 23', '1 23'),

    # Drop non-printable characters
    ('\0\b1 23', '1 23'),
    (u'\0\b1 23', '1 23'),
])
def test_drop_bad_characters(text, expected):
    assert drop_bad_characters(text) == expected

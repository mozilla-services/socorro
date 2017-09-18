# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib.util import to_printable_string


@pytest.mark.parametrize('text, expected', [
    ('', ''),
    (u'', ''),
    ('123', '123'),
    (u'123', '123'),

    # Drop unicode characters
    ('1\xc6\x8a23', '123'),
    (u'1\u018a23', '123'),

    # Drop non-space whitespace
    ('1\n \t\r23', '1 23'),
    (u'1\n \t\r23', '1 23'),
])
def test_to_printable_string(text, expected):
    assert to_printable_string(text) == expected

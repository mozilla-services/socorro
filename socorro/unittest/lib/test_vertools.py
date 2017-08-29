# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib import ver_tools


phs = ver_tools._padding_high_string
pl = ver_tools._padding_list


@pytest.mark.parametrize('ver, expected, ver2', [
    ('3', [3, phs, 0, phs] + pl * 3, '3'),
    ('3.', [3, phs, 0, phs] + pl * 3, '3'),
    ('3.0', [3, phs, 0, phs] + pl * 3, '3'),
    ('3.0.0', [3, phs, 0, phs] + pl * 3, '3'),
    ('3.5', [3, phs, 0, phs, 5, phs, 0, phs] + pl * 2, '3.5'),
    ('3.5pre', [3, phs, 0, phs, 5, 'pre', 0, phs] + pl * 2, '3.5pre'),
    ('3.5b3', [3, phs, 0, phs, 5, 'b', 3, phs] + pl * 2, '3.5b3'),
    ('3.6.4plugin3', [3, phs, 0, phs, 6, phs, 0, phs, 4, 'plugin', 3, phs] + pl, '3.6.4plugin3'),
])
def test_normalize(ver, expected, ver2):
    assert ver_tools.normalize(ver) == expected

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import operator

import pytest

from socorro.scripts.fetch_crashids import INFINITY


@pytest.mark.parametrize(
    "oper, rhs, expected",
    [
        # Infinity == x
        (operator.eq, 10000, False),
        (operator.eq, INFINITY, True),
        # Infinity != x
        (operator.ne, 10000, True),
        (operator.ne, INFINITY, False),
        # Infinity < x
        (operator.lt, 10000, False),
        (operator.lt, INFINITY, False),
        # Infinity <= x
        (operator.le, 10000, False),
        (operator.le, INFINITY, True),
        # Infinity > x
        (operator.gt, 10000, True),
        (operator.gt, INFINITY, False),
        # Infinity >= x
        (operator.ge, 10000, True),
        (operator.ge, INFINITY, True),
    ],
)
def test_infinity_comparisons(oper, rhs, expected):
    assert oper(INFINITY, rhs) == expected


def test_infinity_lhs_subtraction():
    assert INFINITY - 5 == INFINITY
    assert INFINITY - INFINITY == 0


def test_infinity_rhs_subtraction():
    with pytest.raises(ValueError):
        5 - INFINITY

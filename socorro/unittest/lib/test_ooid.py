# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import pytest

from socorro.lib import ooid
from socorro.lib.libdatetime import UTC


@pytest.mark.parametrize(
    "crashid, expected",
    [
        ("", False),
        ("aaa", False),
        ("de1bb258cbbf4589a67334f800160918", False),
        ("DE1BB258-CBBF-4589-A673-34F800160918", False),
        ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", False),
        ("00000000-0000-0000-0000-000000000000", True),
    ],
)
def test_validate_crash_id(crashid, expected):
    assert ooid.is_crash_id_valid(crashid) == expected


def test_date_from_ooid():
    crash_id = "3efa014e-a9e9-405d-ae7e-9def54181210"
    assert ooid.date_from_ooid(crash_id) == datetime.datetime(2018, 12, 10, tzinfo=UTC)

    crash_id = "3efa014e-a9e9-405d-ae7e-9def54ffffff"
    assert ooid.date_from_ooid(crash_id) is None


def test_depth_from_ooid():
    crash_id = "3efa014e-a9e9-405d-ae7e-9def54181210"
    assert ooid.depth_from_ooid(crash_id) == 4

    crash_id = "3efa014e-a9e9-405d-ae7e-9def5fffffff"
    assert ooid.depth_from_ooid(crash_id) is None

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import isodate
import pytest

from socorro.lib import libdatetime


UTC = libdatetime.UTC
PLUS3 = isodate.tzinfo.FixedOffset(3, 0, "+03:00")


def test_utc_now():
    """
    Test libdatetime.utc_now()
    """
    res = libdatetime.utc_now()
    assert res.strftime("%Z") == "UTC"
    assert res.strftime("%z") == "+0000"
    assert res.tzinfo is not None


def test_string_to_datetime():
    """
    Test libdatetime.string_to_datetime()
    """
    # Empty date
    date = ""
    with pytest.raises(ValueError):
        res = libdatetime.string_to_datetime(date)

    # already a date
    date = datetime.datetime.utcnow()
    res = libdatetime.string_to_datetime(date)

    assert res == date.replace(tzinfo=UTC)
    assert res.strftime("%Z") == "UTC"
    assert res.strftime("%z") == "+0000"

    # YY-mm-dd date
    date = "2001-11-03"
    res = libdatetime.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 3, tzinfo=UTC)
    assert res.strftime("%Z") == "UTC"  # timezone aware

    # and naughty YY-m-d date
    date = "2001-1-3"
    res = libdatetime.string_to_datetime(date)
    assert res == datetime.datetime(2001, 1, 3, tzinfo=UTC)
    assert res.strftime("%Z") == "UTC"  # timezone aware

    # YY-mm-dd HH:ii:ss.S date
    date = "2001-11-30 12:34:56.123456"
    res = libdatetime.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, 123456, tzinfo=UTC)

    # Separated date
    date = ["2001-11-30", "12:34:56"]
    res = libdatetime.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, tzinfo=UTC)

    # Invalid date
    date = "2001-11-32"
    with pytest.raises(ValueError):
        libdatetime.string_to_datetime(date)


@pytest.mark.parametrize(
    "data, expected",
    [
        # Good dates return good times
        ("2011-09-06T00:00:00+00:00", 1315267200.0),
        # Bad data returns 0.0
        ("foo", 0.0),
    ],
)
def test_isoformat_to_time(data, expected):
    assert libdatetime.isoformat_to_time(data) == expected


def test_string_datetime_with_timezone():
    date = "2001-11-30T12:34:56Z"
    res = libdatetime.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, tzinfo=UTC)
    assert res.strftime("%H") == "12"
    # because it's a timezone aware datetime
    assert res.tzname() == "UTC"
    assert res.strftime("%Z") == "UTC"
    assert res.strftime("%z") == "+0000"

    # plus 3 hours east of Zulu means minus 3 hours on UTC
    date = "2001-11-30T12:10:56+03:00"
    res = libdatetime.string_to_datetime(date)
    expected = datetime.datetime(2001, 11, 30, 12 - 3, 10, 56, tzinfo=UTC)
    assert res == expected

    # similar example
    date = "2001-11-30T12:10:56-01:30"
    res = libdatetime.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12 + 1, 10 + 30, 56, tzinfo=UTC)

    # YY-mm-dd+HH:ii:ss.S date
    date = "2001-11-30 12:34:56.123456Z"
    res = libdatetime.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, 123456, tzinfo=UTC)


@pytest.mark.parametrize(
    "ts, timezone",
    [
        ("2012-01-10T12:13:14", UTC),
        ("2012-01-10T12:13:14.98765", UTC),
        ("2012-01-10T12:13:14.98765+03:00", PLUS3),
        ("2012-01-10T12:13:14.98765Z", UTC),
        ("2012-01-10 12:13:14", UTC),
        ("2012-01-10 12:13:14.98765", UTC),
        ("2012-01-10 12:13:14.98765+03:00", PLUS3),
        ("2012-01-10 12:13:14.98765Z", UTC),
    ],
)
def test_string_datetime_with_timezone_variations(ts, timezone):
    res = libdatetime.string_to_datetime(ts)
    # NOTE(willkg): isodate.tzinfo.FixedOffset doesn't define __eq__, so we compare the
    # reprs of them. :(
    assert repr(res.tzinfo) == repr(timezone)
    assert isinstance(res, datetime.datetime)


def test_date_to_string():
    # Datetime with timezone
    date = datetime.datetime(2012, 1, 3, 12, 23, 34, tzinfo=UTC)
    res_exp = "2012-01-03T12:23:34+00:00"
    res = libdatetime.date_to_string(date)
    assert res == res_exp

    # Datetime without timezone
    date = datetime.datetime(2012, 1, 3, 12, 23, 34)
    res_exp = "2012-01-03T12:23:34"
    res = libdatetime.date_to_string(date)
    assert res == res_exp

    # Date (no time, no timezone)
    date = datetime.date(2012, 1, 3)
    res_exp = "2012-01-03"
    res = libdatetime.date_to_string(date)
    assert res == res_exp


def test_date_to_string_fail():
    with pytest.raises(TypeError):
        libdatetime.date_to_string("2012-01-03")

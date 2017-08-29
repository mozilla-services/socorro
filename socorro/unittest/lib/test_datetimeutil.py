# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import isodate
import pytest

from socorro.lib import datetimeutil


UTC = datetimeutil.UTC
PLUS3 = isodate.tzinfo.FixedOffset(3, 0, '+03:00')


def test_utc_now():
    """
    Test datetimeutil.utc_now()
    """
    res = datetimeutil.utc_now()
    assert res.strftime('%Z') == 'UTC'
    assert res.strftime('%z') == '+0000'
    assert res.tzinfo is not None


def test_string_to_datetime():
    """
    Test datetimeutil.string_to_datetime()
    """
    # Empty date
    date = ""
    with pytest.raises(ValueError):
        res = datetimeutil.string_to_datetime(date)

    # already a date
    date = datetime.datetime.utcnow()
    res = datetimeutil.string_to_datetime(date)

    assert res == date.replace(tzinfo=UTC)
    assert res.strftime('%Z') == 'UTC'
    assert res.strftime('%z') == '+0000'

    # YY-mm-dd date
    date = "2001-11-03"
    res = datetimeutil.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 3, tzinfo=UTC)
    assert res.strftime('%Z') == 'UTC'  # timezone aware

    # and naughty YY-m-d date
    date = "2001-1-3"
    res = datetimeutil.string_to_datetime(date)
    assert res == datetime.datetime(2001, 1, 3, tzinfo=UTC)
    assert res.strftime('%Z') == 'UTC'  # timezone aware

    # YY-mm-dd HH:ii:ss.S date
    date = "2001-11-30 12:34:56.123456"
    res = datetimeutil.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, 123456, tzinfo=UTC)

    # Separated date
    date = ["2001-11-30", "12:34:56"]
    res = datetimeutil.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, tzinfo=UTC)

    # Invalid date
    date = "2001-11-32"
    with pytest.raises(ValueError):
        datetimeutil.string_to_datetime(date)


def test_string_datetime_with_timezone():
    date = "2001-11-30T12:34:56Z"
    res = datetimeutil.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, tzinfo=UTC)
    assert res.strftime('%H') == '12'
    # because it's a timezone aware datetime
    assert res.tzname() == 'UTC'
    assert res.strftime('%Z') == 'UTC'
    assert res.strftime('%z') == '+0000'

    # plus 3 hours east of Zulu means minus 3 hours on UTC
    date = "2001-11-30T12:10:56+03:00"
    res = datetimeutil.string_to_datetime(date)
    expected = datetime.datetime(2001, 11, 30, 12 - 3, 10, 56, tzinfo=UTC)
    assert res == expected

    # similar example
    date = "2001-11-30T12:10:56-01:30"
    res = datetimeutil.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12 + 1, 10 + 30, 56, tzinfo=UTC)

    # YY-mm-dd+HH:ii:ss.S date
    date = "2001-11-30 12:34:56.123456Z"
    res = datetimeutil.string_to_datetime(date)
    assert res == datetime.datetime(2001, 11, 30, 12, 34, 56, 123456, tzinfo=UTC)


@pytest.mark.parametrize('ts, timezone', [
    ('2012-01-10T12:13:14', UTC),
    ('2012-01-10T12:13:14.98765', UTC),
    ('2012-01-10T12:13:14.98765+03:00', PLUS3),
    ('2012-01-10T12:13:14.98765Z', UTC),
    ('2012-01-10 12:13:14', UTC),
    ('2012-01-10 12:13:14.98765', UTC),
    ('2012-01-10 12:13:14.98765+03:00', PLUS3),
    ('2012-01-10 12:13:14.98765Z', UTC),
])
def test_string_datetime_with_timezone_variations(ts, timezone):
    res = datetimeutil.string_to_datetime(ts)
    # NOTE(willkg): isodate.tzinfo.FixedOffset doesn't define __eq__, so we compare the
    # reprs of them. :(
    assert repr(res.tzinfo) == repr(timezone)
    assert isinstance(res, datetime.datetime)


def test_date_to_string():
    # Datetime with timezone
    date = datetime.datetime(2012, 1, 3, 12, 23, 34, tzinfo=UTC)
    res_exp = '2012-01-03T12:23:34+00:00'
    res = datetimeutil.date_to_string(date)
    assert res == res_exp

    # Datetime without timezone
    date = datetime.datetime(2012, 1, 3, 12, 23, 34)
    res_exp = '2012-01-03T12:23:34'
    res = datetimeutil.date_to_string(date)
    assert res == res_exp

    # Date (no time, no timezone)
    date = datetime.date(2012, 1, 3)
    res_exp = '2012-01-03'
    res = datetimeutil.date_to_string(date)
    assert res == res_exp


def test_date_to_string_fail():
    with pytest.raises(TypeError):
        datetimeutil.date_to_string('2012-01-03')


def test_uuid_to_date():
    uuid = "e8820616-1462-49b6-9784-e99a32120201"
    date_exp = datetime.date(year=2012, month=2, day=1)
    date = datetimeutil.uuid_to_date(uuid)
    assert date == date_exp

    uuid = "e8820616-1462-49b6-9784-e99a32181223"
    date_exp = datetime.date(year=1118, month=12, day=23)
    date = datetimeutil.uuid_to_date(uuid, century=11)
    assert date == date_exp


def test_date_to_weekly_partition_with_string():
    datestring = '2015-01-09'
    partition_exp = '20150105'

    partition = datetimeutil.datestring_to_weekly_partition(datestring)
    assert partition == partition_exp

    # Is there a better way of testing that we handle 'now' as a date value?
    datestring = 'now'
    date_now = datetime.datetime.now().date()
    partition_exp = (date_now + datetime.timedelta(0 - date_now.weekday())).strftime('%Y%m%d')
    partition = datetimeutil.datestring_to_weekly_partition(datestring)
    assert partition == partition_exp


@pytest.mark.parametrize('data, expected', [
    (datetime.datetime(2014, 12, 29), '20141229'),
    (datetime.datetime(2014, 12, 30), '20141229'),
    (datetime.datetime(2014, 12, 31), '20141229'),
    (datetime.datetime(2015, 1, 1), '20141229'),
    (datetime.datetime(2015, 1, 2), '20141229'),
    (datetime.datetime(2015, 1, 3), '20141229'),
    (datetime.datetime(2015, 1, 4), '20141229'),
    (datetime.datetime(2015, 1, 5), '20150105'),
    (datetime.datetime(2015, 1, 6), '20150105'),
    (datetime.datetime(2015, 1, 7), '20150105'),
    (datetime.datetime(2015, 1, 8), '20150105'),
    (datetime.datetime(2015, 1, 9), '20150105'),
])
def test_date_to_weekly_partition_with_datetime(data, expected):
    assert datetimeutil.datestring_to_weekly_partition(data) == expected

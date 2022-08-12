# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import json
import re

import isodate


UTC = isodate.UTC


def datetime_from_isodate_string(s):
    """Take an ISO date string of the form YYYY-MM-DDTHH:MM:SS.S
    and convert it into an instance of datetime.datetime
    """
    return string_to_datetime(s)


def str_hours_to_time_delta(hours_as_string):
    return datetime.timedelta(hours=int(hours_as_string))


def isoformat_to_time(data):
    """Convert an isoformat string to seconds since epoch

    :arg str data: datetime in isoformat

    :returns: time in seconds as a float (equivalent to time.time() return); or 0.0
        if it's a bad datetime

    """
    try:
        dt = datetime.datetime.fromisoformat(data)
        return dt.timestamp()
    except ValueError:
        return 0.0


def utc_now():
    """Return a timezone aware datetime instance in UTC timezone

    This funciton is mainly for convenience. Compare:

        >>> from libdatetime import utc_now
        >>> utc_now()
        datetime.datetime(2012, 1, 5, 16, 42, 13, 639834,
          tzinfo=<isodate.tzinfo.Utc object at 0x101475210>)

    Versus:

        >>> import datetime
        >>> from libdatetime import UTC
        >>> datetime.datetime.now(UTC)
        datetime.datetime(2012, 1, 5, 16, 42, 13, 639834,
          tzinfo=<isodate.tzinfo.Utc object at 0x101475210>)

    """
    return datetime.datetime.now(UTC)


def string_to_datetime(date):
    """Return a datetime.datetime instance with tzinfo.
    I.e. a timezone aware datetime instance.

    Acceptable formats for input are:

        * 2012-01-10T12:13:14
        * 2012-01-10T12:13:14.98765
        * 2012-01-10T12:13:14.98765+03:00
        * 2012-01-10T12:13:14.98765Z
        * 2012-01-10 12:13:14
        * 2012-01-10 12:13:14.98765
        * 2012-01-10 12:13:14.98765+03:00
        * 2012-01-10 12:13:14.98765Z

    But also, some more odd ones (probably because of legacy):

        * 2012-01-10
        * ['2012-01-10', '12:13:14']

    """
    if date is None:
        return None
    if isinstance(date, datetime.datetime):
        if not date.tzinfo:
            date = date.replace(tzinfo=UTC)
        return date
    if isinstance(date, list):
        date = "T".join(date)
    if isinstance(date, str):
        if len(date) <= len("2000-01-01"):
            return datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
        else:
            try:
                parsed = isodate.parse_datetime(date)
            except ValueError:
                # e.g. '2012-01-10 12:13:14Z' becomes '2012-01-10T12:13:14Z'
                parsed = isodate.parse_datetime(re.sub(r"(\d)\s(\d)", r"\1T\2", date))
            if not parsed.tzinfo:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
    raise ValueError("date not a parsable string")


def date_to_string(date):
    """Transform a date or datetime object into a string and return it.

    Examples:
    >>> date_to_string(datetime.datetime(2012, 1, 3, 12, 23, 34, tzinfo=UTC))
    '2012-01-03T12:23:34+00:00'
    >>> date_to_string(datetime.datetime(2012, 1, 3, 12, 23, 34))
    '2012-01-03T12:23:34'
    >>> date_to_string(datetime.date(2012, 1, 3))
    '2012-01-03'

    """
    if isinstance(date, datetime.datetime):
        # Create an ISO 8601 datetime string
        date_str = date.strftime("%Y-%m-%dT%H:%M:%S")
        tzstr = date.strftime("%z")
        if tzstr:
            # Yes, this is ugly. And no, I haven't found a better way to have a
            # truly ISO 8601 datetime with timezone in Python.
            date_str = "%s%s:%s" % (date_str, tzstr[0:3], tzstr[3:5])
    elif isinstance(date, datetime.date):
        # Create an ISO 8601 date string
        date_str = date.strftime("%Y-%m-%d")
    else:
        raise TypeError("Argument is not a date or datetime. ")

    return date_str


class JsonDTEncoder(json.JSONEncoder):
    """JSON encoder that handles datetimes

    >>> json.dumps(some_data, cls=JsonDTEncoder)
    ...

    """

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S.%f")
        return json.JSONEncoder.default(self, obj)


def timesince(d, now):
    """
    Taken from django.utils.timesince and modified to simpler requirements.

    Takes two datetime objects and returns the time between d and now
    as a nicely formatted string, e.g. "10 minutes". If d occurs after now,
    then "0 minutes" is returned.

    Units used are years, months, weeks, days, hours, and minutes.
    Seconds and microseconds are ignored. Up to two adjacent units will be
    displayed. For example, "2 weeks, 3 days" and "1 year, 3 months" are
    possible outputs, but "2 weeks, 3 hours" and "1 year, 5 days" are not.

    Adapted from
    http://web.archive.org/web/20060617175230/\
    http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """

    def pluralize(a, b):
        def inner(n):
            if n == 1:
                return a % n
            return b % n

        return inner

    def ugettext(s):
        return s

    chunks = (
        (60 * 60 * 24 * 365, pluralize("%d year", "%d years")),
        (60 * 60 * 24 * 30, pluralize("%d month", "%d months")),
        (60 * 60 * 24 * 7, pluralize("%d week", "%d weeks")),
        (60 * 60 * 24, pluralize("%d day", "%d days")),
        (60 * 60, pluralize("%d hour", "%d hours")),
        (60, pluralize("%d minute", "%d minutes")),
        (0, pluralize("%d second", "%d seconds")),
    )
    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    delta = now - d
    # ignore microseconds
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        # We'll use the last chunk (highest granularity)
        _, name = chunks[-1]
        return name(0)
    for i, (seconds, name) in enumerate(chunks):
        if seconds > 0:
            count = since // seconds
            if count != 0:
                break
        else:
            count = since

    result = name(count)
    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        if seconds2 > 0:
            count2 = (since - (seconds * count)) // seconds2
        else:
            count2 = since - (seconds * count)
        if count2 != 0:
            result += ugettext(", ") + name2(count2)

    return result

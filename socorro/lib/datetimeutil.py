import re
import datetime
import isodate  # 3rd party


UTC = isodate.UTC


def datetimeFromISOdateString(s):
    """Take an ISO date string of the form YYYY-MM-DDTHH:MM:SS.S
    and convert it into an instance of datetime.datetime
    """
    return string_to_datetime(s)


def strHoursToTimeDelta(hoursAsString):
    return datetime.timedelta(hours=int(hoursAsString))


def timeDeltaToSeconds(td):
    return td.days * 24 * 60 * 60 + td.seconds


def string_to_datetime(date, always_tzinfo=True):
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
    if isinstance(date, datetime.datetime):
        if not date.tzinfo:
            date = date.replace(tzinfo=UTC)
        return date
    if isinstance(date, list):
        date = 'T'.join(date)
    if isinstance(date, basestring):
        if len(date) <= len('2000-01-01'):
            return (datetime.datetime
                    .strptime(date, '%Y-%m-%d')
                    .replace(tzinfo=UTC))
        else:
            try:
                parsed = isodate.parse_datetime(date)
            except ValueError:
                # e.g. '2012-01-10 12:13:14Z' becomes '2012-01-10T12:13:14Z'
                parsed = isodate.parse_datetime(
                  re.sub('(\d)\s(\d)', r'\1T\2', date))
            if not parsed.tzinfo:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
    raise ValueError("date not a parsable string")


def date_to_string(date):
    """
    Transform a datetime object into a string and return it.
    """
    date_format = "%Y-%m-%d %H:%M:%S.%f"
    return date.strftime(date_format)

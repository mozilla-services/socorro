import datetime
import functools
import json
import time
from django import http


def unixtime(value, millis=False, format='%Y-%m-%d'):
    d = datetime.datetime.strptime(value, format)
    epoch_seconds = time.mktime(d.timetuple())
    if millis:
        return epoch_seconds * 1000 + d.microsecond / 1000
    else:
        return epoch_seconds


def daterange(start_date, end_date, format='%Y-%m-%d'):
    for n in range((end_date - start_date).days):
        yield (start_date + datetime.timedelta(n)).strftime(format)


def json_view(f):
    @functools.wraps(f)
    def wrapper(*args, **kw):
        response = f(*args, **kw)
        if isinstance(response, http.HttpResponse):
            return response
        else:
            return http.HttpResponse(_json_clean(json.dumps(response)),
                                content_type='application/json; charset=UTF-8')
    return wrapper


def _json_clean(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return value.replace("</", "<\\/")

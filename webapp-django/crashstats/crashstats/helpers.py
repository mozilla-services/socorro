import json
import urllib
import locale
import jinja2
from jingo import register

from crashstats import scrubber


@register.filter
def split(value, separator):
    return value.split(separator)


@register.function
def truncatechars(str_, max_length):
    if len(str_) < max_length:
        return str_
    else:
        return '%s...' % str_[:max_length - len('...')]


@register.filter
def urlencode(txt):
    """Url encode a path."""
    # originally taken from funfactory but improved to support non-ascii
    # Unicode characters
    if isinstance(txt, unicode):
        txt = txt.encode('utf-8')
    return urllib.quote_plus(txt)


@register.filter
def digitgroupseparator(number):
    """AKA ``thousands separator'' - 1000000 becomes 1,000,000 """

    if type(number) is not int:
        return number

    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

    return locale.format('%d', number, True)


@register.function
def recursive_state_filter(state, root):
    apps = []
    for app_name in state:
        if not root:
            if not state[app_name].get('depends_on', []):
                apps.append((app_name, state[app_name]))
        elif root in state[app_name].get('depends_on', []):
            apps.append((app_name, state[app_name]))

    apps.sort()
    return apps


@register.filter
def js_date(dt, format='ddd, MMM D, YYYY, h:mma UTCZZ', enable_timeago=True):
    """ Python datetime to a time tag with JS Date.parse-parseable format. """
    dt_date = dt.strftime('%m/%d/%Y')
    dt_time = dt.strftime('%H:%M')
    dt_tz = dt.tzname() or 'UTC'
    formatted_datetime = ' '.join([dt_date, dt_time, dt_tz])
    timeago = 'timeago ' if enable_timeago else ''
    return jinja2.Markup('<time datetime="%s" class="%sjstime"'
                         ' data-format="%s">%s</time>'
                         % (dt.isoformat(), timeago,
                            format, formatted_datetime))


@register.filter
def scrub_pii(content):
    return scrubber.scrub_string(content, scrubber.EMAIL, '(email removed)')


@register.filter
def json_dumps(data):
    return jinja2.Markup(json.dumps(data))

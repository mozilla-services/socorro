import datetime
import json
import re
import urllib

import isodate
import jinja2
import humanfriendly

from django_jinja import library

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.template import engines
from django.utils.safestring import mark_safe

from crashstats import scrubber
from crashstats.crashstats.utils import parse_isodate


@library.filter
def split(value, separator):
    return value.split(separator)


@library.global_function
def truncatechars(str_, max_length):
    if len(str_) < max_length:
        return str_
    else:
        return '%s...' % str_[:max_length - len('...')]


@library.filter
def urlencode(txt):
    """Url encode a path.

    This function ensures white spaces are encoded with '%20' and not '+'.
    """
    if not isinstance(txt, basestring):
        # Do nothing on non-strings.
        return txt
    if isinstance(txt, unicode):
        txt = txt.encode('utf-8')
    return urllib.quote_plus(txt).replace('+', '%20')


@library.filter
def digitgroupseparator(number):
    """AKA ``thousands separator'' - 1000000 becomes 1,000,000 """
    if not isinstance(number, (long, int)):
        return number
    return format(number, ',')


@library.global_function
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


@library.filter
def timestamp_to_date(
    timestamp,
    format='%Y-%m-%d %H:%M:%S'
):
    """ Python datetime to a time tag with JS Date.parse-parseable format. """
    try:
        timestamp = float(timestamp)
    except (TypeError, ValueError):
        # By returning an empty string, when using this filter in templates
        # on an invalid value, it becomes ''. For example:
        #
        #  <span>{{ some_timestamp | timestamp_to_date }}</span>
        #
        # then becomes:
        #
        #  <span></span>
        return ''

    dt = datetime.datetime.fromtimestamp(float(timestamp))
    return jinja2.Markup(
        '<time datetime="{}" class="jstime" data-format="{}">{}</time>'
        .format(
            dt.isoformat(),
            format,
            dt.strftime(format)
        )
    )


@library.filter
def time_tag(dt, format='%a, %b %d %H:%M %Z', future=False):
    if not isinstance(dt, (datetime.date, datetime.datetime)):
        try:
            dt = parse_isodate(dt)
        except isodate.ISO8601Error:
            return dt
    return jinja2.Markup(
        '<time datetime="{}" class="{}">{}</time>'
        .format(
            dt.isoformat(),
            future and 'in' or 'ago',
            dt.strftime(format)
        )
    )


@library.global_function
def datetime_picker(input_name, default_value):
    """Return a datetime picker HTML element to be powered by a JS library.
    """
    return jinja2.Markup(
        '''
        <span
            class="datetime-picker {input_name}"
            data-wrap="true"
            data-enable-time="true"
            data-utc="true"
            data-time_24hr="true"
            data-alt-input="true"
            data-date-format="Y-m-d\TH:i:S\Z"
            data-alt-format="F j, Y - H:i"
            date-default-date="{default_value}"
        >
            <input
                type="date"
                name="{input_name}"
                value="{default_value}"
                data-input
            ><a data-toggle><i class="icon-calendar"></i></a>
        </span>
        '''.format(
            input_name=input_name,
            # We need special formatting here because that's the only timezone
            # format the JS library will correctly parse.
            default_value=default_value.strftime('%Y-%m-%dT%H:%M:%SZ'),
        )
    )


@library.filter
def human_readable_iso_date(dt):
    """ Python datetime to a human readable ISO datetime. """
    if not isinstance(dt, (datetime.date, datetime.datetime)):
        try:
            dt = parse_isodate(dt)
        except isodate.ISO8601Error:
            # Because we're paranoid, we don't want to fail
            # the whole template rendering just because one date
            # couldn't be displayed in a more human readable format.
            # This, for example, can happen if the date isn't really
            # valid but something. E.g. 2015-10-10 15:32:07.620535
            return dt

    format = '%Y-%m-%d %H:%M:%S'
    return dt.strftime(format)


@library.filter
def scrub_pii(content):
    content = scrubber.scrub_string(content, scrubber.EMAIL, '(email removed)')
    content = scrubber.scrub_string(content, scrubber.URL, '(URL removed)')
    return content


@library.filter
def json_dumps(data):
    return jinja2.Markup(
        json.dumps(data).replace('</', '<\\/')
    )


@library.filter
def to_json(data):
    return json.dumps(data).replace('</', '<\\/')


@library.global_function
def show_bug_link(bug_id):
    data = {'bug_id': bug_id, 'class': ['bug-link']}
    tmpl = (
        '<a href="https://bugzilla.mozilla.org/show_bug.cgi?id=%(bug_id)s" '
        'title="Find more information in Bugzilla" '
        'data-id="%(bug_id)s" '
    )
    # if available, set some data attributes on the link from our cache
    cache_key = 'buginfo:%s' % bug_id
    information = cache.get(cache_key)
    if information:
        tmpl += (
            'data-summary="%(summary)s" '
            'data-resolution="%(resolution)s" '
            'data-status="%(status)s" '
        )
        data.update(information)
        data['class'].append('bug-link-with-data')
    else:
        data['class'].append('bug-link-without-data')

    tmpl += (
        'class="%(class)s">%(bug_id)s</a>'
    )
    data['class'] = ' '.join(data['class'])
    return jinja2.Markup(tmpl) % data


@library.global_function
def read_crash_column(crash, column_key):
    if 'raw_crash' in crash:
        raw_crash = crash['raw_crash'] or {}
        return raw_crash.get(column_key, crash.get(column_key, ''))
    return crash.get(column_key, '')


@library.global_function
def bugzilla_submit_url(report, bug_product):
    url = 'https://bugzilla.mozilla.org/enter_bug.cgi'
    # Some crashes has the `os_name` but it's null so we
    # fall back on an empty string on it instead. That way the various
    # `.startswith(...)` things we do don't raise an AttributeError.
    op_sys = report.get('os_pretty_version') or report['os_name'] or ''
    # At the time of writing, these pretty versions of the OS name
    # don't perfectly fit with the drop-down choices that Bugzilla
    # has in its OS drop-down. So we have to make some adjustments.
    if op_sys.startswith('OS X '):
        op_sys = 'Mac OS X'
    elif op_sys == 'Windows 8.1':
        op_sys = 'Windows 8'
    elif op_sys in ('Windows Unknown', 'Windows 2000'):
        op_sys = 'Windows'

    kwargs = {
        'bug_severity': 'critical',
        'keywords': 'crash',
        'product': bug_product,
        'op_sys': op_sys,
        'rep_platform': report['cpu_name'],
        'cf_crash_signature': '[@ {}]'.format(report['signature']),
        'short_desc': 'Crash in {}'.format(report['signature']),
        'comment': (
            'This bug was filed from the Socorro interface and is \n'
            'report bp-{}.\n'
            '{}'
            '\n'
        ).format(
            report['uuid'],
            '=' * 61
        ),
    }

    # some special keys have to be truncated to make Bugzilla happy
    if len(kwargs['short_desc']) > 255:
        kwargs['short_desc'] = kwargs['short_desc'][:255 - 3] + '...'

    # People who are new to bugzilla automatically get the more
    # basic, "guided format". for entering bugs. This unfortunately
    # means that all the parameters we pass along gets lost when
    # the user makes it to the second page. Let's prevent that.
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=1238212
    kwargs['format'] = '__default__'

    url += '?' + urllib.urlencode(kwargs, True)
    return url


@library.filter
def replace_bugzilla_links(text):
    """Returns a text with any bugzilla URL replaced with a link to that URL
    with a nice 'Bug XXX' text. """
    bugzilla_finder = re.compile(
        '(https?://bugzilla.mozilla.org/show_bug.cgi\?id='
        '([0-9]*)[a-zA-Z0-9#&=]*)'
    )

    # Sanitize the text first, before adding some HTML into it.
    text = text.replace('</', '<\\/')

    return jinja2.Markup(
        bugzilla_finder.sub(r'<a href="\1">Bug \2</a>', text)
    )


@library.global_function
def full_url(request, *args, **kwargs):
    """Just like the `url` method of jinja, but with a scheme and host.
    """
    return '{}://{}{}'.format(
        request.scheme,
        request.get_host(),
        reverse(*args, args=kwargs.values())
    )


@library.global_function
def is_list(value):
    return isinstance(value, (list, tuple))


@library.global_function
def show_duration(seconds, unit='seconds'):
    """Instead of just showing the integer number of seconds
    we display it nicely like::

        125 seconds <span>(2 minutes, 5 seconds)</span>

    If we can't do it, just return as is.
    """
    template = engines['backend'].from_string(
        '{{ seconds_str }} {{ unit }} '
        '{% if seconds > 60 %}'
        '<span class="humanized" title="{{ seconds_str }} {{ unit }}">'
        '({{ humanized }})</span>'
        '{% endif %}'
    )

    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        # ValueErrors happen when `seconds` is not a number.
        # TypeErrors happen when you try to convert a None to an integer.

        # Bail, but note how it's NOT marked as safe.
        # That means that if `seconds` is literally '<script>'
        # it will be sent to the template rendering engine to be
        # dealt with and since it's not marked safe, it'll be automatically
        # escaped.
        return seconds

    humanized = humanfriendly.format_timespan(seconds)
    return mark_safe(template.render({
        'seconds_str': format(seconds, ','),
        'seconds': seconds,
        'unit': unit,
        'humanized': humanized,
    }).strip())


@library.global_function
def show_filesize(bytes, unit='bytes'):
    """Instead of just showing the integer number of bytes
    we display it nicely like::

        12345678 <span title="12345678 bytes">(11.77 MB)</span>

    If we can't do it, just return as is.
    """
    template = engines['backend'].from_string(
        '{{ bytes_str }} {{ unit }} '
        '{% if bytes > 1024 %}'
        '<span class="humanized" title="{{ bytes_str }} {{ unit }}">'
        '({{ humanized }})</span>'
        '{% endif %}'
    )

    try:
        bytes = int(bytes)
    except (ValueError, TypeError):
        # ValueErrors happen when `bytes` is not a number.
        # TypeErrors happen when you try to convert a None to an integer.

        # Bail but note how it's NOT marked as safe.
        # That means that if `bytes` is literally '<script>'
        # it will be sent to the template rendering engine to be
        # dealt with and since it's not marked safe, it'll be automatically
        # escaped.
        return bytes

    humanized = humanfriendly.format_size(bytes)
    return mark_safe(template.render({
        'bytes_str': format(bytes, ','),
        'bytes': bytes,
        'unit': unit,
        'humanized': humanized,
    }).strip())


@library.global_function
def booleanish_to_boolean(value):
    return str(value).lower() in ('1', 'true', 'yes')

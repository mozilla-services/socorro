# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from itertools import islice
import json
import re
from urllib.parse import urlencode, parse_qs, quote_plus

from django_jinja import library
import humanfriendly
import isodate
import jinja2
import markupsafe

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import cache
from django.template import engines
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_str

from crashstats.crashstats.utils import parse_isodate, urlencode_obj


@library.global_function
def minimum(item1, item2):
    """Returns the minimum of two items"""
    return min(item1, item2)


@library.global_function
def truncatechars(str_, max_length):
    """Truncates a string to max_length and adds ... to the end"""
    if len(str_) < max_length:
        return str_
    else:
        return "%s..." % str_[: max_length - len("...")]


@library.filter
def digitgroupseparator(number):
    """AKA ``thousands separator'' - 1000000 becomes 1,000,000"""
    if not isinstance(number, int):
        return number
    return format(number, ",")


@library.filter
def buildid_to_date(buildid, fmt="%Y-%m-%d"):
    """Returns the date portion of the build id"""
    try:
        dt = datetime.datetime.strptime(buildid[0:8], "%Y%m%d")
    except (TypeError, ValueError):
        return ""

    return markupsafe.Markup(
        '<time datetime="{}" class="jstime" data-format="{}">{}</time>'.format(
            dt.isoformat(), fmt, dt.strftime(fmt)
        )
    )


@library.filter
def timestamp_to_date(timestamp, fmt="%Y-%m-%d %H:%M:%S"):
    """Python datetime to a time tag with JS Date.parse-parseable format"""
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
        return ""

    try:
        dt = datetime.datetime.fromtimestamp(float(timestamp))
    except OverflowError:
        return ""

    return markupsafe.Markup(
        '<time datetime="{}" class="jstime" data-format="{}">{}</time>'.format(
            dt.isoformat(), fmt, dt.strftime(fmt)
        )
    )


@library.filter
def time_tag(dt, format="%a, %b %d, %Y at %H:%M %Z", future=False):
    if not isinstance(dt, (datetime.date, datetime.datetime)):
        try:
            dt = parse_isodate(dt)
        except isodate.ISO8601Error:
            return dt
    return markupsafe.Markup(
        '<time datetime="{}" class="{}">{}</time>'.format(
            dt.isoformat(), future and "in" or "ago", dt.strftime(format)
        )
    )


@library.filter
def human_readable_iso_date(dt):
    """Python datetime to a human readable ISO datetime."""
    if not isinstance(dt, (datetime.date, datetime.datetime)):
        if not dt:
            return ""
        try:
            dt = parse_isodate(dt)
        except isodate.ISO8601Error:
            # Because we're paranoid, we don't want to fail
            # the whole template rendering just because one date
            # couldn't be displayed in a more human readable format.
            # This, for example, can happen if the date isn't really
            # valid but something. E.g. 2015-10-10 15:32:07.620535
            return dt

    format = "%Y-%m-%d %H:%M:%S"
    return dt.strftime(format)


@library.filter
def to_json(data):
    return json.dumps(data).replace("</", "<\\/")


@library.global_function
def show_bug_link(bug_id):
    data = {"bug_id": bug_id, "class": ["bug-link"]}
    tmpl = (
        '<a href="https://bugzilla.mozilla.org/show_bug.cgi?id=%(bug_id)s" '
        'title="Find more information in Bugzilla" '
        'data-id="%(bug_id)s" '
    )
    # if available, set some data attributes on the link from our cache
    cache_key = "buginfo:%s" % bug_id
    information = cache.get(cache_key)
    if information:
        tmpl += (
            'data-summary="%(summary)s" '
            'data-resolution="%(resolution)s" '
            'data-status="%(status)s" '
        )
        data.update(information)
        data["class"].append("bug-link-with-data")
    else:
        data["class"].append("bug-link-without-data")

    tmpl += 'class="%(class)s">%(bug_id)s</a>'
    data["class"] = " ".join(data["class"])
    return markupsafe.Markup(tmpl) % data


EXTRA_NEWLINES_RE = re.compile(r"\n\n\n+")

MAX_TITLE_LENGTH = 255


@library.global_function
def generate_create_bug_url(
    request, template, raw_crash, report, parsed_dump, crashing_thread
):
    parsed_dump = parsed_dump or {}

    # Some crashes has the `os_name` but it's null so we
    # fall back on an empty string on it instead. That way the various
    # `.startswith(...)` things we do don't raise an AttributeError.
    op_sys = report.get("os_pretty_version") or report["os_name"] or ""

    # At the time of writing, these pretty versions of the OS name don't perfectly fit
    # with the drop-down choices that Bugzilla has in its OS drop-down. So we have to
    # make some adjustments.
    if op_sys.startswith("OS X "):
        op_sys = "macOS"
    elif op_sys == "Windows 8.1":
        op_sys = "Windows 8"
    elif op_sys in ("Windows Unknown", "Windows 2000"):
        op_sys = "Windows"

    frames = None
    threads = parsed_dump.get("threads")
    if threads:
        thread_index = crashing_thread or 0
        frames = bugzilla_thread_frames(parsed_dump["threads"][thread_index])

    comment = render_to_string(
        "crashstats/bug_comment.txt",
        {
            "request": request,
            "uuid": report["uuid"],
            # NOTE(willkg): this is the redacted stack trace--not the raw one that can
            # have PII in it
            "java_stack_trace": report.get("java_stack_trace", None),
            # NOTE(willkg): this is the redacted mozcrashreason--not the raw one that
            # can have PII in it
            "moz_crash_reason": report.get("moz_crash_reason", None),
            "reason": report.get("reason", None),
            "frames": frames,
            "crashing_thread": crashing_thread,
        },
    )

    # Whitespace is a nightmare when using Jinja2 templates to render text that's not
    # destined for HTML. So we do a pass on removing extra line endings.
    comment = EXTRA_NEWLINES_RE.sub("\n\n", comment)

    kwargs = {
        "bug_type": "defect",
        "op_sys": op_sys,
        "rep_platform": report["cpu_arch"],
        "signature": "[@ {}]".format(smart_str(report["signature"])),
        "title": "Crash in [@ {}]".format(smart_str(report["signature"])),
        "description": comment,
    }

    # Truncate the title
    if len(kwargs["title"]) > MAX_TITLE_LENGTH:
        kwargs["title"] = kwargs["title"][: MAX_TITLE_LENGTH - 3] + "..."

    # urlencode the values so they work in the url template correctly
    kwargs = {key: quote_plus(value) for key, value in kwargs.items()}
    return template % kwargs


def bugzilla_thread_frames(thread):
    """Build frame information for bug creation link

    Extract frame info for the top frames of a crashing thread to be included in the
    Bugzilla summary when reporting the crash.

    :arg thread: dict of thread information including "frames" list

    :returns: list of frame information dicts

    """

    def frame_generator(thread):
        """Yield frames in a thread factoring in inlines"""
        for frame in thread["frames"]:
            for inline in frame.get("inlines") or []:
                yield {
                    "frame": frame.get("frame", "?"),
                    "module": frame.get("module", ""),
                    "signature": inline["function"],
                    "file": inline["file"],
                    "line": inline["line"],
                }

            yield frame

    # We only want to include 10 frames in the link
    MAX_FRAMES = 10

    frames = []
    for frame in islice(frame_generator(thread), MAX_FRAMES):
        # Source is an empty string if data isn't available
        source = frame.get("file") or ""
        if frame.get("line"):
            source += ":{}".format(frame["line"])

        signature = frame.get("signature") or ""

        # Remove function arguments
        if not signature.startswith("(unloaded"):
            signature = re.sub(r"\(.*\)", "", signature)

        frames.append(
            {
                "frame": frame.get("frame", "?"),
                "module": frame.get("module") or "?",
                "signature": signature,
                "source": source,
            }
        )

    return frames


BUG_RE = re.compile(r"(bug #?(\d+))")


@library.filter
def replace_bugzilla_links(text):
    """Replaces "bug #xxx" with a link to bugzilla

    Note, run this after escape::

        {{ data | escape | replace_bugzilla_links }}

    """
    # Convert text from Markup/str to a str so it doesn't escape the substituted
    # text, then return as a Markup because it's safe
    return markupsafe.Markup(
        BUG_RE.sub(
            r'<a href="https://bugzilla.mozilla.org/show_bug.cgi?id=\2">\1</a>',
            str(text),
        )
    )


@library.global_function
def full_url(request, *args, **kwargs):
    """Just like the `url` method of jinja, but with a scheme and host."""
    return "{}://{}{}".format(
        request.scheme, request.get_host(), reverse(*args, args=kwargs.values())
    )


@library.global_function
def is_list(value):
    return isinstance(value, (list, tuple))


@library.global_function
def show_delta_duration(time1, time2, unit="seconds"):
    """Converts the delta of the two (time2 - time1) and displays in unit.

    Returns "" if time values aren't valid.

    Returns duration in seconds.

    """
    try:
        time1_dt = parse_isodate(time1)
    except isodate.ISO8601Error:
        time1_dt = None

    try:
        time2_dt = parse_isodate(time2)
    except isodate.ISO8601Error:
        time2_dt = None

    if not time1_dt or not time2_dt:
        return ""

    delta = time2_dt - time1_dt
    delta = delta / datetime.timedelta(seconds=1)

    return show_duration(delta, unit=unit)


@library.global_function
def show_duration(seconds, unit="seconds"):
    """Instead of just showing the integer number of seconds
    we display it nicely like::

        125 seconds <span>(2 minutes, 5 seconds)</span>

    If we can't do it, just return as is.
    """
    template = engines["backend"].from_string(
        "{{ seconds_str }} {{ unit }} "
        "{% if seconds > 60 %}"
        '<span class="humanized" title="{{ seconds_str }} {{ unit }}">'
        "({{ humanized }})</span>"
        "{% endif %}"
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
    return mark_safe(
        template.render(
            {
                "seconds_str": format(seconds, ","),
                "seconds": seconds,
                "unit": unit,
                "humanized": humanized,
            }
        ).strip()
    )


@library.global_function
def show_filesize(bytes, unit="bytes"):
    """Instead of just showing the integer number of bytes
    we display it nicely like::

        12345678 <span title="12345678 bytes">(11.77 MB)</span>

    If we can't do it, just return as is.
    """
    template = engines["backend"].from_string(
        "{{ bytes_str }} {{ unit }} "
        "{% if bytes > 1024 %}"
        '<span class="humanized" title="{{ bytes_str }} {{ unit }}">'
        "({{ humanized }})</span>"
        "{% endif %}"
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
    return mark_safe(
        template.render(
            {
                "bytes_str": format(bytes, ","),
                "bytes": bytes,
                "unit": unit,
                "humanized": humanized,
            }
        ).strip()
    )


@library.global_function
def booleanish_to_boolean(value):
    return str(value).lower() in ("1", "true", "yes")


@library.global_function
def url(viewname, *args, **kwargs):
    """Makes it possible to construct URLs from templates.

    Because this function is used by taking user input, (e.g. query
    string values), we have to sanitize the values.
    """

    def clean_argument(s):
        if isinstance(s, str):
            # First remove all proper control characters like '\n',
            # '\r' or '\t'.
            s = "".join(c for c in s if ord(c) >= 32)
            # Then, if any '\' left (it might have started as '\\nn')
            # remove those too.
            while "\\" in s:
                s = s.replace("\\", "")
            return s
        return s

    args = [clean_argument(x) for x in args]
    kwargs = {x: clean_argument(y) for x, y in kwargs.items()}

    return reverse(viewname, args=args, kwargs=kwargs)


@library.global_function
def static(path):
    return staticfiles_storage.url(path)


@library.global_function
@jinja2.pass_context
def change_query_string(context, **kwargs):
    """
    Template function for modifying the current URL by parameters.
    You use it like this in a template:

        <a href={{ change_query_string(foo='bar') }}>

    And it takes the current request's URL (and query string) and modifies it
    just by the parameters you pass in. So if the current URL is
    `/page/?day=1` the output of this will become:

        <a href=/page?day=1&foo=bar>

    You can also pass lists like this:

        <a href={{ change_query_string(thing=['bar','foo']) }}>

    And you get this output:

        <a href=/page?day=1&thing=bar&thing=foo>

    And if you want to remove a parameter you can explicitely pass it `None`.
    Like this for example:

        <a href={{ change_query_string(day=None) }}>

    And you get this output:

        <a href=/page>

    """
    if kwargs.get("_no_base"):
        kwargs.pop("_no_base")
        base = ""
    else:
        base = context["request"].META["PATH_INFO"]
    qs = parse_qs(context["request"].META["QUERY_STRING"])
    for key, value in kwargs.items():
        if value is None:
            # delete the parameter
            if key in qs:
                del qs[key]
        else:
            # change it
            qs[key] = value
    new_qs = urlencode(qs, True)

    # We don't like + as the encoding character for spaces. %20 is better.
    new_qs = new_qs.replace("+", "%20")
    if new_qs:
        return "%s?%s" % (base, new_qs)
    return base


@library.global_function
def make_query_string(**kwargs):
    return urlencode_obj(kwargs)


@library.global_function
def is_dangerous_cpu(cpu_arch, cpu_info):
    if not cpu_info:
        return False

    # These models are known to cause lots of crashes, we want to mark them
    # for ease of find by users.
    return (
        cpu_info.startswith("AuthenticAMD family 20 model 1")
        or cpu_info.startswith("AuthenticAMD family 20 model 2")
        or (cpu_arch == "amd64" and cpu_info.startswith("family 20 model 1"))
        or (cpu_arch == "amd64" and cpu_info.startswith("family 20 model 2"))
    )


@library.global_function
def filter_featured_versions(product_versions):
    return [pv for pv in product_versions if pv["is_featured"]]


@library.global_function
def filter_not_featured_versions(product_versions):
    return [pv for pv in product_versions if not pv["is_featured"]]

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import time
from urllib.parse import quote_plus, parse_qs, urlparse

from django.core.cache import cache
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils.safestring import SafeText

from crashstats.crashstats.templatetags.jinja_helpers import (
    bugzilla_submit_url,
    change_query_string,
    digitgroupseparator,
    is_dangerous_cpu,
    replace_bugzilla_links,
    show_bug_link,
    show_duration,
    show_filesize,
    time_tag,
    timestamp_to_date,
    url,
)


class TestTimestampToDate:
    def test_timestamp_to_date(self):
        timestamp = time.time()
        date = datetime.datetime.fromtimestamp(timestamp)
        output = timestamp_to_date(int(timestamp))
        assert date.strftime("%Y-%m-%d %H:%M:%S") in output
        assert "%Y-%m-%d %H:%M:%S" in output

        # Test missing and bogus values.
        output = timestamp_to_date(None)
        assert output == ""

        output = timestamp_to_date("abc")
        assert output == ""


class TestTimeTag:
    def test_time_tag_with_datetime(self):
        date = datetime.datetime(2000, 1, 2, 3, 4, 5)
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            date.isoformat(), date.strftime("%a, %b %d %H:%M %Z")
        )
        assert output == expected

    def test_time_tag_with_date(self):
        date = datetime.date(2000, 1, 2)
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            date.isoformat(), date.strftime("%a, %b %d %H:%M %Z")
        )
        assert output == expected

    def test_time_tag_future(self):
        date = datetime.datetime(2000, 1, 2, 3, 4, 5)
        output = time_tag(date, future=True)

        expected = '<time datetime="{}" class="in">{}</time>'.format(
            date.isoformat(), date.strftime("%a, %b %d %H:%M %Z")
        )
        assert output == expected

    def test_time_tag_invalid_date(self):
        output = time_tag("junk")
        assert output == "junk"

    def test_parse_with_unicode_with_timezone(self):
        # See https://bugzilla.mozilla.org/show_bug.cgi?id=1300921
        date = "2016-09-07T00:38:42.630775+00:00"
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            "2016-09-07T00:38:42.630775+00:00", "Wed, Sep 07 00:38 +00:00"
        )
        assert output == expected


class TestBugzillaLink:
    def test_show_bug_link_no_cache(self):
        output = show_bug_link(123)
        assert 'data-id="123"' in output
        assert "bug-link-without-data" in output
        assert "bug-link-with-data" not in output

    def test_show_bug_link_with_cache(self):
        cache_key = "buginfo:456"
        data = {
            "summary": "<script>xss()</script>",
            "resolution": "MESSEDUP",
            "status": "CONFUSED",
        }
        cache.set(cache_key, data, 5)
        output = show_bug_link(456)
        assert 'data-id="456"' in output
        assert "bug-link-without-data" not in output
        assert "bug-link-with-data" in output
        assert 'data-resolution="MESSEDUP"' in output
        assert 'data-status="CONFUSED"' in output
        assert 'data-summary="&lt;script&gt;xss()&lt;/script&gt;"' in output


class TestBugzillaSubmitURL:
    EMPTY_PARSED_DUMP = {}
    CRASHING_THREAD = 0

    @staticmethod
    def _create_report(**overrides):
        default = {
            "signature": "$&#;deadbeef",
            "uuid": "00000000-0000-0000-0000-000000000000",
            "cpu_arch": "x86",
            "os_name": None,
        }
        return dict(default, **overrides)

    @staticmethod
    def _extract_query_string(url):
        return parse_qs(urlparse(url).query)

    @staticmethod
    def _create_frame(
        frame=1,
        module="fake_module",
        signature="fake_signature",
        file="fake.cpp",
        line=1,
    ):
        return {
            "frame": frame,
            "module": module,
            "signature": signature,
            "file": file,
            "line": line,
        }

    @staticmethod
    def _create_thread(frames=None):
        return {"frames": frames or []}

    @staticmethod
    def _create_dump(threads=None):
        return {"threads": threads or []}

    def test_basic_url(self):
        report = self._create_report(os_name="Windows")
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Plugin"
        )
        assert url.startswith("https://bugzilla.mozilla.org/enter_bug.cgi?")
        qs = self._extract_query_string(url)
        assert "00000000-0000-0000-0000-000000000000" in qs["comment"][0]
        assert qs["cf_crash_signature"] == ["[@ $&#;deadbeef]"]
        assert qs["format"] == ["__default__"]
        assert qs["product"] == ["Plugin"]
        assert qs["rep_platform"] == ["x86"]
        assert qs["short_desc"] == ["Crash in [@ $&#;deadbeef]"]
        assert qs["keywords"] == ["crash"]
        assert qs["op_sys"] == ["Windows"]
        assert qs["bug_type"] == ["defect"]

    def test_truncate_short_desc(self):
        report = self._create_report(os_name="Windows", signature="x" * 1000)
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        qs = self._extract_query_string(url)
        assert len(qs["short_desc"][0]) == 255
        assert qs["short_desc"][0].endswith("...")

    def test_corrected_os_version_name(self):
        report = self._create_report(
            os_name="Windoooosws", os_pretty_version="Windows 10"
        )
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windows 10"]

        # os_name if the os_pretty_version is there, but empty
        report = self._create_report(os_name="Windoooosws", os_pretty_version="")
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windoooosws"]

        # 'OS X <Number>' becomes 'Mac OS X'
        report = self._create_report(os_name="OS X", os_pretty_version="OS X 11.1")
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Mac OS X"]

        # 'Windows 8.1' becomes 'Windows 8'
        report = self._create_report(
            os_name="Windows NT", os_pretty_version="Windows 8.1"
        )
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windows 8"]

        # 'Windows Unknown' becomes plain 'Windows'
        report = self._create_report(
            os_name="Windows NT", os_pretty_version="Windows Unknown"
        )
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        qs = self._extract_query_string(url)
        assert qs["op_sys"] == ["Windows"]

    def test_with_os_name_is_null(self):
        """Some processed crashes haev a os_name but it's null.
        FennecAndroid crashes for example."""
        report = self._create_report(
            os_name=None, signature="java.lang.IllegalStateException"
        )
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        qs = self._extract_query_string(url)
        assert "op_sys" not in qs

    def test_with_unicode_signature(self):
        """The jinja helper bugzilla_submit_url should work when
        the signature contains non-ascii characters.

        Based on an actual error in production:
        https://bugzilla.mozilla.org/show_bug.cgi?id=1383269
        """
        report = self._create_report(
            os_name=None, signature="YouTube\u2122 No Buffer (Stop Auto-playing)"
        )
        url = bugzilla_submit_url(
            report, self.EMPTY_PARSED_DUMP, self.CRASHING_THREAD, "Core"
        )
        # Most important that it should work
        assert (
            "Crash+in+%5B%40+YouTube%E2%84%A2+No+Buffer+%28Stop+Auto-playing%29%5D"
            in url
        )

    def test_comment(self):
        report = self._create_report()
        parsed_dump = self._create_dump(
            threads=[
                self._create_thread(),  # Empty thread 0
                self._create_thread(
                    frames=[
                        self._create_frame(frame=0),
                        self._create_frame(frame=1),
                        self._create_frame(frame=2),
                    ]
                ),
            ]
        )
        url = bugzilla_submit_url(report, parsed_dump, 1, "Core")

        assert quote_plus("bp-" + report["uuid"]) in url
        assert quote_plus("Top 3 frames of crashing thread:") in url

        frame1 = parsed_dump["threads"][1]["frames"][1]
        assert (
            quote_plus("1 {module} {signature} {file}:{line}".format(**frame1)) in url
        )

    def test_comment_no_threads(self):
        """If parsed_dump has no threads available, do not output any
        frames.

        """
        report = self._create_report()
        url = bugzilla_submit_url(report, {}, 0, "Core")
        assert quote_plus("frames of crashing thread:") not in url

    def test_comment_more_than_ten_frames(self):
        """If the crashing thread has more than ten frames, only display
        the top ten.

        """
        report = self._create_report()
        parsed_dump = self._create_dump(
            threads=[
                self._create_thread(
                    frames=[self._create_frame(frame=frame) for frame in range(10)]
                    + [self._create_frame(frame=10, module="do_not_include")]
                )
            ]
        )
        url = bugzilla_submit_url(report, parsed_dump, 0, "Core")
        assert quote_plus("do_not_include") not in url

    def test_comment_remove_arguments(self):
        """If a frame signature includes function arguments, remove
        them.

        """
        report = self._create_report()
        parsed_dump = self._create_dump(
            threads=[
                self._create_thread(
                    frames=[
                        self._create_frame(
                            frame=0,
                            module="test_module",
                            signature="foo::bar(char* x, int y)",
                            file="foo.cpp",
                            line=7,
                        )
                    ]
                )
            ]
        )
        url = bugzilla_submit_url(report, parsed_dump, 0, "Core")
        assert quote_plus("0 test_module foo::bar foo.cpp:7") in url

    def test_comment_missing_line(self):
        """If a frame is missing a line number, do not include it."""
        report = self._create_report()
        parsed_dump = self._create_dump(
            threads=[
                self._create_thread(
                    frames=[
                        self._create_frame(
                            frame=0,
                            module="test_module",
                            signature="foo::bar(char* x, int y)",
                            file="foo.cpp",
                            line=None,
                        )
                    ]
                )
            ]
        )
        url = bugzilla_submit_url(report, parsed_dump, 0, "Core")
        assert quote_plus("0 test_module foo::bar foo.cpp\n") in url

    def test_comment_missing_file(self):
        """If a frame is missing file info, do not include it."""
        report = self._create_report()
        parsed_dump = self._create_dump(
            threads=[
                self._create_thread(
                    frames=[
                        self._create_frame(
                            frame=0,
                            module="test_module",
                            signature="foo::bar(char* x, int y)",
                            file=None,
                            line=None,
                        )
                    ]
                )
            ]
        )
        url = bugzilla_submit_url(report, parsed_dump, 0, "Core")
        assert quote_plus("0 test_module foo::bar \n") in url

    def test_comment_missing_everything(self):
        """If a frame is missing everything, do not throw an error."""
        report = self._create_report()
        parsed_dump = self._create_dump(threads=[self._create_thread(frames=[{}])])
        bugzilla_submit_url(report, parsed_dump, 0, "Core")

    def test_comment_no_html_escaping(self):
        """If a frame contains <, >, &, or ", they should not be HTML
        escaped in the comment body.

        """
        report = self._create_report()
        parsed_dump = self._create_dump(
            threads=[
                self._create_thread(
                    frames=[
                        self._create_frame(
                            frame=0,
                            module="&test_module",
                            signature="foo<char>::bar(char* x, int y)",
                            file='"foo".cpp',
                            line=7,
                        )
                    ]
                )
            ]
        )
        url = bugzilla_submit_url(report, parsed_dump, 0, "Core")
        assert quote_plus('0 &test_module foo<char>::bar "foo".cpp:7') in url

    def test_comment_java_stack_trace(self):
        """If there's a java stack trace, use that instead"""
        report = self._create_report()
        report["java_stack_trace"] = "java.lang.NullPointerException: list == null"
        parsed_dump = self._create_dump(
            threads=[
                self._create_thread(),  # Empty thread 0
                self._create_thread(
                    frames=[
                        self._create_frame(frame=0),
                        self._create_frame(frame=1),
                        self._create_frame(frame=2),
                    ]
                ),
            ]
        )
        url = bugzilla_submit_url(report, parsed_dump, 0, "Core")
        assert quote_plus("Java stack trace:") in url
        assert quote_plus("java.lang.NullPointerException: list == null") in url

        # Make sure it didn't also add the crashing frames
        assert quote_plus("frames of crashing thread:") not in url


class TestReplaceBugzillaLinks:
    def test_simple(self):
        text = "a bug #1129515 b"
        res = replace_bugzilla_links(text)
        expected = 'a <a href="https://bugzilla.mozilla.org/show_bug.cgi?id=1129515">bug #1129515</a> b'
        assert res == expected

    def test_several_bugs(self):
        text = "abc bug #43 def bug #40878 bug #7845"
        res = replace_bugzilla_links(text)
        assert "https://bugzilla.mozilla.org/show_bug.cgi?id=43" in res
        assert "https://bugzilla.mozilla.org/show_bug.cgi?id=40878" in res
        assert "https://bugzilla.mozilla.org/show_bug.cgi?id=7845" in res


class TesDigitGroupSeparator:
    def test_basics(self):
        assert digitgroupseparator(None) is None
        assert digitgroupseparator(1000) == "1,000"
        assert digitgroupseparator(-1000) == "-1,000"
        assert digitgroupseparator(1000000) == "1,000,000"


class TestHumanizers:
    def test_show_duration(self):
        html = show_duration(59)
        assert isinstance(html, SafeText)
        assert html == "59 seconds"

        html = show_duration(150)
        assert isinstance(html, SafeText)
        expected = (
            '150 seconds <span class="humanized" title="150 seconds">'
            "(2 minutes and 30 seconds)</span>"
        )
        assert html == expected

        # if the number is digit but a string it should work too
        html = show_duration("1500")
        expected = (
            '1,500 seconds <span class="humanized" title="1,500 seconds">'
            "(25 minutes)</span>"
        )
        assert html == expected

    def test_show_duration_different_unit(self):
        html = show_duration(150, unit="cool seconds")
        assert isinstance(html, SafeText)
        expected = (
            "150 cool seconds "
            '<span class="humanized" title="150 cool seconds">'
            "(2 minutes and 30 seconds)</span>"
        )
        assert html == expected

    def test_show_duration_failing(self):
        html = show_duration(None)
        assert html is None
        html = show_duration("not a number")
        assert html == "not a number"

    def test_show_duration_safety(self):
        html = show_duration("<script>")
        assert not isinstance(html, SafeText)
        assert html == "<script>"

        html = show_duration(150, unit="<script>")
        assert isinstance(html, SafeText)
        expected = (
            "150 &lt;script&gt; "
            '<span class="humanized" title="150 &lt;script&gt;">'
            "(2 minutes and 30 seconds)</span>"
        )
        assert html == expected

    def test_show_filesize(self):
        html = show_filesize(100)
        assert isinstance(html, SafeText)
        assert html == "100 bytes"

        html = show_filesize(10000)
        assert isinstance(html, SafeText)
        expected = (
            "10,000 bytes "
            '<span class="humanized" title="10,000 bytes">'
            "(10 KB)</span>"
        )
        assert html == expected

        html = show_filesize("10000")
        assert isinstance(html, SafeText)
        expected = (
            "10,000 bytes "
            '<span class="humanized" title="10,000 bytes">'
            "(10 KB)</span>"
        )
        assert html == expected

    def test_show_filesize_failing(self):
        html = show_filesize(None)
        assert html is None

        html = show_filesize("junk")
        assert html == "junk"


class TestChangeURL:
    def test_root_url_no_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/")
        result = change_query_string(context)
        assert result == "/"

    def test_with_path_no_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/")
        result = change_query_string(context)
        assert result == "/page/"

    def test_with_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar&bar=baz")
        result = change_query_string(context)
        assert result == "/page/?foo=bar&bar=baz"

    def test_add_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/")
        result = change_query_string(context, foo="bar")
        assert result == "/page/?foo=bar"

    def test_change_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar")
        result = change_query_string(context, foo="else")
        assert result == "/page/?foo=else"

    def test_remove_query_string(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar")
        result = change_query_string(context, foo=None)
        assert result == "/page/"

    def test_remove_leave_some(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar&other=thing")
        result = change_query_string(context, foo=None)
        assert result == "/page/?other=thing"

    def test_change_query_without_base(self):
        context = {}
        context["request"] = RequestFactory().get("/page/?foo=bar")
        result = change_query_string(context, foo="else", _no_base=True)
        assert result == "?foo=else"


class TestURL:
    def test_basic(self):
        output = url("crashstats:login")
        assert output == reverse("crashstats:login")

        # now with a arg
        output = url("crashstats:product_home", "Firefox")
        assert output == reverse("crashstats:product_home", args=("Firefox",))

        # now with a kwarg
        output = url("crashstats:product_home", product="Waterfox")
        assert output == reverse("crashstats:product_home", args=("Waterfox",))

    def test_arg_cleanup(self):
        output = url("crashstats:product_home", "Firefox\n")
        assert output == reverse("crashstats:product_home", args=("Firefox",))

        output = url("crashstats:product_home", product="\tWaterfox")
        assert output == reverse("crashstats:product_home", args=("Waterfox",))

        # this is something we've seen in the "wild"
        output = url("crashstats:product_home", "Winterfox\\\\nn")
        assert output == reverse("crashstats:product_home", args=("Winterfoxnn",))

        # check that it works if left as a byte string too
        output = url("crashstats:product_home", "Winterfox\\\\nn")
        assert output == reverse("crashstats:product_home", args=("Winterfoxnn",))


class TestIsDangerousCPU:
    def test_false(self):
        assert is_dangerous_cpu(None, None) is False
        assert is_dangerous_cpu(None, "family 20 model 1") is False

    def test_true(self):
        assert is_dangerous_cpu(None, "AuthenticAMD family 20 model 1") is True
        assert is_dangerous_cpu(None, "AuthenticAMD family 20 model 2") is True
        assert is_dangerous_cpu("amd64", "family 20 model 1") is True
        assert is_dangerous_cpu("amd64", "family 20 model 2") is True

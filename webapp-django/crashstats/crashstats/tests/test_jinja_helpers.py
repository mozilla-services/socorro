import datetime
import time
import urlparse

from django.core.cache import cache
from django.utils.safestring import SafeText

from crashstats.base.tests.testbase import TestCase
from crashstats.crashstats.templatetags.jinja_helpers import (
    bugzilla_submit_url,
    digitgroupseparator,
    recursive_state_filter,
    replace_bugzilla_links,
    show_bug_link,
    show_duration,
    show_filesize,
    time_tag,
    timestamp_to_date,
)


class TestTimestampToDate(TestCase):

    def test_timestamp_to_date(self):
        timestamp = time.time()
        date = datetime.datetime.fromtimestamp(timestamp)
        output = timestamp_to_date(int(timestamp))
        assert date.strftime('%Y-%m-%d %H:%M:%S') in output
        assert '%Y-%m-%d %H:%M:%S' in output

        # Test missing and bogus values.
        output = timestamp_to_date(None)
        assert output == ''

        output = timestamp_to_date('abc')
        assert output == ''


class TestTimeTag(TestCase):

    def test_time_tag_with_datetime(self):
        date = datetime.datetime(2000, 1, 2, 3, 4, 5)
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            date.isoformat(),
            date.strftime('%a, %b %d %H:%M %Z')
        )
        assert output == expected

    def test_time_tag_with_date(self):
        date = datetime.date(2000, 1, 2)
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            date.isoformat(),
            date.strftime('%a, %b %d %H:%M %Z')
        )
        assert output == expected

    def test_time_tag_future(self):
        date = datetime.datetime(2000, 1, 2, 3, 4, 5)
        output = time_tag(date, future=True)

        expected = '<time datetime="{}" class="in">{}</time>'.format(
            date.isoformat(),
            date.strftime('%a, %b %d %H:%M %Z')
        )
        assert output == expected

    def test_time_tag_invalid_date(self):
        output = time_tag('junk')
        assert output == 'junk'

    def test_parse_with_unicode_with_timezone(self):
        # See https://bugzilla.mozilla.org/show_bug.cgi?id=1300921
        date = u'2016-09-07T00:38:42.630775+00:00'
        output = time_tag(date)

        expected = '<time datetime="{}" class="ago">{}</time>'.format(
            '2016-09-07T00:38:42.630775+00:00',
            'Wed, Sep 07 00:38 +00:00'
        )
        assert output == expected


class TestRecursiveStateFilter(TestCase):

    def test_basic_recursion(self):
        state = {
            'app1': {'key': 'value1'},
            'app2': {'key': 'value2', 'depends_on': ['app1']},
            'appX': {'key': 'valueX'},
        }
        apps = recursive_state_filter(state, None)
        expected = [
            ('app1', {'key': 'value1'}),
            ('appX', {'key': 'valueX'})
        ]
        assert apps == expected

        apps = recursive_state_filter(state, 'app1')
        expected = [
            ('app2', {'key': 'value2', 'depends_on': ['app1']}),
        ]
        assert apps == expected

        apps = recursive_state_filter(state, 'XXXX')
        assert apps == []


class TestBugzillaLink(TestCase):

    def test_show_bug_link_no_cache(self):
        output = show_bug_link(123)
        assert 'data-id="123"' in output
        assert 'bug-link-without-data' in output
        assert 'bug-link-with-data' not in output

    def test_show_bug_link_with_cache(self):
        cache_key = 'buginfo:456'
        data = {
            'summary': '<script>xss()</script>',
            'resolution': 'MESSEDUP',
            'status': 'CONFUSED',
        }
        cache.set(cache_key, data, 5)
        output = show_bug_link(456)
        assert 'data-id="456"' in output
        assert 'bug-link-without-data' not in output
        assert 'bug-link-with-data' in output
        assert 'data-resolution="MESSEDUP"' in output
        assert 'data-status="CONFUSED"' in output
        assert 'data-summary="&lt;script&gt;xss()&lt;/script&gt;"' in output


class TestBugzillaSubmitURL(TestCase):

    PARSED_DUMP = {}
    CRASHING_THREAD = 0

    @staticmethod
    def _create_report(**overrides):
        default = {
            'signature': '$&#;deadbeef',
            'uuid': '00000000-0000-0000-0000-000000000000',
            'cpu_name': 'x86'
        }
        return dict(default, **overrides)

    @staticmethod
    def _extract_query_string(url):
        return urlparse.parse_qs(urlparse.urlparse(url).query)

    def test_basic_url(self):
        report = self._create_report(os_name='Windows')
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Plugin')
        assert url.startswith('https://bugzilla.mozilla.org/enter_bug.cgi?')
        qs = self._extract_query_string(url)
        assert '00000000-0000-0000-0000-000000000000' in qs['comment'][0]
        assert qs['cf_crash_signature'] == ['[@ $&#;deadbeef]']
        assert qs['format'] == ['__default__']
        assert qs['product'] == ['Plugin']
        assert qs['rep_platform'] == ['x86']
        assert qs['short_desc'] == ['Crash in $&#;deadbeef']
        assert qs['keywords'] == ['crash']
        assert qs['op_sys'] == ['Windows']
        assert qs['bug_severity'] == ['critical']

    def test_truncate_short_desc(self):
        report = self._create_report(
            os_name='Windows',
            signature='x' * 1000
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        qs = self._extract_query_string(url)
        assert len(qs['short_desc'][0]) == 255
        assert qs['short_desc'][0].endswith('...')

    def test_corrected_os_version_name(self):
        report = self._create_report(
            os_name='Windoooosws',
            os_pretty_version='Windows 10',
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        qs = self._extract_query_string(url)
        assert qs['op_sys'] == ['Windows 10']

        # os_name if the os_pretty_version is there, but empty
        report = self._create_report(
            os_name='Windoooosws',
            os_pretty_version='',
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        qs = self._extract_query_string(url)
        assert qs['op_sys'] == ['Windoooosws']

        # 'OS X <Number>' becomes 'Mac OS X'
        report = self._create_report(
            os_name='OS X',
            os_pretty_version='OS X 11.1',
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        qs = self._extract_query_string(url)
        assert qs['op_sys'] == ['Mac OS X']

        # 'Windows 8.1' becomes 'Windows 8'
        report = self._create_report(
            os_name='Windows NT',
            os_pretty_version='Windows 8.1',
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        qs = self._extract_query_string(url)
        assert qs['op_sys'] == ['Windows 8']

        # 'Windows Unknown' becomes plain 'Windows'
        report = self._create_report(
            os_name='Windows NT',
            os_pretty_version='Windows Unknown',
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        qs = self._extract_query_string(url)
        assert qs['op_sys'] == ['Windows']

    def test_with_os_name_is_null(self):
        """Some processed crashes haev a os_name but it's null.
        FennecAndroid crashes for example."""
        report = self._create_report(
            os_name=None,
            signature='java.lang.IllegalStateException',
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        qs = self._extract_query_string(url)
        assert 'op_sys' not in qs

    def test_with_unicode_signature(self):
        """The jinja helper bugzilla_submit_url should work when
        the signature contains non-ascii characters.

        Based on an actual error in production:
        https://bugzilla.mozilla.org/show_bug.cgi?id=1383269
        """
        report = self._create_report(
            os_name=None,
            signature=u'YouTube\u2122 No Buffer (Stop Auto-playing)',
        )
        url = bugzilla_submit_url(report, self.PARSED_DUMP, self.CRASHING_THREAD, 'Core')
        # Most important that it should work
        assert 'Crash+in+YouTube%E2%84%A2+No+Buffer+%28Stop+Auto-playing' in url


class TestReplaceBugzillaLinks(TestCase):
    def test_simple(self):
        text = 'foo https://bugzilla.mozilla.org/show_bug.cgi?id=1129515 bar'
        res = replace_bugzilla_links(text)
        expected = (
            'foo <a href="https://bugzilla.mozilla.org/show_bug.cgi?id='
            '1129515">Bug 1129515</a> bar'
        )
        assert res == expected

    def test_url_http(self):
        text = 'hey http://bugzilla.mozilla.org/show_bug.cgi?id=1129515#c5 ho'
        res = replace_bugzilla_links(text)
        expected = (
            'hey <a href="http://bugzilla.mozilla.org/show_bug.cgi?id='
            '1129515#c5">Bug 1129515</a> ho'
        )
        assert res == expected

    def test_url_with_hash(self):
        text = 'hey https://bugzilla.mozilla.org/show_bug.cgi?id=1129515#c5 ho'
        res = replace_bugzilla_links(text)
        expected = (
            'hey <a href="https://bugzilla.mozilla.org/show_bug.cgi?id='
            '1129515#c5">Bug 1129515</a> ho'
        )
        assert res == expected

    def test_several_urls(self):
        text = '''hey, I https://bugzilla.mozilla.org/show_bug.cgi?id=43 met
        you and this is
        https://bugzilla.mozilla.org/show_bug.cgi?id=40878 but here's my
        https://bugzilla.mozilla.org/show_bug.cgi?id=7845 so call me maybe
        '''
        res = replace_bugzilla_links(text)
        assert 'Bug 43' in res
        assert 'Bug 40878' in res
        assert 'Bug 7845' in res

    def test_several_with_unsafe_html(self):
        text = '''malicious <script></script> tag
        for https://bugzilla.mozilla.org/show_bug.cgi?id=43
        '''
        res = replace_bugzilla_links(text)
        assert '</script>' not in res
        assert 'Bug 43' in res
        assert '</a>' in res


class TesDigitGroupSeparator(TestCase):

    def test_basics(self):
        assert digitgroupseparator(None) is None
        assert digitgroupseparator(1000) == '1,000'
        assert digitgroupseparator(-1000) == '-1,000'
        assert digitgroupseparator(1000000L) == '1,000,000'


class TestHumanizers(TestCase):

    def test_show_duration(self):
        html = show_duration(59)
        assert isinstance(html, SafeText)
        assert html == '59 seconds'

        html = show_duration(150)
        assert isinstance(html, SafeText)
        expected = (
            '150 seconds <span class="humanized" title="150 seconds">'
            '(2 minutes and 30 seconds)</span>'
        )
        assert html == expected

        # if the number is digit but a string it should work too
        html = show_duration('1500')
        expected = (
            '1,500 seconds <span class="humanized" title="1,500 seconds">'
            '(25 minutes)</span>'
        )
        assert html == expected

    def test_show_duration_different_unit(self):
        html = show_duration(150, unit='cool seconds')
        assert isinstance(html, SafeText)
        expected = (
            '150 cool seconds '
            '<span class="humanized" title="150 cool seconds">'
            '(2 minutes and 30 seconds)</span>'
        )
        assert html == expected

    def test_show_duration_failing(self):
        html = show_duration(None)
        assert html is None
        html = show_duration('not a number')
        assert html == 'not a number'

    def test_show_duration_safety(self):
        html = show_duration('<script>')
        assert not isinstance(html, SafeText)
        assert html == '<script>'

        html = show_duration(150, unit='<script>')
        assert isinstance(html, SafeText)
        expected = (
            '150 &lt;script&gt; '
            '<span class="humanized" title="150 &lt;script&gt;">'
            '(2 minutes and 30 seconds)</span>'
        )
        assert html == expected

    def test_show_filesize(self):
        html = show_filesize(100)
        assert isinstance(html, SafeText)
        assert html == '100 bytes'

        html = show_filesize(10000)
        assert isinstance(html, SafeText)
        expected = (
            '10,000 bytes '
            '<span class="humanized" title="10,000 bytes">'
            '(9.77 KB)</span>'
        )
        assert html == expected

        html = show_filesize('10000')
        assert isinstance(html, SafeText)
        expected = (
            '10,000 bytes '
            '<span class="humanized" title="10,000 bytes">'
            '(9.77 KB)</span>'
        )
        assert html == expected

    def test_show_filesize_failing(self):
        html = show_filesize(None)
        assert html is None

        html = show_filesize('junk')
        assert html == 'junk'

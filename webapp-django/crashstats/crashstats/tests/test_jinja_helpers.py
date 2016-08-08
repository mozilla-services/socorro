import datetime
import time
import urlparse

from nose.tools import eq_, ok_

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
    timestamp_to_date,
)


class TestTimestampToDate(TestCase):

    def test_timestamp_to_date(self):
        timestamp = time.time()
        date = datetime.datetime.fromtimestamp(timestamp)
        output = timestamp_to_date(int(timestamp))
        ok_(date.strftime('%Y-%m-%d %H:%M:%S') in output)
        ok_('%Y-%m-%d %H:%M:%S' in output)

        # Test missing and bogus values.
        output = timestamp_to_date(None)
        eq_(output, '')

        output = timestamp_to_date('abc')
        eq_(output, '')


class TestRecursiveStateFilter(TestCase):

    def test_basic_recursion(self):
        state = {
            'app1': {'key': 'value1'},
            'app2': {'key': 'value2', 'depends_on': ['app1']},
            'appX': {'key': 'valueX'},
        }
        apps = recursive_state_filter(state, None)
        eq_(
            apps,
            [
                ('app1', {'key': 'value1'}),
                ('appX', {'key': 'valueX'})
            ]
        )

        apps = recursive_state_filter(state, 'app1')
        eq_(
            apps,
            [
                ('app2', {'key': 'value2', 'depends_on': ['app1']}),
            ]
        )

        apps = recursive_state_filter(state, 'XXXX')
        eq_(apps, [])


class TestBugzillaLink(TestCase):

    def test_show_bug_link_no_cache(self):
        output = show_bug_link(123)
        ok_('data-id="123"' in output)
        ok_('bug-link-without-data' in output)
        ok_('bug-link-with-data' not in output)

    def test_show_bug_link_with_cache(self):
        cache_key = 'buginfo:456'
        data = {
            'summary': '<script>xss()</script>',
            'resolution': 'MESSEDUP',
            'status': 'CONFUSED',
        }
        cache.set(cache_key, data, 5)
        output = show_bug_link(456)
        ok_('data-id="456"' in output)
        ok_('bug-link-without-data' not in output)
        ok_('bug-link-with-data' in output)
        ok_('data-resolution="MESSEDUP"' in output)
        ok_('data-status="CONFUSED"' in output)
        ok_('data-summary="&lt;script&gt;xss()&lt;/script&gt;"' in output)


class TestBugzillaSubmitURL(TestCase):

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
        url = bugzilla_submit_url(report, 'Plugin')
        ok_(url.startswith('https://bugzilla.mozilla.org/enter_bug.cgi?'))
        qs = self._extract_query_string(url)
        ok_('00000000-0000-0000-0000-000000000000' in qs['comment'][0])
        eq_(qs['cf_crash_signature'], ['[@ $&#;deadbeef]'])
        eq_(qs['format'], ['__default__'])
        eq_(qs['product'], ['Plugin'])
        eq_(qs['rep_platform'], ['x86'])
        eq_(qs['short_desc'], ['Crash in $&#;deadbeef'])
        eq_(qs['keywords'], ['crash'])
        eq_(qs['op_sys'], ['Windows'])
        eq_(qs['bug_severity'], ['critical'])

    def test_truncate_short_desc(self):
        report = self._create_report(
            os_name='Windows',
            signature='x' * 1000
        )
        url = bugzilla_submit_url(report, 'Core')
        qs = self._extract_query_string(url)
        eq_(len(qs['short_desc'][0]), 255)
        ok_(qs['short_desc'][0].endswith('...'))

    def test_corrected_os_version_name(self):
        report = self._create_report(
            os_name='Windoooosws',
            os_pretty_version='Windows 10',
        )
        url = bugzilla_submit_url(report, 'Core')
        qs = self._extract_query_string(url)
        eq_(qs['op_sys'], ['Windows 10'])

        # os_name if the os_pretty_version is there, but empty
        report = self._create_report(
            os_name='Windoooosws',
            os_pretty_version='',
        )
        url = bugzilla_submit_url(report, 'Core')
        qs = self._extract_query_string(url)
        eq_(qs['op_sys'], ['Windoooosws'])

        # 'OS X <Number>' becomes 'Mac OS X'
        report = self._create_report(
            os_name='OS X',
            os_pretty_version='OS X 11.1',
        )
        url = bugzilla_submit_url(report, 'Core')
        qs = self._extract_query_string(url)
        eq_(qs['op_sys'], ['Mac OS X'])

        # 'Windows 8.1' becomes 'Windows 8'
        report = self._create_report(
            os_name='Windows NT',
            os_pretty_version='Windows 8.1',
        )
        url = bugzilla_submit_url(report, 'Core')
        qs = self._extract_query_string(url)
        eq_(qs['op_sys'], ['Windows 8'])

        # 'Windows Unknown' becomes plain 'Windows'
        report = self._create_report(
            os_name='Windows NT',
            os_pretty_version='Windows Unknown',
        )
        url = bugzilla_submit_url(report, 'Core')
        qs = self._extract_query_string(url)
        eq_(qs['op_sys'], ['Windows'])

    def test_with_os_name_is_null(self):
        """Some processed crashes haev a os_name but it's null.
        FennecAndroid crashes for example."""
        report = self._create_report(
            os_name=None,
            signature='java.lang.IllegalStateException',
        )
        url = bugzilla_submit_url(report, 'Core')
        qs = self._extract_query_string(url)
        ok_('op_sys' not in qs)


class TestReplaceBugzillaLinks(TestCase):
    def test_simple(self):
        text = 'foo https://bugzilla.mozilla.org/show_bug.cgi?id=1129515 bar'
        res = replace_bugzilla_links(text)
        eq_(
            res,
            'foo <a href="https://bugzilla.mozilla.org/show_bug.cgi?id='
            '1129515">Bug 1129515</a> bar'
        )

    def test_url_http(self):
        text = 'hey http://bugzilla.mozilla.org/show_bug.cgi?id=1129515#c5 ho'
        res = replace_bugzilla_links(text)
        eq_(
            res,
            'hey <a href="http://bugzilla.mozilla.org/show_bug.cgi?id='
            '1129515#c5">Bug 1129515</a> ho'
        )

    def test_url_with_hash(self):
        text = 'hey https://bugzilla.mozilla.org/show_bug.cgi?id=1129515#c5 ho'
        res = replace_bugzilla_links(text)
        eq_(
            res,
            'hey <a href="https://bugzilla.mozilla.org/show_bug.cgi?id='
            '1129515#c5">Bug 1129515</a> ho'
        )

    def test_several_urls(self):
        text = '''hey, I https://bugzilla.mozilla.org/show_bug.cgi?id=43 met
        you and this is
        https://bugzilla.mozilla.org/show_bug.cgi?id=40878 but here's my
        https://bugzilla.mozilla.org/show_bug.cgi?id=7845 so call me maybe
        '''
        res = replace_bugzilla_links(text)
        ok_('Bug 43' in res)
        ok_('Bug 40878' in res)
        ok_('Bug 7845' in res)

    def test_several_with_unsafe_html(self):
        text = '''malicious <script></script> tag
        for https://bugzilla.mozilla.org/show_bug.cgi?id=43
        '''
        res = replace_bugzilla_links(text)
        ok_('</script>' not in res)
        ok_('Bug 43' in res)
        ok_('</a>' in res)


class TesDigitGroupSeparator(TestCase):

    def test_basics(self):
        eq_(digitgroupseparator(None), None)
        eq_(digitgroupseparator(1000), '1,000')
        eq_(digitgroupseparator(-1000), '-1,000')
        eq_(digitgroupseparator(1000000L), '1,000,000')


class TestHumanizers(TestCase):

    def test_show_duration(self):
        html = show_duration(59)
        ok_(isinstance(html, SafeText))
        eq_(
            html,
            '59 seconds'
        )

        html = show_duration(150)
        ok_(isinstance(html, SafeText))
        eq_(
            html,
            '150 seconds <span class="humanized" title="150 seconds">'
            '(2 minutes and 30 seconds)</span>'
        )

        # if the number is digit but a string it should work too
        html = show_duration('1500')
        eq_(
            html,
            '1,500 seconds <span class="humanized" title="1,500 seconds">'
            '(25 minutes)</span>'
        )

    def test_show_duration_different_unit(self):
        html = show_duration(150, unit='cool seconds')
        ok_(isinstance(html, SafeText))
        eq_(
            html,
            '150 cool seconds '
            '<span class="humanized" title="150 cool seconds">'
            '(2 minutes and 30 seconds)</span>'
        )

    def test_show_duration_failing(self):
        html = show_duration(None)
        eq_(html, None)
        html = show_duration('not a number')
        eq_(html, 'not a number')

    def test_show_duration_safety(self):
        html = show_duration('<script>')
        ok_(not isinstance(html, SafeText))
        eq_(html, '<script>')

        html = show_duration(150, unit='<script>')
        ok_(isinstance(html, SafeText))
        eq_(
            html,
            '150 &lt;script&gt; '
            '<span class="humanized" title="150 &lt;script&gt;">'
            '(2 minutes and 30 seconds)</span>'
        )

    def test_show_filesize(self):
        html = show_filesize(100)
        ok_(isinstance(html, SafeText))
        eq_(
            html,
            '100 bytes'
        )

        html = show_filesize(10000)
        ok_(isinstance(html, SafeText))
        eq_(
            html,
            '10,000 bytes '
            '<span class="humanized" title="10,000 bytes">'
            '(9.77 KB)</span>'
        )

        html = show_filesize('10000')
        ok_(isinstance(html, SafeText))
        eq_(
            html,
            '10,000 bytes '
            '<span class="humanized" title="10,000 bytes">'
            '(9.77 KB)</span>'
        )

    def test_show_filesize_failing(self):
        html = show_filesize(None)
        eq_(html, None)

        html = show_filesize('junk')
        eq_(html, 'junk')

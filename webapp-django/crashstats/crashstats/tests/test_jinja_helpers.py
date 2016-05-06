import datetime
import time
import urlparse

from nose.tools import eq_, ok_
from django.core.cache import cache

from crashstats.base.tests.testbase import TestCase
from crashstats.crashstats.templatetags.jinja_helpers import (
    timestamp_to_date,
    recursive_state_filter,
    show_bug_link,
    bugzilla_submit_url,
    digitgroupseparator,
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


class TesDigitGroupSeparator(TestCase):

    def test_basics(self):
        eq_(digitgroupseparator(None), None)
        eq_(digitgroupseparator(1000), '1,000')
        eq_(digitgroupseparator(-1000), '-1,000')
        eq_(digitgroupseparator(1000000L), '1,000,000')

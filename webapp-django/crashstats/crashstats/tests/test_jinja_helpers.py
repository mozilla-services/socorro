import datetime
import time
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

    def test_basic_url(self):
        url = bugzilla_submit_url()
        eq_(
            url,
            'https://bugzilla.mozilla.org/enter_bug.cgi?format=__default__'
        )

    def test_kwargs(self):
        url = bugzilla_submit_url(foo='?&"', numbers=['one', 'two'])
        ok_(url.startswith('https://bugzilla.mozilla.org/enter_bug.cgi?'))
        ok_('format=__default__' in url)
        ok_('foo=%3F%26%22' in url)
        ok_('numbers=one' in url)
        ok_('numbers=two' in url)

        url = bugzilla_submit_url(format='different')
        ok_('format=__default__' not in url)
        ok_('format=different' in url)

    def test_truncate_certain_keys(self):
        url = bugzilla_submit_url(short_desc='x' * 1000)
        ok_('x' * 1000 not in url)
        ok_('x' * (255 - 3) + '...' in url)


class TesDigitGroupSeparator(TestCase):

    def test_basics(self):
        eq_(digitgroupseparator(None), None)
        eq_(digitgroupseparator(1000), '1,000')
        eq_(digitgroupseparator(-1000), '-1,000')

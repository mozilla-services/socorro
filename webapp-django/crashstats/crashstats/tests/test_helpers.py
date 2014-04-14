import datetime
from nose.tools import eq_, ok_
from django.test import TestCase
from django.utils.timezone import utc
from django.core.cache import cache


from crashstats.crashstats.helpers import (
    js_date,
    recursive_state_filter,
    show_bug_link
)


class TestJSDate(TestCase):

    def test_js_date(self):
        # naive date
        date = datetime.datetime.utcnow()
        output = js_date(date)
        ok_(date.strftime('%Y-%m-%dT%H:%M:%S.%f') in output)
        ok_('timeago' in output)

        # aware date
        date = date.replace(tzinfo=utc)
        output = js_date(date)
        ok_(date.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00') in output)


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

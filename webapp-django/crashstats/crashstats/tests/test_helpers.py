import datetime
from nose.tools import eq_, ok_
from django.test import TestCase
from django.utils.timezone import utc

from crashstats.crashstats.helpers import (
    js_date,
    recursive_state_filter
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

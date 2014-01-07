from nose.tools import eq_

from django.test import TestCase
from django.test.client import RequestFactory

from crashstats.base.helpers import (
    change_query_string
)


class TestChangeURL(TestCase):

    def test_root_url_no_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/')
        result = change_query_string(context)
        eq_(result, '/')

    def test_with_path_no_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/')
        result = change_query_string(context)
        eq_(result, '/page/')

    def test_with_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar&bar=baz')
        result = change_query_string(context)
        eq_(result, '/page/?foo=bar&bar=baz')

    def test_add_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/')
        result = change_query_string(context, foo='bar')
        eq_(result, '/page/?foo=bar')

    def test_change_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar')
        result = change_query_string(context, foo='else')
        eq_(result, '/page/?foo=else')

    def test_remove_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar')
        result = change_query_string(context, foo=None)
        eq_(result, '/page/')

    def test_remove_leave_some(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar&other=thing')
        result = change_query_string(context, foo=None)
        eq_(result, '/page/?other=thing')

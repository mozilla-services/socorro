from nose.tools import eq_

from django.test.client import RequestFactory
from django.core.urlresolvers import reverse

from crashstats.base.tests.testbase import TestCase
from crashstats.base.templatetags.jinja_helpers import (
    change_query_string,
    url
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

    def test_change_query_without_base(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar')
        result = change_query_string(context, foo='else', _no_base=True)
        eq_(result, '?foo=else')


class TestURL(TestCase):

    def test_basic(self):
        output = url('crashstats:login')
        eq_(output, reverse('crashstats:login'))

        # now with a arg
        output = url('crashstats:home', 'Firefox')
        eq_(output, reverse('crashstats:home', args=('Firefox',)))

        # now with a kwarg
        output = url('crashstats:home', product='Waterfox')
        eq_(output, reverse('crashstats:home', args=('Waterfox',)))

    def test_arg_cleanup(self):
        output = url('crashstats:home', 'Firefox\n')
        eq_(output, reverse('crashstats:home', args=('Firefox',)))

        output = url('crashstats:home', product='\tWaterfox')
        eq_(output, reverse('crashstats:home', args=('Waterfox',)))

        # this is something we've seen in the "wild"
        output = url('crashstats:home', u'Winterfox\\\\nn')
        eq_(output, reverse('crashstats:home', args=('Winterfoxnn',)))

        # check that it works if left as a byte string too
        output = url('crashstats:home', 'Winterfox\\\\nn')
        eq_(output, reverse('crashstats:home', args=('Winterfoxnn',)))

from django.test.client import RequestFactory
from django.core.urlresolvers import reverse

from crashstats.base.tests.testbase import TestCase
from crashstats.base.templatetags.jinja_helpers import (
    change_query_string,
    is_dangerous_cpu,
    url
)


class TestChangeURL(TestCase):

    def test_root_url_no_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/')
        result = change_query_string(context)
        assert result == '/'

    def test_with_path_no_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/')
        result = change_query_string(context)
        assert result == '/page/'

    def test_with_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar&bar=baz')
        result = change_query_string(context)
        assert result == '/page/?foo=bar&bar=baz'

    def test_add_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/')
        result = change_query_string(context, foo='bar')
        assert result == '/page/?foo=bar'

    def test_change_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar')
        result = change_query_string(context, foo='else')
        assert result == '/page/?foo=else'

    def test_remove_query_string(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar')
        result = change_query_string(context, foo=None)
        assert result == '/page/'

    def test_remove_leave_some(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar&other=thing')
        result = change_query_string(context, foo=None)
        assert result == '/page/?other=thing'

    def test_change_query_without_base(self):
        context = {}
        context['request'] = RequestFactory().get('/page/?foo=bar')
        result = change_query_string(context, foo='else', _no_base=True)
        assert result == '?foo=else'


class TestURL(TestCase):

    def test_basic(self):
        output = url('crashstats:login')
        assert output == reverse('crashstats:login')

        # now with a arg
        output = url('home:home', 'Firefox')
        assert output == reverse('home:home', args=('Firefox',))

        # now with a kwarg
        output = url('home:home', product='Waterfox')
        assert output == reverse('home:home', args=('Waterfox',))

    def test_arg_cleanup(self):
        output = url('home:home', 'Firefox\n')
        assert output == reverse('home:home', args=('Firefox',))

        output = url('home:home', product='\tWaterfox')
        assert output == reverse('home:home', args=('Waterfox',))

        # this is something we've seen in the "wild"
        output = url('home:home', u'Winterfox\\\\nn')
        assert output == reverse('home:home', args=('Winterfoxnn',))

        # check that it works if left as a byte string too
        output = url('home:home', 'Winterfox\\\\nn')
        assert output == reverse('home:home', args=('Winterfoxnn',))


class TestIsDangerousCPU:

    def test_false(self):
        assert is_dangerous_cpu(None, None) is False
        assert is_dangerous_cpu(None, 'family 20 model 1') is False

    def test_true(self):
        assert is_dangerous_cpu(None, 'AuthenticAMD family 20 model 1') is True
        assert is_dangerous_cpu(None, 'AuthenticAMD family 20 model 2') is True
        assert is_dangerous_cpu('amd64', 'family 20 model 1') is True
        assert is_dangerous_cpu('amd64', 'family 20 model 2') is True

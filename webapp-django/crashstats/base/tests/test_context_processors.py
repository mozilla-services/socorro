from nose.tools import eq_, ok_

from django.test.client import RequestFactory
from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse

from crashstats.base import context_processors


class TestContextProcessors(TestCase):

    def test_browserid(self):
        # you're on the root page
        request = RequestFactory().get('/')
        context = context_processors.browserid(request)
        result = context['redirect_next']()
        eq_(result, request.build_absolute_uri())

        # you're on some other page with a query string
        request = RequestFactory().get('/some/other/page', {'foo': 'bar'})
        context = context_processors.browserid(request)
        result = context['redirect_next']()
        eq_(result, request.build_absolute_uri())
        ok_('?foo=bar' in result)

        # you're on the /login/ page
        request = RequestFactory().get(reverse('crashstats.login'))
        context = context_processors.browserid(request)
        result = context['redirect_next']()
        home_url = reverse('crashstats.home', args=(settings.DEFAULT_PRODUCT,))
        eq_(result, home_url)

        # you're on a page with a `?next=` query string
        # you're on some other page with a query string
        request = RequestFactory().get('/', {'next': '/some/page'})
        context = context_processors.browserid(request)
        result = context['redirect_next']()
        eq_(result, '/some/page')

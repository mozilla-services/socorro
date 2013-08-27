import mock

from crashstats.crashstats import middleware
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory


@mock.patch.object(middleware.statsd, 'incr')
class TestAnalyticsMiddleware(TestCase):

    def setUp(self):
        self.req = RequestFactory().get('/firefox-26.a1/')
        self.res = HttpResponse()

    def test_process_response(self, incr):
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.req, self.res)
        assert incr.called

    def test_dot_conversion(self, incr):
        '''ensure 26.a1 is converted to 26-a1'''
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.req, self.res)
        incr.assert_called_with('analytics.GET.firefox-26-a1.200')

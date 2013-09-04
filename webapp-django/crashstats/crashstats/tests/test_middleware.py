import mock

from crashstats.crashstats import middleware
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory


@mock.patch.object(middleware.statsd, 'incr')
class TestAnalyticsMiddleware(TestCase):

    def setUp(self):
        self.simple_req = RequestFactory().get('/firefox/26.a1')
        self.trailing_slash_req = RequestFactory().get('/firefox/26.a1/')
        self.unique_req = RequestFactory().get('/report/pending/bp-1bb31a3/')
        self.res = HttpResponse()

    def test_process_response(self, incr):
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.simple_req, self.res)
        assert incr.called

    def test_dot_conversion(self, incr):
        '''ensure 26.a1 is converted to 26-a1'''
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.simple_req, self.res)
        incr.assert_called_with('analytics.GET.firefox/26-a1.200')

    def test_trailing_slash(self, incr):
        '''ensure trailing slash is only added when present'''
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.trailing_slash_req, self.res)
        incr.assert_called_with('analytics.GET.firefox/26-a1/.200')

    def test_rule_order_precedence(self, incr):
        '''ensure earlier rules are caught before later rules'''
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.unique_req, self.res)
        incr.assert_called_with('analytics.GET.report/pending/bp.200')

    def test_truncate_unique_keys(self, incr):
        '''ensure unique portions of the path are truncated'''
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.unique_req, self.res)
        incr.assert_called_with('analytics.GET.report/pending/bp.200')

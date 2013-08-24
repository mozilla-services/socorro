import mock

from crashstats.crashstats import middleware
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory


@mock.patch.object(middleware.statsd, 'incr')
class TestAnalyticsMiddleware(TestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.res = HttpResponse()

    def test_process_response(self, incr):
        amw = middleware.AnalyticsMiddleware()
        amw.process_response(self.req, self.res)
        assert incr.called

from nose.tools import eq_

from django.test.client import RequestFactory

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats.middleware import SetRemoteAddrFromForwardedFor


class TestSetRemoteAddrFromForwardedFor(DjangoTestCase):

    def test_no_headers(self):
        """should not break if there is no HTTP_X_FORWARDED_FOR"""
        middleware = SetRemoteAddrFromForwardedFor()
        request = RequestFactory().get('/')
        response = middleware.process_request(request)
        eq_(response, None)

    def test_happy_path(self):
        """the first (comma separated) IP in HTTP_X_FORWARDED_FOR should
        update request.META['REMOTE_ADDR']"""
        middleware = SetRemoteAddrFromForwardedFor()
        request = RequestFactory(**{
            'HTTP_X_FORWARDED_FOR': '245.245.245.245 , 100.100.100.100',
            'REMOTE_ADDR': '123.123.123.123',
        }).get('/')
        response = middleware.process_request(request)
        eq_(response, None)
        eq_(request.META['REMOTE_ADDR'], '245.245.245.245')

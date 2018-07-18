from django.test.client import RequestFactory

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats.middleware import SetRemoteAddrFromForwardedFor


class TestSetRemoteAddrFromForwardedFor(DjangoTestCase):

    def test_no_headers(self):
        """Should not break if there is no HTTP_X_REAL_IP"""
        middleware = SetRemoteAddrFromForwardedFor()
        request = RequestFactory().get('/')
        response = middleware.process_request(request)
        assert response is None

    def test_real_ip(self):
        """Ihe IP in HTTP_X_REAL_IP should update
        request.META['REMOTE_ADDR'].

        """
        middleware = SetRemoteAddrFromForwardedFor()
        request = RequestFactory(**{
            'HTTP_X_REAL_IP': '100.100.100.100',
            'REMOTE_ADDR': '123.123.123.123',
        }).get('/')
        response = middleware.process_request(request)
        assert response is None
        assert request.META['REMOTE_ADDR'] == '100.100.100.100'

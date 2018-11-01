from crashstats.crashstats.middleware import SetRemoteAddrFromRealIP


class TestSetRemoteAddrFromRealIP(object):
    def test_no_headers(self, rf):
        """Should not break if there is no HTTP_X_REAL_IP"""
        middleware = SetRemoteAddrFromRealIP()
        request = rf.get('/')
        response = middleware.process_request(request)
        assert response is None

    def test_real_ip(self, rf):
        """Ihe IP in HTTP_X_REAL_IP should update request.META['REMOTE_ADDR']"""
        middleware = SetRemoteAddrFromRealIP()
        request = rf.get('/', HTTP_X_REAL_IP='100.100.100.100', REMOTE_ADDR='123.123.123.123')
        response = middleware.process_request(request)
        assert response is None
        assert request.META['REMOTE_ADDR'] == '100.100.100.100'

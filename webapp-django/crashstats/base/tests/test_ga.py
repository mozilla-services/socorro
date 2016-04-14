import mock
from raven.conf import defaults

from django.test.client import RequestFactory
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.base.ga import track_api_pageview, track_pageview


class TestTrackingPageviews(DjangoTestCase):
    """Note, we're using DjangoTestCase so we can use `with self.settings()`
    in the tests to flip settings around.
    """

    @mock.patch('raven.transport.threaded_requests.AsyncWorker')
    @mock.patch('requests.post')
    @mock.patch('crashstats.base.ga.logger')
    def test_basic_pageview(self, logger, rpost, aw):

        queues_started = []

        def mocked_queue(function, data, headers, success_cb, failure_cb):
            queues_started.append(data)
            function(data, headers, success_cb, failure_cb)

        aw().queue.side_effect = mocked_queue

        request = RequestFactory().get('/some/page')
        request.user = AnonymousUser()
        assert not settings.GOOGLE_ANALYTICS_ID  # the default
        track_pageview(request, 'Test page')
        assert not queues_started

        with self.settings(GOOGLE_ANALYTICS_ID='XYZ-123'):
            # The reason for setting a client_id value is because if we
            # don't set it, it'll be a randomly generated UUID string
            # which we can't know. Then it becomes really hard to do
            # some_mocked_thing.assert_called_with(...)
            track_pageview(request, 'Test page', client_id='mycid')
            assert queues_started

            params = {
                'v': 1,
                't': 'pageview',
                'cid': 'mycid',
                'dh': 'testserver',
                'tid': 'XYZ-123',
                'dt': 'Test page',
                'ds': 'web',
                'dp': '/some/page',
            }
            logger.info.assert_called_with(
                'Successfully attempted to sent pageview to Google '
                'Analytics (%s)',
                params
            )

            rpost.assert_called_with(
                settings.GOOGLE_ANALYTICS_API_URL,
                verify=defaults.CA_BUNDLE,
                data=params,
                timeout=settings.GOOGLE_ANALYTICS_API_TIMEOUT,
                headers={}
            )

        # Now test with a few more parameters and a user that is not
        # anonymous.
        request = RequestFactory(**{
            'REMOTE_ADDR': '123.123.123.123',
            'HTTP_USER_AGENT': 'testingthings 1.0',
        }).get('/other/page?foo=bar')
        user = User.objects.create_user('koblaikahn')
        request.user = user

        with self.settings(GOOGLE_ANALYTICS_ID='XYZ-123'):
            track_pageview(request, 'Test page', client_id='mycid')

            params = {
                'v': 1,
                't': 'pageview',
                'cid': 'mycid',
                'dh': 'testserver',
                'tid': 'XYZ-123',
                'dt': 'Test page',
                'ds': 'web',
                'dp': '/other/page?foo=bar',
                'uid': str(user.id),
                'ua': 'testingthings 1.0',
                'uip': '123.123.123.123',
            }
            logger.info.assert_called_with(
                'Successfully attempted to sent pageview to Google '
                'Analytics (%s)',
                params
            )

            rpost.assert_called_with(
                settings.GOOGLE_ANALYTICS_API_URL,
                verify=defaults.CA_BUNDLE,
                data=params,
                timeout=settings.GOOGLE_ANALYTICS_API_TIMEOUT,
                headers={}
            )

    @mock.patch('raven.transport.threaded_requests.AsyncWorker')
    @mock.patch('requests.post')
    @mock.patch('crashstats.base.ga.logger')
    def test_api_pageview(self, logger, rpost, aw):

        def mocked_queue(function, data, headers, success_cb, failure_cb):
            function(data, headers, success_cb, failure_cb)

        aw().queue.side_effect = mocked_queue

        request = RequestFactory().get('/api/SomeAPI/')
        request.user = AnonymousUser()

        with self.settings(GOOGLE_ANALYTICS_ID='XYZ-123'):
            track_api_pageview(request, client_id='mycid')

            params = {
                'v': 1,
                't': 'pageview',
                'cid': 'mycid',
                'dh': 'testserver',
                'tid': 'XYZ-123',
                'dt': 'API (/api/SomeAPI/)',
                'ds': 'api',
                'dp': '/api/SomeAPI/',
            }
            logger.info.assert_called_with(
                'Successfully attempted to sent pageview to Google '
                'Analytics (%s)',
                params
            )

    @mock.patch('raven.transport.threaded_requests.AsyncWorker')
    @mock.patch('requests.post')
    @mock.patch('crashstats.base.ga.logger')
    def test_basic_pageview_failure(self, logger, rpost, aw):

        def mocked_queue(function, data, headers, success_cb, failure_cb):
            function(data, headers, success_cb, failure_cb)

        aw().queue.side_effect = mocked_queue

        errors_raised = []

        def failing_post(*a, **kw):
            try:
                raise NameError('oh no!')
            except Exception as exp:
                errors_raised.append(exp)
                raise

        rpost.side_effect = failing_post

        request = RequestFactory().get('/some/page')
        request.user = AnonymousUser()

        with self.settings(GOOGLE_ANALYTICS_ID='XYZ-123'):
            track_pageview(request, 'Test page')

            # Note that even those the mocked requests.post method
            # did raise an error, we're still here and things are still
            # working.
            assert errors_raised

            logger.error.assert_called_with(
                'Failed to send GA page tracking (%s)',
                errors_raised[0]
            )

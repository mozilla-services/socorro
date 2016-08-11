import mock
from raven.conf import defaults
from nose.tools import eq_

from django.test.client import RequestFactory
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.core.urlresolvers import reverse

from socorrolib.lib import BadArgumentError

from crashstats.crashstats.models import ProductBuildTypes
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
                'dl': 'http://testserver/some/page',
            }
            logger.info.assert_called_with(
                'Successfully attempted to send pageview to Google '
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
                'dp': '/other/page',
                'uid': str(user.id),
                'ua': 'testingthings 1.0',
                'dl': 'http://testserver/other/page?foo=bar',
            }
            logger.info.assert_called_with(
                'Successfully attempted to send pageview to Google '
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
                'dl': 'http://testserver/api/SomeAPI/',
            }
            logger.info.assert_called_with(
                'Successfully attempted to send pageview to Google '
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

            logger.exception.assert_called_with(
                'Failed to send GA page tracking'
            )

    @mock.patch('raven.transport.threaded_requests.AsyncWorker')
    @mock.patch('crashstats.base.ga.logger')
    def test_basic_pageview_strange_errors(self, logger, aw):

        def mocked_queue(function, data, headers, success_cb, failure_cb):
            raise Exception('crap')

        aw().queue.side_effect = mocked_queue

        request = RequestFactory().get('/some/page')
        request.user = AnonymousUser()

        with self.settings(GOOGLE_ANALYTICS_ID='XYZ-123'):
            track_pageview(request, 'Test page')
            # ANY error inside the queue will get caught
            logger.error.assert_called_with(
                'Failed for unknown reason to send to GA',
                exc_info=True
            )

    @mock.patch('raven.transport.threaded_requests.AsyncWorker')
    @mock.patch('requests.post')
    @mock.patch('crashstats.base.ga.logger')
    def test_api_pageview_decorator(self, logger, rpost, aw):
        """Test when the API is actually used. No fake request object"""

        # Use this mutable to keep track of executions of the mocked queue
        queues = []

        def mocked_queue(function, data, headers, success_cb, failure_cb):
            queues.append(data)
            # Don't need to execute the function because we're only
            # interested in if this queue function got called.

        aw().queue.side_effect = mocked_queue

        # Use this mutable to keep track of executions mocked get.
        # This helps us be certain the get method really is called.
        gets = []

        def mocked_get(**options):
            gets.append(options)
            if options.get('product') == '400':
                raise BadArgumentError('product')
            return {
                'hits': {
                    'release': 0.1,
                    'beta': 1.0,
                }
            }

        ProductBuildTypes.implementation().get = mocked_get

        url = reverse('api:model_wrapper', args=('ProductBuildTypes',))

        with self.settings(GOOGLE_ANALYTICS_ID='XYZ-123'):
            response = self.client.get(url, {'product': 'WaterWolf'})
            eq_(response.status_code, 200)
            eq_(len(queues), 1)  # the mutable
            assert len(gets) == 1
            eq_(queues[0]['dp'], '/api/ProductBuildTypes/')
            eq_(
                queues[0]['dl'],
                'http://testserver/api/ProductBuildTypes/?product=WaterWolf'
            )

            response = self.client.get(url, {'product': '400'})
            assert len(gets) == 2, len(gets)
            eq_(response.status_code, 400)
            eq_(len(queues), 2)
            eq_(queues[1]['dp'], '/api/ProductBuildTypes/')
            eq_(
                queues[1]['dl'],
                'http://testserver/api/ProductBuildTypes/?product=400'
            )

            response = self.client.get(
                url,
                {'product': 'WaterWolf2'},  # different product => no cache
                HTTP_REFERER='example.com'
            )
            assert len(gets) == 3, len(gets)
            eq_(response.status_code, 200)
            eq_(len(queues), 3)

            response = self.client.get(
                url,
                {'product': 'WaterWolf2'},  # different product => no cache
                HTTP_REFERER='http://example.com/page.html',
                HTTP_HOST='example.com',
            )
            assert len(gets) == 3, len(gets)
            eq_(response.status_code, 200)
            eq_(len(queues), 3)  # no increase!

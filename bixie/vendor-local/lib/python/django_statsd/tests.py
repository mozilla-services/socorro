import json
import logging
import sys

from django.conf import settings
from nose.exc import SkipTest
from nose import tools as nose_tools

minimal = {
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'mydatabase'
        }
    },
    'ROOT_URLCONF': '',
    'STATSD_CLIENT': 'django_statsd.clients.null',
    'METLOG': None
}

if not settings.configured:
    settings.configure(**minimal)

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import dictconfig
from django.utils import unittest

import mock
from nose.tools import eq_
from django_statsd.clients import get_client
from django_statsd import middleware

cfg = {
    'version': 1,
    'formatters': {},
    'handlers': {
        'test_statsd_handler': {
            'class': 'django_statsd.loggers.errors.StatsdHandler',
        },
    },
    'loggers': {
        'test.logging': {
            'handlers': ['test_statsd_handler'],
        },
    },
}


@mock.patch.object(middleware.statsd, 'incr')
class TestIncr(TestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.res = HttpResponse()

    def test_graphite_response(self, incr):
        gmw = middleware.GraphiteMiddleware()
        gmw.process_response(self.req, self.res)
        assert incr.called

    def test_graphite_response_authenticated(self, incr):
        self.req.user = mock.Mock()
        self.req.user.is_authenticated.return_value = True
        gmw = middleware.GraphiteMiddleware()
        gmw.process_response(self.req, self.res)
        eq_(incr.call_count, 2)

    def test_graphite_exception(self, incr):
        gmw = middleware.GraphiteMiddleware()
        gmw.process_exception(self.req, None)
        assert incr.called

    def test_graphite_exception_authenticated(self, incr):
        self.req.user = mock.Mock()
        self.req.user.is_authenticated.return_value = True
        gmw = middleware.GraphiteMiddleware()
        gmw.process_exception(self.req, None)
        eq_(incr.call_count, 2)


@mock.patch.object(middleware.statsd, 'timing')
class TestTiming(unittest.TestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.res = HttpResponse()

    def test_request_timing(self, timing):
        func = lambda x: x
        gmw = middleware.GraphiteRequestTimingMiddleware()
        gmw.process_view(self.req, func, tuple(), dict())
        gmw.process_response(self.req, self.res)
        eq_(timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, timing.call_args_list):
            eq_(expected, args[0])

    def test_request_timing_exception(self, timing):
        func = lambda x: x
        gmw = middleware.GraphiteRequestTimingMiddleware()
        gmw.process_view(self.req, func, tuple(), dict())
        gmw.process_exception(self.req, self.res)
        eq_(timing.call_count, 3)
        names = ['view.%s.%s.GET' % (func.__module__, func.__name__),
                 'view.%s.GET' % func.__module__,
                 'view.GET']
        for expected, (args, kwargs) in zip(names, timing.call_args_list):
            eq_(expected, args[0])


class TestClient(unittest.TestCase):

    @mock.patch.object(settings, 'STATSD_CLIENT', 'statsd.client')
    def test_normal(self):
        eq_(get_client().__module__, 'statsd.client')

    @mock.patch.object(settings, 'STATSD_CLIENT',
                       'django_statsd.clients.null')
    def test_null(self):
        eq_(get_client().__module__, 'django_statsd.clients.null')

    @mock.patch.object(settings, 'STATSD_CLIENT',
                       'django_statsd.clients.toolbar')
    def test_toolbar(self):
        eq_(get_client().__module__, 'django_statsd.clients.toolbar')

    @mock.patch.object(settings, 'STATSD_CLIENT',
                       'django_statsd.clients.toolbar')
    def test_toolbar_send(self):
        client = get_client()
        eq_(client.cache, {})
        client.incr('testing')
        eq_(client.cache, {'testing|count': [[1, 1]]})


class TestMetlogClient(unittest.TestCase):

    def check_metlog(self):
        try:
            from metlog.config  import client_from_dict_config
            return client_from_dict_config
        except ImportError:
            raise SkipTest("Metlog is not installed")

    @nose_tools.raises(AttributeError)
    def test_no_metlog(self):
        with mock.patch.object(settings, 'STATSD_CLIENT',
                'django_statsd.clients.moz_metlog'):
            get_client()

    def test_get_client(self):
        client_from_dict_config = self.check_metlog()

        METLOG_CONF = {
            'logger': 'django-statsd',
            'sender': {
                'class': 'metlog.senders.DebugCaptureSender',
            },
        }

        metlog = client_from_dict_config(METLOG_CONF)
        with mock.patch.object(settings, 'METLOG', metlog):
            with mock.patch.object(settings, 'STATSD_CLIENT',
                    'django_statsd.clients.moz_metlog'):

                client = get_client()
                eq_(client.__module__, 'django_statsd.clients.moz_metlog')

    def test_metlog_incr(self):
        client_from_dict_config = self.check_metlog()

        # Need to load within the test in case metlog is not installed
        from metlog.config import client_from_dict_config
        METLOG_CONF = {
            'logger': 'django-statsd',
            'sender': {
                'class': 'metlog.senders.DebugCaptureSender',
            },
        }

        metlog = client_from_dict_config(METLOG_CONF)
        with mock.patch.object(settings, 'METLOG', metlog):
            with mock.patch.object(settings, 'STATSD_CLIENT',
                    'django_statsd.clients.moz_metlog'):

                client = get_client()
                eq_(len(client.metlog.sender.msgs), 0)
                client.incr('testing')
                eq_(len(client.metlog.sender.msgs), 1)

                msg = json.loads(client.metlog.sender.msgs[0])
                eq_(msg['severity'], 6)
                eq_(msg['payload'], '1')
                eq_(msg['fields']['rate'], 1)
                eq_(msg['fields']['name'], 'testing')
                eq_(msg['type'], 'counter')

    def test_metlog_decr(self):
        client_from_dict_config = self.check_metlog()

        # Need to load within the test in case metlog is not installed
        from metlog.config import client_from_dict_config

        METLOG_CONF = {
            'logger': 'django-statsd',
            'sender': {
                'class': 'metlog.senders.DebugCaptureSender',
            },
        }

        metlog = client_from_dict_config(METLOG_CONF)
        with mock.patch.object(settings, 'METLOG', metlog):
            with mock.patch.object(settings, 'STATSD_CLIENT',
                    'django_statsd.clients.moz_metlog'):

                client = get_client()
                eq_(len(client.metlog.sender.msgs), 0)
                client.decr('testing')
                eq_(len(client.metlog.sender.msgs), 1)

                msg = json.loads(client.metlog.sender.msgs[0])
                eq_(msg['severity'], 6)
                eq_(msg['payload'], '-1')
                eq_(msg['fields']['rate'], 1)
                eq_(msg['fields']['name'], 'testing')
                eq_(msg['type'], 'counter')

    def test_metlog_timing(self):
        client_from_dict_config = self.check_metlog()

        # Need to load within the test in case metlog is not installed
        from metlog.config import client_from_dict_config

        METLOG_CONF = {
            'logger': 'django-statsd',
            'sender': {
                'class': 'metlog.senders.DebugCaptureSender',
            },
        }

        metlog = client_from_dict_config(METLOG_CONF)
        with mock.patch.object(settings, 'METLOG', metlog):
            with mock.patch.object(settings, 'STATSD_CLIENT',
                    'django_statsd.clients.moz_metlog'):

                client = get_client()
                eq_(len(client.metlog.sender.msgs), 0)
                client.timing('testing', 512, rate=2)
                eq_(len(client.metlog.sender.msgs), 1)

                msg = json.loads(client.metlog.sender.msgs[0])
                eq_(msg['severity'], 6)
                eq_(msg['payload'], '512')
                eq_(msg['fields']['rate'], 2)
                eq_(msg['fields']['name'], 'testing')
                eq_(msg['type'], 'timer')


# This is primarily for Zamboni, which loads in the custom middleware
# classes, one of which, breaks posts to our url. Let's stop that.
@mock.patch.object(settings, 'MIDDLEWARE_CLASSES', [])
class TestRecord(TestCase):

    urls = 'django_statsd.urls'

    def setUp(self):
        super(TestRecord, self).setUp()
        self.url = reverse('django_statsd.record')
        settings.STATSD_RECORD_GUARD = None
        self.good = {'client': 'boomerang', 'nt_nav_st': 1,
                     'nt_domcomp': 3}
        self.stick = {'client': 'stick',
                      'window.performance.timing.domComplete': 123,
                      'window.performance.timing.domInteractive': 456,
                      'window.performance.timing.domLoading': 789,
                      'window.performance.timing.navigationStart': 0,
                      'window.performance.navigation.redirectCount': 3,
                      'window.performance.navigation.type': 1}

    def test_no_client(self):
        assert self.client.get(self.url).status_code == 400

    def test_no_valid_client(self):
        assert self.client.get(self.url, {'client': 'no'}).status_code == 400

    def test_boomerang_almost(self):
        assert self.client.get(self.url,
                               {'client': 'boomerang'}).status_code == 400

    def test_boomerang_minimum(self):
        assert self.client.get(self.url,
                               {'client': 'boomerang',
                                'nt_nav_st': 1}).content == 'recorded'

    @mock.patch('django_statsd.views.process_key')
    def test_boomerang_something(self, process_key):
        assert self.client.get(self.url, self.good).content == 'recorded'
        assert process_key.called

    def test_boomerang_post(self):
        assert self.client.post(self.url, self.good).status_code == 405

    def test_good_guard(self):
        settings.STATSD_RECORD_GUARD = lambda r: None
        assert self.client.get(self.url, self.good).status_code == 200

    def test_bad_guard(self):
        settings.STATSD_RECORD_GUARD = lambda r: HttpResponseForbidden()
        assert self.client.get(self.url, self.good).status_code == 403

    def test_stick_get(self):
        assert self.client.get(self.url, self.stick).status_code == 405

    @mock.patch('django_statsd.views.process_key')
    def test_stick(self, process_key):
        assert self.client.post(self.url, self.stick).status_code == 200
        assert process_key.called

    def test_stick_start(self):
        data = self.stick.copy()
        del data['window.performance.timing.navigationStart']
        assert self.client.post(self.url, data).status_code == 400

    @mock.patch('django_statsd.views.process_key')
    def test_stick_missing(self, process_key):
        data = self.stick.copy()
        del data['window.performance.timing.domInteractive']
        assert self.client.post(self.url, data).status_code == 200
        assert process_key.called

    def test_stick_garbage(self):
        data = self.stick.copy()
        data['window.performance.timing.domInteractive'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400

    def test_stick_some_garbage(self):
        data = self.stick.copy()
        data['window.performance.navigation.redirectCount'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400

    def test_stick_more_garbage(self):
        data = self.stick.copy()
        data['window.performance.navigation.type'] = '<alert>'
        assert self.client.post(self.url, data).status_code == 400


@mock.patch.object(middleware.statsd, 'incr')
class TestErrorLog(TestCase):

    def setUp(self):
        dictconfig.dictConfig(cfg)
        self.log = logging.getLogger('test.logging')

    def division_error(self):
        try:
            1 / 0
        except:
            return sys.exc_info()

    def test_emit(self, incr):
        self.log.error('blargh!', exc_info=self.division_error())
        assert incr.call_args[0][0] == 'error.zerodivisionerror'

    def test_not_emit(self, incr):
        self.log.error('blargh!')
        assert not incr.called

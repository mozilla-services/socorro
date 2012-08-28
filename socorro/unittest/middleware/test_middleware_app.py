# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import unittest
import logging
from cStringIO import StringIO
import paste
from paste.fixture import TestApp
import mock
from nose.plugins.attrib import attr
from mock import patch
from configman import ConfigurationManager
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from socorro.webapi.servers import CherryPy
from socorro.lib.util import DotDict
from socorro.middleware import middleware_app
from socorro.webapi.servers import WebServerBase
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)


DSN = {
  "database.database_host": databaseHost.default,
  "database.database_name": databaseName.default,
  "database.database_user": databaseUserName.default,
  "database.database_password": databasePassword.default
}


class MyWSGIServer(WebServerBase):

    def run(self):
        return self


class Response(object):

    def __init__(self, status, body):
        self.status = status
        self.body = body
        self._data = None

    def __repr__(self):
        return "<Response %s: %r>" % (self.status, self.body)

    __str__ = __repr__

    @property
    def data(self):
        assert self.status == 200, self.status
        return json.loads(self.body)


class _AuxImplementation(object):

    def __init__(self, *args, **kwargs):
        self.context = kwargs.get("config")


class AuxImplementation1(_AuxImplementation):

    def get(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100}


class AuxImplementation2(_AuxImplementation):

    def get_age(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100}

    def get_gender(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        return {'gender': 0}


class AuxImplementation3(_AuxImplementation):

    def post(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100}


class AuxImplementation4(_AuxImplementation):

    def put(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100 + int(kwargs.get('add', 0))}


class AuxImplementation5(_AuxImplementation):

    def get(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        return kwargs


class ImplementationWrapperTestCase(unittest.TestCase):

    @patch('logging.info')
    def test_basic_get(self, logging_info):
        # what the middleware app does is that creates a class based on another
        # and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation1

        config = DotDict(
            logger=logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            )
        )
        server = CherryPy(config, (
          ('/aux/(.*)', MadeUp),
        ))

        testapp = TestApp(server._wsgi_func)
        response = testapp.get('/aux/')
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body), {'age': 100})

        logging_info.assert_called_with('Running AuxImplementation1')

        response = testapp.get('/xxxjunkxxx', expect_errors=True)
        self.assertEqual(response.status, 404)

    @patch('logging.info')
    def test_basic_get_args(self, logging_info):
        # what the middleware app does is that creates a class based on another
        # and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation2

        config = DotDict(
            logger=logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            )
        )
        server = CherryPy(config, (
          ('/aux/(age|gender|misconfigured)/(.*)', MadeUp),
        ))

        testapp = TestApp(server._wsgi_func)
        response = testapp.get('/aux/age/')
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body), {'age': 100})
        self.assertEqual(response.header_dict['content-length'],
                         str(len(response.body)))
        self.assertEqual(response.header_dict['content-type'],
                         'application/json')

        logging_info.assert_called_with('Running AuxImplementation2')

        response = testapp.get('/aux/gender/', expect_errors=True)
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body), {'gender': 0})

        # if the URL allows a certain first argument but the implementation
        # isn't prepared for it, it barfs a 405 at you
        response = testapp.get('/aux/misconfigured/', expect_errors=True)
        self.assertEqual(response.status, 405)

    @patch('logging.info')
    def test_basic_post(self, logging_info):
        # what the middleware app does is that creates a class based on another
        # and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation3

        config = DotDict(
            logger=logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            )
        )

        server = CherryPy(config, (
          ('/aux/(.*)', MadeUp),
        ))

        testapp = TestApp(server._wsgi_func)
        response = testapp.post('/aux/')
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body), {'age': 100})

        logging_info.assert_called_with('Running AuxImplementation3')

        response = testapp.get('/aux/', expect_errors=True)
        self.assertEqual(response.status, 405)

    @patch('logging.info')
    def test_put_with_data(self, logging_info):
        # what the middleware app does is that creates a class based on another
        # and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation4

        config = DotDict(
            logger=logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            )
        )

        server = CherryPy(config, (
          ('/aux/(.*)', MadeUp),
        ))

        testapp = TestApp(server._wsgi_func)
        response = testapp.put('/aux/', params={'add': 1})
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body), {'age': 101})

        logging_info.assert_called_with('Running AuxImplementation4')

    @patch('logging.info')
    def test_basic_get_with_parsed_query_string(self, logging_info):
        # what the middleware app does is that creates a class based on another
        # and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation5

        config = DotDict(
            logger=logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            )
        )
        server = CherryPy(config, (
          ('/aux/(.*)', MadeUp),
        ))

        testapp = TestApp(server._wsgi_func)
        response = testapp.get('/aux/foo/bar/names/peter+anders')
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body),
                         {'foo': 'bar',
                          'names': ['peter', 'anders']})

        logging_info.assert_called_with('Running AuxImplementation5')



@attr(integration='postgres')  # for nosetests
class TestMiddlewareApp(unittest.TestCase):
    # test the middleware_app except that we won't start the daemon

    def setUp(self):
        super(TestMiddlewareApp, self).setUp()
        self.uuid = '06a0c9b5-0381-42ce-855a-ccaaa2120116'
        assert 'test' in DSN['database.database_name']
        dsn = ('host=%(database.database_host)s '
               'dbname=%(database.database_name)s '
               'user=%(database.database_user)s '
               'password=%(database.database_password)s' % DSN)
        self.conn = psycopg2.connect(dsn)
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE

    def tearDown(self):
        super(TestMiddlewareApp, self).tearDown()
        self.conn.cursor().execute("""
        TRUNCATE TABLE reports CASCADE;
        """)
        self.conn.commit()

    def _setup_config_manager(self, extra_value_source=None):
        if extra_value_source is None:
            extra_value_source = {}
        extra_value_source['web_server.wsgi_server_class'] = MyWSGIServer
        mock_logging = mock.Mock()
        required_config = middleware_app.MiddlewareApp.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config,
             #logging_required_config(app_name)
             ],
            app_name='middleware',
            app_description=__doc__,
            values_source_list=[{
                'logger': mock_logging,
                #'crontabber.jobs': jobs_string,
                #'crontabber.database_file': json_file,
            }, DSN, extra_value_source]
        )
        return config_manager

    def _get(self, server, url, request_method='GET'):
        response = DotDict()
        def start_response(status, headers):
            response.status = status
            response.headers = dict(headers)
            response.header_items = headers
        env = {}
        env['REQUEST_METHOD'] = request_method
        env['PATH_INFO'] = url
        response_body = ''.join(server._wsgi_func(env, start_response))
        return Response(int(response.status.split()[0]), response_body)

    def _post(self, server, url, data=None):
        response = DotDict()
        def start_response(status, headers):
            response.status = status
            response.headers = dict(headers)
            response.header_items = headers
        env = {}
        data = data or ''
        if isinstance(data, dict):
            q = urllib.urlencode(data)
        else:
            q = data
        env['wsgi.input'] = StringIO(q)
        env['REQUEST_METHOD'] = 'POST'
        env['PATH_INFO'] = url
        response_body = ''.join(server._wsgi_func(env, start_response))
        return Response(int(response.status.split()[0]), response_body)

    def test_crash(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application
            assert isinstance(server, MyWSGIServer)

            response = self._get(server, '/crash/uuid/' + self.uuid)
            self.assertEqual(response.data, {'hits': [], 'total': 0})
            #cursor = self.conn.cursor()
            #cursor.execute("""
            #INSERT INTO reports (uuid, success, date_processed, url)
            #VALUES (%s, %s, %s, %s)
            #""", (self.uuid, True, '2012-01-16', 'google.com'))
            #self.conn.commit()

            #response = self._get(server, '/crash/uuid/' + self.uuid)
            #self.assertEqual(response.data['total'], 1)
            #self.assertEqual(response.data['hits'][0]['url'], 'google.com')

    def test_crashes(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/crashes/comments/signature/xxx'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self._get(
                server,
                '/crashes/daily/product/Firefox/versions/9.0a1+16.0a1/'
            )
            self.assertEqual(response.data, {'hits': {}})

            response = self._get(
                server,
                '/crashes/frequency/signature/SocketSend/'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self._get(
                server,
                '/crashes/paireduuid/uuid/%s/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self._get(
                server,
                '/crashes/signatures/product/Firefox/version/9.0a1/'
            )
            self.assertEqual(response.data['crashes'], [])

    def test_extensions(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/extensions/uuid/%s/date/'
                '2012-02-29T01:23:45+00:00/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_crashtrends(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/crashtrends/start_date/2012-03-01/end_date/2012-03-15/'
                'product/Firefox/version/13.0a1'
            )
            self.assertEqual(response.data, {'crashtrends': []})

    def test_job(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/job/uuid/%s/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_priorityjobs(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/priorityjobs/uuid/%s/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self._post(
                server,
                '/priorityjobs/uuid/%s/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_products(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/products/versions/Firefox:9.0a1/',
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self._get(
                server,
                '/products/builds/product/Firefox/version/9.0a1/',
            )
            self.assertEqual(response.data, [])

    def test_releases(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/releases/featured/products/Firefox+Fennec/',
            )
            self.assertEqual(response.data, {'hits': {}, 'total': 0})

    def test_signatureurls(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/signatureurls/signature/samplesignature/start_date/'
                '2012-03-01T00:00:00+00:00/end_date/2012-03-31T00:00:00+00:00/'
                'products/Firefox+Fennec/versions/Firefox:4.0.1+Fennec:13.0/'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_search(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/search/crashes/for/libflash.so/in/signature/products/'
                'Firefox/versions/Firefox:4.0.1/from/2011-05-01/to/'
                '2011-05-05/os/Windows/'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_server_status(self):
        breakpad_revision = '1.0'
        socorro_revision = '19.5'

        config_manager = self._setup_config_manager({
            'revisions.breakpad_revision': breakpad_revision,
            'revisions.socorro_revision': socorro_revision,
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self._get(
                server,
                '/server_status/duration/12/'
            )
            self.assertEqual(response.data, {
                'hits': [],
                'total': 0,
                'breakpad_revision': breakpad_revision,
                'socorro_revision': socorro_revision,
            })

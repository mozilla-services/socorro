# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import unittest
import logging
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
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)


DSN = {
  "database.database_host": databaseHost.default,
  "database.database_name": databaseName.default,
  "database.database_user": databaseUserName.default,
  "database.database_password": databasePassword.default
}

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
        if not extra_value_source:
            extra_value_source = {}
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

    def _get(self, server, url):
        response = DotDict()
        def start_response(status, headers):
            response.status = status
            response.headers = dict(headers)
            response.header_items = headers
        env = {}
        env['REQUEST_METHOD'] = 'GET'
        env['PATH_INFO'] = url
        response_body = ''.join(server._wsgi_func(env, start_response))
        return Response(int(response.status.split()[0]), response_body)

    def test_running_the_middleware(self):
        config_manager = self._setup_config_manager({
            'web_server.wsgi_server_class': MyWSGIServer,
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application
            assert isinstance(server, MyWSGIServer)

            response = self._get(server, '/crash/uuid/' + self.uuid)
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO reports (uuid, success, date_processed, url)
            VALUES (%s, %s, %s, %s)
            """, (self.uuid, True, '2012-01-16', 'google.com'))
            self.conn.commit()

            response = self._get(server, '/crash/uuid/' + self.uuid)
            self.assertEqual(response.data['total'], 1)
            self.assertEqual(response.data['hits'][0]['url'], 'google.com')
            print response

from socorro.webapi.servers import WebServerBase
class MyWSGIServer(WebServerBase):

    def run(self):
        return self


class Response(object):

    def __init__(self, status, body):
        self.status = status
        self.body = body

    def __repr__(self):
        return "<Response %s: %r>" % (self.status, self.body)

    __str__ = __repr__

    @property
    def data(self):
        assert self.status == 200
        return json.loads(self.body)

#class AppTester(object):
#    def __init__(self, app):
#        self.app = app

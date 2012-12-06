# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import unittest
import logging
import urllib
from paste.fixture import TestApp
import mock
from nose.plugins.attrib import attr
from mock import patch
from configman import ConfigurationManager
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from socorro.lib import datetimeutil
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


def double_encode(value):
    def q(v):
        return urllib.quote(v).replace('/', '%2F')
    return q(q(value))


class MyWSGIServer(WebServerBase):

    def run(self):
        return self


class HttpError(Exception):
    pass


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

    def create(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100}


class AuxImplementation4(_AuxImplementation):

    def update(self, **kwargs):
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
        assert False
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
        TRUNCATE TABLE bugs CASCADE;
        TRUNCATE TABLE bug_associations CASCADE;
        TRUNCATE TABLE extensions CASCADE;
        TRUNCATE TABLE reports CASCADE;
        TRUNCATE products CASCADE;
        TRUNCATE releases_raw CASCADE;
        TRUNCATE release_channels CASCADE;
        TRUNCATE product_release_channels CASCADE;
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

    def get(self, server, url, request_method='GET', expect_errors=False):
        a = TestApp(server._wsgi_func)
        response = a.get(url, expect_errors=expect_errors)
        return self._respond(response, expect_errors)

    def _respond(self, response, expect_errors):
        if response.status != 200 and not expect_errors:
            raise HttpError('%s - %s' % (response.status, response.body))
        try:
            response.data = json.loads(response.body)
        except ValueError:
            response.data = None
        return response

    def post(self, server, url, data=None, expect_errors=False):
        a = TestApp(server._wsgi_func)
        data = data or ''
        if isinstance(data, dict):
            q = urllib.urlencode(data, True)
        else:
            q = data
        response = a.post(url, q, expect_errors=expect_errors)
        return self._respond(response, expect_errors)

    def put(self, server, url, data=None, expect_errors=False):
        a = TestApp(server._wsgi_func)
        data = data or ''
        if isinstance(data, dict):
            q = urllib.urlencode(data, True)
        else:
            q = data
        response = a.put(url, q, expect_errors=expect_errors)
        return self._respond(response, expect_errors)

    def test_overriding_implementation_class(self):
        config_manager = self._setup_config_manager({
            'implementations.service_overrides': 'Crash: typo'
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            self.assertRaises(
                middleware_app.ImplementationConfigurationError,
                app.main
            )

        default = (middleware_app.MiddlewareApp.required_config
                   .implementations.implementation_list.default)
        previous_as_str = ', '.join('%s: %s' % (x, y) for (x, y) in default)

        config_manager = self._setup_config_manager({
            'implementations.service_overrides': 'Crash: testy',
            'implementations.implementation_list': (
              previous_as_str + ', testy: socorro.uTYPO.middleware'
            )
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            self.assertRaises(ImportError, app.main)

        config_manager = self._setup_config_manager({
            'implementations.service_overrides': 'Crash: testy',
            'implementations.implementation_list': (
                previous_as_str + ', testy: socorro.unittest.middleware'
            )
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(server, '/crash/uuid/' + self.uuid)
            self.assertEqual(response.data, ['all', 'your', 'base'])

    def test_crash(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application
            assert isinstance(server, MyWSGIServer)

            response = self.get(server, '/crash/uuid/' + self.uuid)
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_crashes(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/crashes/comments/signature/xxx/from/2011-05-01/'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self.get(
                server,
                '/crashes/daily/product/Firefox/versions/9.0a1+16.0a1/'
                'from/2011-05-01/to/2011-05-05/'
            )
            self.assertEqual(response.data, {'hits': {}})

            response = self.get(
                server,
                '/crashes/frequency/signature/SocketSend/'
                'from_date/2011-05-01/to_date/2011-05-05/'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self.get(
                server,
                '/crashes/paireduuid/uuid/%s/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self.get(
                server,
                '/crashes/signatures/product/Firefox/version/9.0a1/'
            )
            self.assertEqual(response.data['crashes'], [])

    def test_crashes_comments_with_data(self):
        config_manager = self._setup_config_manager()

        now = datetimeutil.utc_now()
        uuid = "%%s-%s" % now.strftime("%y%m%d")
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO reports
            (id, date_processed, uuid, signature, user_comments)
            VALUES
            (
                1,
                %s,
                %s,
                'sig1',
                'crap'
            ),
            (
                2,
                %s,
                %s,
                'sig2',
                'great'
            );
        """, (now, uuid % "a1", now, uuid % "a2"))
        self.conn.commit()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/crashes/comments/signature/%s/from/%s/to/%s/'
                % ('sig1',
                   #(now - datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
                   now,
                   now)
            )
            self.assertEqual(response.data['total'], 1)
            self.assertEqual(response.data['hits'][0]['user_comments'], 'crap')

    def test_extensions(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/extensions/uuid/%s/date/'
                '2012-02-29T01:23:45+00:00/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            now = datetimeutil.utc_now()
            uuid = "%%s-%s" % now.strftime("%y%m%d")
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO reports
                (id, date_processed, uuid)
                VALUES
                (
                    1,
                    '%s',
                    '%s'
                ),
                (
                    2,
                    '%s',
                    '%s'
                );
            """ % (now, uuid % "a1", now, uuid % "a2"))

            cursor.execute("""
                INSERT INTO extensions VALUES
                (
                    1,
                    '%s',
                    10,
                    'id1',
                    'version1'
                ),
                (
                    1,
                    '%s',
                    11,
                    'id2',
                    'version2'
                ),
                (
                    1,
                    '%s',
                    12,
                    'id3',
                    'version3'
                );
            """ % (now, now, now))
            self.conn.commit()

            response = self.get(
                server,
                '/extensions/uuid/%s/date/'
                '%s/' %
                (uuid % 'a1',
                 now.isoformat())
            )
            self.assertEqual(response.data['total'], 3)

    def test_crashtrends(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
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

            response = self.get(
                server,
                '/job/uuid/%s/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_platforms(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(server, '/platforms/')
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_priorityjobs(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/priorityjobs/uuid/%s/' % self.uuid
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self.post(
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

            response = self.get(
                server,
                '/products/versions/Firefox:9.0a1/',
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_products_builds(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/products/builds/product/Firefox/version/9.0a1/',
            )
            self.assertEqual(response.data, [])

    def test_products_builds_post(self):
        config_manager = self._setup_config_manager()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO products
            (product_name, sort, release_name)
            VALUES
            (
                'Firefox',
                1,
                'firefox'
            ),
            (
                'FennecAndroid',
                2,
                'fennecandroid'
            ),
            (
                'Thunderbird',
                3,
                'thunderbird'
            );
        """)

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1),
            ('Aurora', 2),
            ('Beta', 3),
            ('Release', 4);
        """)

        cursor.execute("""
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            ('Firefox', 'Nightly', 1),
            ('Firefox', 'Aurora', 1),
            ('Firefox', 'Beta', 1),
            ('Firefox', 'Release', 1),
            ('Thunderbird', 'Nightly', 1),
            ('Thunderbird', 'Aurora', 1),
            ('Thunderbird', 'Beta', 1),
            ('Thunderbird', 'Release', 1),
            ('FennecAndroid', 'Nightly', 1),
            ('FennecAndroid', 'Aurora', 1),
            ('FennecAndroid', 'Beta', 1),
            ('FennecAndroid', 'Release', 1);
        """)
        self.conn.commit()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.post(
                server,
                '/products/builds/product/Firefox/',
                {"product": "Firefox",
                 "version": "20.0",
                 "build_id": 20120417012345,
                 "build_type": "Release",
                 "platform": "macosx",
                 "repository": "mozilla-central"
                 }
            )
            self.assertEqual(response.status, 200)
            self.assertEqual(response.body, 'Firefox')

    def test_releases(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/releases/featured/products/Firefox+Fennec/',
            )
            self.assertEqual(response.data, {'hits': {}, 'total': 0})

    def test_releases_featured_put(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.put(
                server,
                '/releases/featured/',
                {'Firefox': '15.0a1,14.0b1'},
            )
            self.assertEqual(response.data, False)

    def test_signatureurls(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
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

            response = self.get(
                server,
                '/search/crashes/for/libflash.so/in/signature/products/'
                'Firefox/versions/Firefox:4.0.1/from/2011-05-01/to/'
                '2011-05-05/os/Windows/'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_search_with_double_encoded_slash(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/signatureurls/signature/%s/'
                'start_date/2012-03-01T00:00:00+00:00/'
                'end_date/2012-03-31T00:00:00+00:00/'
                'products/Firefox+Fennec/versions/Firefox:4.0.1+Fennec:13.0/'
                % double_encode('+samplesignat/ure')
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

            response = self.post(
                server,
                '/bugs/',
                {'signatures': '%2Fsign1%2B'}
            )
            self.assertEqual(response.data, {'hits': [], u'total': 0})

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

            response = self.get(
                server,
                '/server_status/duration/12/'
            )
            self.assertEqual(response.data, {
                'hits': [],
                'total': 0,
                'breakpad_revision': breakpad_revision,
                'socorro_revision': socorro_revision,
            })

    def test_report_list(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/report/list/signature/SocketSend/'
                'from/2011-05-01/to/2011-05-05/'
            )
            self.assertEqual(response.data, {'hits': [], 'total': 0})

    def test_util_versions_info(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/util/versions_info/versions/Firefox:9.0a1+Fennec:7.0/'
            )
            self.assertEqual(response.data, {})

    def test_bugs(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.post(
                server,
                '/bugs/',
                {'signatures': ['sign1', 'sign2']}
            )
            self.assertEqual(response.data, {'hits': [], u'total': 0})

            # because the bugs API is using POST and potentially multiple
            # signatures, it's a good idea to write a full integration test

            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO bugs VALUES
            (1),
            (2),
            (3);
            INSERT INTO bug_associations
            (signature, bug_id)
            VALUES
            (%s, 1),
            (%s, 3),
            (%s, 2);
            """, ('othersig', 'si/gn1', 'sign2+'))
            self.conn.commit()

            response = self.post(
                server,
                '/bugs/',
                {'signatures': ['si%2Fgn1', 'sign2%2B']}
            )
            self.assertEqual(response.data['total'], 2)
            self.assertEqual(response.data['hits'],
                             [{u'id': 3, u'signature': u'si/gn1'},
                              {u'id': 2, u'signature': u'sign2+'}])

            response = self.post(
                server,
                '/bugs/',
                {'signatures': 'othersig'}
            )
            self.assertEqual(response.data['total'], 1)
            self.assertEqual(response.data['hits'],
                             [{u'id': 1, u'signature': u'othersig'}])

            response = self.post(
                server,
                '/bugs/',
                {'signatures': ['never', 'heard', 'of']}
            )
            self.assertEqual(response.data, {'hits': [], u'total': 0})

    def test_signaturesummary(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/signaturesummary/report_type/products/'
                'signature/sig%2Bnature'
                '/start_date/2012-02-29T01:23:45+00:00/end_date/'
                '2012-02-29T01:23:45+00:00/versions/1+2'
            )
            self.assertEqual(response.data, [])

    def test_missing_argument_yield_bad_request(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/crash/xx/yy',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('uuid' in response.body)

            response = self.get(
                server,
                '/crashes/comments/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('signature' in response.body)

            response = self.get(
                server,
                '/crashes/daily/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('product' in response.body)

            response = self.get(
                server,
                '/crashes/daily/product/Firefox/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('versions' in response.body)

            response = self.get(
                server,
                '/crashes/paireduuid/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('uuid' in response.body)

            response = self.get(
                server,
                '/job/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('uuid' in response.body)

            response = self.post(
                server,
                '/bugs/',
                {},
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('signatures' in response.body)

            response = self.get(
                server,
                '/priorityjobs/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('uuid' in response.body)

            response = self.post(
                server,
                '/priorityjobs/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('uuid' in response.body)

            response = self.post(
                server,
                '/products/builds/xxx',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('product' in response.body)

            response = self.get(
                server,
                '/signatureurls/signXXXXe/samplesignature/start_date/'
                '2012-03-01T00:00:00+00:00/end_date/2012-03-31T00:00:00+00:00/'
                'products/Firefox+Fennec/versions/Firefox:4.0.1+Fennec:13.0/',
                expect_errors=True
            )
            self.assertEqual(response.status, 400)
            self.assertTrue('signature' in response.body)

    def test_setting_up_with_lists_overridden(self):

        platforms = [
            {'id': 'amiga',
             'name': 'Amiga'}
        ]
        platforms_json_dump = json.dumps(platforms)

        config_manager = self._setup_config_manager(
            extra_value_source={
                'webapi.channels': 'Foo, Bar',
                'webapi.restricted_channels': 'foo , bar',
                'webapi.platforms': platforms_json_dump
            }
        )

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            self.assertEqual(
                app.config.webapi.channels,
                ['Foo', 'Bar']
            )
            self.assertEqual(
                app.config.webapi.restricted_channels,
                ['foo', 'bar']
            )
            self.assertEqual(
                app.config.webapi.platforms,
                platforms
            )

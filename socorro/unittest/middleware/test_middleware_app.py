# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import mock
import os
import psycopg2
import urllib
import re

from paste.fixture import TestApp, AppError
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from configman import (
    ConfigurationManager,
    environment
)

from socorro.lib.util import DotDict
from socorro.external import (
    MissingArgumentError,
    BadArgumentError,
    ResourceNotFound,
    ResourceUnavailable
)
from socorro.lib import datetimeutil
from socorro.middleware import middleware_app
from socorro.unittest.config.commonconfig import (
    databaseHost,
    databaseName,
    databaseUserName,
    databasePassword
)
from socorro.unittest.testbase import TestCase
from socorro.webapi.servers import CherryPy
from socorro.webapi.servers import WebServerBase


DSN = {
    "database.database_hostname": databaseHost.default,
    "database.database_name": databaseName.default,
    "database.database_username": databaseUserName.default,
    "database.database_password": databasePassword.default
}


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


class AuxImplementationErroring(_AuxImplementation):

    def get(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        raise NameError('crap!')


class AuxImplementationWithUnavailableError(_AuxImplementation):

    def get(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        raise ResourceUnavailable('unavailable')


class AuxImplementationWithNotFoundError(_AuxImplementation):

    def get(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        raise ResourceNotFound('not here')


class AuxImplementationWithMissingArgumentError(_AuxImplementation):

    def get(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        raise MissingArgumentError('missing arg')


class AuxImplementationWithBadArgumentError(_AuxImplementation):

    def get(self, **kwargs):
        self.context.logger.info('Running %s' % self.__class__.__name__)
        raise BadArgumentError('bad arg')


class ImplementationWrapperTestCase(TestCase):

    @mock.patch('logging.info')
    def test_basic_get(self, logging_info):
        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation1
            all_services = {}

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
        eq_(response.status, 200)
        eq_(json.loads(response.body), {'age': 100})

        logging_info.assert_called_with('Running AuxImplementation1')

        response = testapp.get('/xxxjunkxxx', expect_errors=True)
        eq_(response.status, 404)

    @mock.patch('logging.info')
    def test_basic_get_args(self, logging_info):
        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation2
            all_services = {}

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
        eq_(response.status, 200)
        eq_(json.loads(response.body), {'age': 100})
        eq_(response.header_dict['content-length'],
                         str(len(response.body)))
        eq_(response.header_dict['content-type'],
                         'application/json')

        logging_info.assert_called_with('Running AuxImplementation2')

        response = testapp.get('/aux/gender/', expect_errors=True)
        eq_(response.status, 200)
        eq_(json.loads(response.body), {'gender': 0})

        # if the URL allows a certain first argument but the implementation
        # isn't prepared for it, it barfs a 405 at you
        response = testapp.get('/aux/misconfigured/', expect_errors=True)
        eq_(response.status, 405)

    @mock.patch('logging.info')
    def test_basic_post(self, logging_info):
        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation3
            all_services = {}

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
        eq_(response.status, 200)
        eq_(json.loads(response.body), {'age': 100})

        logging_info.assert_called_with('Running AuxImplementation3')

        response = testapp.get('/aux/', expect_errors=True)
        eq_(response.status, 405)

    @mock.patch('logging.info')
    def test_put_with_data(self, logging_info):
        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation4
            all_services = {}

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
        eq_(response.status, 200)
        eq_(json.loads(response.body), {'age': 101})

        logging_info.assert_called_with('Running AuxImplementation4')

    @mock.patch('logging.info')
    def test_basic_get_with_parsed_query_string(self, logging_info):
        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementation5
            all_services = {}

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
        response = testapp.get(
            '/aux/',
            {'foo': 'bar', 'names': ['peter', 'anders']},
        )
        eq_(response.status, 200)
        eq_(json.loads(response.body),
                         {'foo': 'bar',
                          'names': ['peter', 'anders']})

        logging_info.assert_called_with('Running AuxImplementation5')

    @mock.patch('logging.info')
    def test_errors(self, logging_info):
        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class WithNotFound(middleware_app.ImplementationWrapper):
            cls = AuxImplementationWithNotFoundError
            all_services = {}

        class WithUnavailable(middleware_app.ImplementationWrapper):
            cls = AuxImplementationWithUnavailableError
            all_services = {}

        class WithMissingArgument(middleware_app.ImplementationWrapper):
            cls = AuxImplementationWithMissingArgumentError
            all_services = {}

        class WithBadArgument(middleware_app.ImplementationWrapper):
            cls = AuxImplementationWithBadArgumentError
            all_services = {}

        config = DotDict(
            logger=logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            )
        )

        server = CherryPy(config, (
            ('/aux/notfound', WithNotFound),
            ('/aux/unavailable', WithUnavailable),
            ('/aux/missing', WithMissingArgument),
            ('/aux/bad', WithBadArgument),
        ))

        testapp = TestApp(server._wsgi_func)

        # Test a Not Found error
        response = testapp.get('/aux/notfound', expect_errors=True)
        eq_(response.status, 404)
        eq_(
            response.header('content-type'),
            'application/json; charset=UTF-8'
        )
        body = json.loads(response.body)
        eq_(body['error']['message'], 'not here')

        # Test a Timeout error
        response = testapp.get('/aux/unavailable', expect_errors=True)
        eq_(response.status, 408)
        eq_(
            response.header('content-type'),
            'application/json; charset=UTF-8'
        )
        body = json.loads(response.body)
        eq_(body['error']['message'], 'unavailable')

        # Test BadRequest errors
        response = testapp.get('/aux/missing', expect_errors=True)
        eq_(response.status, 400)
        eq_(
            response.header('content-type'),
            'application/json; charset=UTF-8'
        )
        body = json.loads(response.body)
        eq_(
            body['error']['message'],
            "Mandatory parameter(s) 'missing arg' is missing or empty."
        )

        response = testapp.get('/aux/bad', expect_errors=True)
        eq_(response.status, 400)
        eq_(
            response.header('content-type'),
            'application/json; charset=UTF-8'
        )
        body = json.loads(response.body)
        eq_(
            body['error']['message'],
            "Bad value for parameter(s) 'bad arg'"
        )

    @mock.patch('raven.Client')
    @mock.patch('logging.info')
    def test_errors_to_sentry(self, logging_info, raven_client_mocked):
        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class MadeUp(middleware_app.ImplementationWrapper):
            cls = AuxImplementationErroring
            all_services = {}

        FAKE_DSN = 'https://24131e9070324cdf99d@errormill.mozilla.org/XX'

        mock_logging = mock.MagicMock()

        config = DotDict(
            logger=mock_logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            ),
            sentry=DotDict(
                dsn=FAKE_DSN
            )
        )
        server = CherryPy(config, (
            ('/aux/(.*)', MadeUp),
        ))

        def fake_get_ident(exception):
            return '123456789'

        mocked_client = mock.MagicMock()
        mocked_client.get_ident.side_effect = fake_get_ident

        def fake_client(dsn):
            assert dsn == FAKE_DSN
            return mocked_client

        raven_client_mocked.side_effect = fake_client

        testapp = TestApp(server._wsgi_func)
        response = testapp.get('/aux/bla', expect_errors=True)
        eq_(response.status, 500)
        mock_logging.info.has_call([mock.call(
            'Error captured in Sentry. Reference: 123456789'
        )])


class MeasuringImplementationWrapperTestCase(TestCase):

    @mock.patch('logging.info')
    def test_basic_get(self, logging_info):

        config_ = DotDict(
            logger=logging,
            web_server=DotDict(
                ip_address='127.0.0.1',
                port='88888'
            )
        )

        # what the middleware app does is that it creates a class based on
        # another and sets an attribute called `cls`
        class MadeUp(middleware_app.MeasuringImplementationWrapper):
            cls = AuxImplementation1
            all_services = {}
            config = config_

        server = CherryPy(config_, (
            ('/aux/(.*)', MadeUp),
        ))

        testapp = TestApp(server._wsgi_func)
        response = testapp.get('/aux/', params={'add': 1})
        eq_(response.status, 200)
        for call in logging_info.call_args_list:
            # mock calls are funny
            args = call[0]
            arg = args[0]
            if re.findall('measuringmiddleware:[\d\.]+\t/aux/\t\?add=1', arg):
                break
        else:
            raise AssertionError('call never found')


@attr(integration='postgres')
class IntegrationTestMiddlewareApp(TestCase):
    # test the middleware_app except that we won't start the daemon

    def setUp(self):
        super(IntegrationTestMiddlewareApp, self).setUp()
        self.uuid = '06a0c9b5-0381-42ce-855a-ccaaa2120116'
        mock_logging = mock.Mock()
        required_config = middleware_app.MiddlewareApp.get_required_config()
        required_config.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
            [required_config],
            app_name='middleware',
            app_description=__doc__,
            values_source_list=[
                {'logger': mock_logging},
                environment,
                DSN,
            ],
            argv_source=[]
        )
        config = config_manager.get_config()
        self.conn = config.database.database_class(
            config.database
        ).connection()
        assert self.conn.get_transaction_status() == \
            psycopg2.extensions.TRANSACTION_STATUS_IDLE

    def tearDown(self):
        super(IntegrationTestMiddlewareApp, self).tearDown()
        self.conn.cursor().execute("""
            TRUNCATE
                bugs,
                bug_associations,
                reports,
                products,
                releases_raw,
                release_channels,
                product_release_channels,
                os_names,
                graphics_device
            CASCADE
        """)
        self.conn.commit()
        self.conn.close()

    def _insert_release_channels(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1),
            ('Aurora', 2),
            ('Beta', 3),
            ('Release', 4),
            ('ESR', 5);
        """)
        self.conn.commit()

    def _insert_products(self):
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
        self.conn.commit()

    def _setup_config_manager(self, extra_value_source=None):
        if extra_value_source is None:
            extra_value_source = {}
        extra_value_source['web_server.wsgi_server_class'] = MyWSGIServer
        mock_logging = mock.Mock()
        required_config = middleware_app.MiddlewareApp.get_required_config()
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config,
             ],
            app_name='middleware',
            app_description=__doc__,
            values_source_list=[
                {'logger': mock_logging},
                environment,
                DSN,
                extra_value_source
            ],
            argv_source=[]
        )
        return config_manager

    def get(self, server, url, params=None, request_method='GET',
            expect_errors=False):
        a = TestApp(server._wsgi_func)
        response = a.get(url, params=params, expect_errors=expect_errors)
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
            'implementations.service_overrides': 'Backfill: psql, Bugs: typo'
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            assert_raises(
                middleware_app.ImplementationConfigurationError,
                app.main
            )

        imp_list_option = (
            middleware_app.MiddlewareApp.required_config
            .implementations.implementation_list
        )
        default = imp_list_option.from_string_converter(
            imp_list_option.default
        )
        prev_impl_list = ', '.join('%s: %s' % (x, y) for (x, y) in default)
        imp_service_overrides_option = (
            middleware_app.MiddlewareApp.required_config
            .implementations.service_overrides
        )
        default_overrides = imp_service_overrides_option.from_string_converter(
            imp_service_overrides_option.default
        )
        prev_overrides_list = (
            ', '.join('%s: %s' % (x, y) for (x, y) in default_overrides)
        )

        config_manager = self._setup_config_manager({
            'implementations.service_overrides': (
                prev_overrides_list + ', Bugs: testy'
            ),
            'implementations.implementation_list': (
                prev_impl_list + ', testy: socorro.uTYPO.middleware'
            )
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            assert_raises(ImportError, app.main)

        config_manager = self._setup_config_manager({
            'implementations.service_overrides': (
                prev_overrides_list + ', Bugs: testy'
            ),
            'implementations.implementation_list': (
                prev_impl_list + ', testy: socorro.unittest.middleware'
            )
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(server, '/bugs/')
            eq_(response.data, ['all', 'your', 'base'])

    def test_overriding_implementation_class_at_runtime(self):
        imp_list_option = (
            middleware_app.MiddlewareApp.required_config
            .implementations.implementation_list
        )
        default = imp_list_option.from_string_converter(
            imp_list_option.default
        )
        prev_impl_list = ', '.join('%s: %s' % (x, y) for (x, y) in default)

        config_manager = self._setup_config_manager({
            'implementations.implementation_list': (
                prev_impl_list + ', testy: socorro.unittest.middleware'
            )
        })

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            # normal call
            url = '/bugs/'
            response = self.get(server, url, {'signatures': ['abc']})
            eq_(response.data, {'hits': [], 'total': 0})

            # forcing implementation at runtime
            url = '/bugs/'
            response = self.get(server, url, {
                'signatures': ['abc'],
                '_force_api_impl': 'testy',
            })
            eq_(response.data, ['all', 'your', 'base'])

            # forcing unexisting implementation at runtime
            url = '/bugs/'
            assert_raises(
                AppError,
                self.get,
                server, url, {
                    'signatures': ['abc'],
                    '_force_api_impl': 'TYPO',
                }
            )

    def test_crashes(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/crashes/comments/',
                {'signature': 'xxx', 'from': '2011-05-01'}
            )
            eq_(response.data, {'hits': [], 'total': 0})

            response = self.get(
                server,
                '/crashes/daily/',
                {
                    'product': 'Firefox',
                    'versions': ['9.0a1', '16.0a1'],
                    'from': '2011-05-01',
                    'to': '2011-05-05',
                }
            )
            eq_(response.data, {'hits': {}})

            response = self.get(
                server,
                '/crashes/frequency/',
                {
                    'signature': 'SocketSend',
                    'from_date': '2011-05-01',
                    'to_date': '2011-05-05',
                }
            )
            eq_(response.data, {'hits': [], 'total': 0})

            response = self.get(
                server,
                '/crashes/signatures/',
                {'product': 'Firefox', 'version': '9.0a1'}
            )
            eq_(response.data['crashes'], [])

            response = self.get(
                server,
                '/crashes/exploitability/'
            )
            eq_(response.data, {'hits': [], 'total': 0})

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
                '/crashes/comments/',
                {'signature': 'sig1', 'from': now, 'to': now}
            )
            eq_(response.data['total'], 1)
            eq_(response.data['hits'][0]['user_comments'], 'crap')

    def test_field(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/field/',
                {'name': 'something'}
            )
            eq_(response.data, {
                'name': None,
                'transforms': None,
                'product': None
            })

    def test_crashtrends(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/crashtrends/',
                {
                    'start_date': '2012-03-01',
                    'end_date': '2012-03-15',
                    'product': 'Firefox',
                    'version': '13.0a1',
                }
            )
            eq_(response.data, {'crashtrends': []})

    def test_platforms(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(server, '/platforms/')
            eq_(response.data, {'hits': [], 'total': 0})

    def test_priorityjobs(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/priorityjobs/',
                {'uuid': self.uuid},
                expect_errors=True
            )
            eq_(response.status, 500)

            response = self.post(
                server,
                '/priorityjobs/',
                {'uuid': self.uuid}
            )
            ok_(response.data)

    def test_products(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/products/',
                {'versions': 'Firefox:9.0a1'}
            )
            eq_(response.data, {'hits': [], 'total': 0})

    def test_releases_channels(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/releases/channels/',
                {'products': ['Firefox', 'Fennec']}
            )
            eq_(response.data, {})

    def test_releases_featured(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/releases/featured/',
                {'products': ['Firefox', 'Fennec']}
            )
            eq_(response.data, {'hits': {}, 'total': 0})

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
            eq_(response.data, False)

    def test_signatureurls(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/signatureurls/',
                {
                    'signature': 'samplesignature',
                    'start_date': '2012-03-01T00:00:00+00:00',
                    'end_date': '2012-03-31T00:00:00+00:00',
                    'products': ['Firefox', 'Fennec'],
                    'versions': ['Firefox:4.0.1', 'Fennec:13.0'],
                }
            )
            eq_(response.data, {'hits': [], 'total': 0})

    def test_server_status(self):
        breakpad_revision = '1.0'
        socorro_revision = '19.5'

        from socorro.external.postgresql import server_status

        # Create fake revision files
        self.basedir = os.path.dirname(server_status.__file__)
        open(os.path.join(
            self.basedir, 'socorro_revision.txt'
        ), 'w').write(socorro_revision)
        open(os.path.join(
            self.basedir, 'breakpad_revision.txt'
        ), 'w').write(breakpad_revision)

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/server_status/',
                {'duration': 12}
            )
            eq_(response.data, {
                'hits': [],
                'total': 0,
                'breakpad_revision': breakpad_revision,
                'socorro_revision': socorro_revision,
                'schema_revision': 'Unknown',
            })

        # Delete fake revision files
        os.remove(os.path.join(self.basedir, 'socorro_revision.txt'))
        os.remove(os.path.join(self.basedir, 'breakpad_revision.txt'))

    def test_report_list(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/report/list/',
                {
                    'signature': 'SocketSend',
                    'from': '2011-05-01',
                    'to': '2011-05-05',
                }
            )
            eq_(response.data, {'hits': [], 'total': 0})

    def test_util_versions_info(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/util/versions_info/',
                {'versions': ['Firefox:9.0a1', 'Fennec:7.0']}
            )
            eq_(response.data, {})

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
            eq_(response.data, {'hits': [], u'total': 0})

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
                {'signatures': ['si/gn1', 'sign2+']}
            )
            hits = sorted(response.data['hits'], key=lambda k: k['id'])
            eq_(response.data['total'], 2)
            eq_(hits,
                             [{u'id': 2, u'signature': u'sign2+'},
                              {u'id': 3, u'signature': u'si/gn1'}])

            response = self.post(
                server,
                '/bugs/',
                {'signatures': 'othersig'}
            )
            eq_(response.data['total'], 1)
            eq_(response.data['hits'],
                             [{u'id': 1, u'signature': u'othersig'}])

            response = self.post(
                server,
                '/bugs/',
                {'signatures': ['never', 'heard', 'of']}
            )
            eq_(response.data, {'hits': [], u'total': 0})

    def test_signaturesummary(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/signaturesummary/',
                {
                    'report_type': 'products',
                    'signature': 'sig+nature',
                    'start_date': '2012-02-29T01:23:45+00:00',
                    'end_date': '2012-02-29T01:23:45+00:00',
                    'versions': [1, 2],
                }
            )
            eq_(response.data, [])

    def test_backfill(self):
        config_manager = self._setup_config_manager()

        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO raw_adi
        (adi_count, date, product_name, product_os_platform,
        product_os_version, product_version, build, update_channel,
        product_guid, received_at)
        VALUES
        (10, '2013-08-22', 'NightTrain', 'Linux', 'Linux', '3.0a2',
        '20130821000016', 'aurora', '{nighttrain@example.com}',
        '2013-08-21')
        """)
        self.conn.commit()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/backfill/',
                {'backfill_type': 'adu', 'update_day': '2013-08-22'}
            )
            eq_(response.status, 200)

    def test_missing_argument_yield_bad_request(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/crash_data/',
                {'xx': 'yy'},
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('uuid' in response.body)

            response = self.get(
                server,
                '/crashes/comments/',
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('signature' in response.body)

            response = self.get(
                server,
                '/crashes/daily/',
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('product' in response.body)

            response = self.get(
                server,
                '/crashes/daily/',
                {'product': 'Firefox'},
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('versions' in response.body)

            response = self.post(
                server,
                '/bugs/',
                {},
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('signatures' in response.body)

            response = self.get(
                server,
                '/priorityjobs/',
                expect_errors=True
            )
            eq_(response.status, 500)

            response = self.post(
                server,
                '/priorityjobs/',
                expect_errors=True
            )
            eq_(response.status, 400)

            response = self.post(
                server,
                '/priorityjobs/',
                {'uuid': 1234689},
            )
            eq_(response.status, 200)

            response = self.get(
                server,
                '/signatureurls/',
                {
                    'signXXXXe': 'samplesignature',
                    'start_date': '2012-03-01T00:00:00+00:00',
                    'end_date': '2012-03-31T00:00:00+00:00',
                    'products': ['Firefox', 'Fennec'],
                    'versions': ['Firefox:4.0.1', 'Fennec:13.0'],
                },
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('signature' in response.body)

    def test_setting_up_with_lists_overridden(self):

        platforms = [
            {'id': 'amiga',
             'name': 'Amiga'}
        ]
        platforms_json_dump = json.dumps(platforms)

        config_manager = self._setup_config_manager(
            extra_value_source={
                'webapi.non_release_channels': 'Foo, Bar',
                'webapi.restricted_channels': 'foo , bar',
                'webapi.platforms': platforms_json_dump
            }
        )

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            eq_(
                app.config.webapi.non_release_channels,
                ['Foo', 'Bar']
            )
            eq_(
                app.config.webapi.restricted_channels,
                ['foo', 'bar']
            )
            eq_(
                app.config.webapi.platforms,
                platforms
            )

    def test_laglog(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/laglog/',
            )
            eq_(response.status, 200)
            eq_(json.loads(response.body), {'replicas': []})

    def test_graphics_devices(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/graphics_devices/',
                expect_errors=True
            )
            eq_(response.status, 400)

            response = self.get(
                server,
                '/graphics_devices/',
                {'vendor_hex': '0x1002', 'adapter_hex': '0x0166'},
            )
            eq_(response.status, 200)
            eq_(
                json.loads(response.body),
                {'hits': [], 'total': 0}
            )

    def test_graphics_devices_post_payload(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application
            one = {
                'vendor_hex': '0x1002',
                'adapter_hex': '0x0166',
                'vendor_name': 'Vendor',
                'adapter_name': 'Adapter'
            }
            payload = [one]
            response = self.post(
                server,
                '/graphics_devices/',
                # this must be a string or paste will
                # try to urlencode it
                json.dumps(payload)
            )
            eq_(response.status, 200)
            eq_(
                json.loads(response.body),
                True
            )

            # try to post some rubbish
            response = self.post(
                server,
                '/graphics_devices/',
                json.dumps([{'rubbish': 'stuff'}])
            )
            eq_(response.status, 200)
            eq_(
                json.loads(response.body),
                False
            )

    def test_adu_by_signature(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/crashes/adu_by_signature/',
                {
                    'start_date': '2012-03-01',
                    'end_date': '2012-03-15',
                    'signature': 'FakeSignature1',
                    'channel': 'aurora',
                }
            )
            eq_(response.data, {'hits': [], 'total': 0})

    def test_post_product(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.post(
                server,
                '/products/',
                {
                    'product': 'KillerApp',
                    'version': '1.0',
                }
            )
            eq_(response.data, True)

            # do it a second time
            response = self.post(
                server,
                '/products/',
                {
                    'product': 'KillerApp',
                    'version': '1.0',
                }
            )
            eq_(response.data, False)

    def test_post_bad_product(self):
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.post(
                server,
                '/products/',
                {
                    'product': 'Spaces not allowed',
                    'version': '',
                }
            )
            eq_(response.data, False)

    def test_create_release(self):
        self._insert_release_channels()
        self._insert_products()
        config_manager = self._setup_config_manager()

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            now = datetimeutil.utc_now()
            response = self.post(
                server,
                '/releases/release/',
                {
                    'product': 'Firefox',
                    'version': '1.0',
                    'update_channel': 'beta',
                    'build_id': now.strftime('%Y%m%d%H%M'),
                    'platform': 'Windows',
                    'beta_number': '1',
                    'release_channel': 'Beta',
                    'throttle': '1'
                }
            )
            eq_(response.data, True)

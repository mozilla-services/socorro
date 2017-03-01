# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import mock
import psycopg2
import urllib
import re

from paste.fixture import TestApp, AppError
from nose.tools import eq_, ok_, assert_raises

from configman import (
    ConfigurationManager,
    environment
)

from socorro.lib.util import DotDict
from socorro.lib import (
    MissingArgumentError,
    BadArgumentError,
    ResourceNotFound,
    ResourceUnavailable
)
from socorro.lib import datetimeutil
from socorro.middleware import middleware_app
from socorro.unittest.testbase import TestCase
from socorro.webapi.servers import CherryPy
from socorro.webapi.servers import WebServerBase


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

    def _setup_config_manager(
        self,
        extra_value_source=None,
        services_list=None
    ):
        if extra_value_source is None:
            extra_value_source = {}
        extra_value_source['web_server.wsgi_server_class'] = MyWSGIServer
        mock_logging = mock.Mock()
        if services_list:
            middleware_app.MiddlewareApp.SERVICES_LIST = services_list
        else:
            # the global list
            middleware_app.MiddlewareApp.SERVICES_LIST = middleware_app.SERVICES_LIST
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
            'implementations.implementation_list': (
                'psql:socorro.unittest.middleware'
            ),
            'implementations.service_overrides': (
                'Fooing: typo'
            )
        },
            services_list=(
                ('/fooing/', 'things.Fooing'),
            )
        )

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            assert_raises(
                middleware_app.ImplementationConfigurationError,
                app.main
            )

        prev_impl_list = 'psql: does.not.exist'
        prev_overrides_list = 'Other: stuff'

        config_manager = self._setup_config_manager({
            'implementations.service_overrides': (
                prev_overrides_list + ', Doesnt: matter'
            ),
            'implementations.implementation_list': (
                prev_impl_list + ', testy: socorro.uTYPO.middleware'
            )
        },
            services_list=(
                ('/fooing/', 'fooing.Fooing'),
            )
        )

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            assert_raises(ImportError, app.main)

        config_manager = self._setup_config_manager({
            'implementations.service_overrides': (
                prev_overrides_list + ', Fooing: testy'
            ),
            'implementations.implementation_list': (
                prev_impl_list + ', testy: socorro.unittest.middleware'
            )
        },
            services_list=(
                ('/fooing/', 'fooing.Fooing'),
            )
        )

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(server, '/fooing/')
            eq_(response.data, ['all', 'your', 'base'])

    def test_overriding_implementation_class_at_runtime(self):
        config_manager = self._setup_config_manager({
            'implementations.implementation_list': (
                'psql: socorro.unittest.middleware, '
                'testy: socorro.unittest.middleware.somesubmodule'
            )
        },
            services_list=(
                ('/fooing/', 'fooing.Fooing'),
            )
        )

        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            # normal call
            url = '/fooing/'
            response = self.get(server, url, {'signatures': ['abc']})
            eq_(response.data, ['all', 'your', 'base'])

            # forcing implementation at runtime
            url = '/fooing/'
            response = self.get(server, url, {
                'signatures': ['abc'],
                '_force_api_impl': 'testy',
            })
            eq_(response.data, ['one', 'two', 'three'])

            # forcing unexisting implementation at runtime
            url = '/fooing/'
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
                '/crashes/daily/',
                {
                    'product': 'Firefox',
                    'versions': ['9.0a1', '16.0a1'],
                    'from': '2011-05-01',
                    'to': '2011-05-05',
                }
            )
            eq_(response.data, {'hits': {}})

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

    def test_healthcheck(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            app = middleware_app.MiddlewareApp(config)
            app.main()
            server = middleware_app.application

            response = self.get(
                server,
                '/healthcheck/',
            )
            eq_(response.data, True)

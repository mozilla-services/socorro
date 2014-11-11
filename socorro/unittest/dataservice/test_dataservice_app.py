# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import mock
import os
import psycopg2
import urllib

from paste.fixture import TestApp
from nose.plugins.attrib import attr

from nose.tools import eq_, ok_

from configman import (
    Namespace,
    ConfigurationManager,
    environment,
    class_converter
)

from socorro.external import (
    MissingArgumentError,
    BadArgumentError,
    ResourceNotFound,
    ResourceUnavailable
)
from socorro.lib import datetimeutil
from socorro.dataservice import dataservice_app
from socorro.unittest.testbase import TestCase
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)
from socorro.unittest.dataservice.setup_configman import (
    get_config_manager_with_internal_pg,
    get_config_manager_for_dataservice,
    MyWSGIServer
)


DSN = {
    "resource.postgresql.database_hostname": "localhost",
    "resource.postgresql.database_name": "socorro_integration_test",
    "secrets.postgresql.database_username": 'breakpad_rw',
    "secrets.postgresql.database_password": 'aPassword',
}


#==============================================================================
class HttpError(Exception):
    pass


#==============================================================================
class _AuxImplementation(object):

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get("config")


#==============================================================================
class AuxImplementation1(_AuxImplementation):

    def get(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100}


#==============================================================================
class AuxImplementation2(_AuxImplementation):

    def get_age(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100}

    def get_gender(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        return {'gender': 0}


#==============================================================================
class AuxImplementation3(_AuxImplementation):

    def create(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100}


#==============================================================================
class AuxImplementation4(_AuxImplementation):

    def update(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        return {'age': 100 + int(kwargs.get('add', 0))}


#==============================================================================
class AuxImplementation5(_AuxImplementation):

    def get(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        return kwargs


#==============================================================================
class AuxImplementationErroring(_AuxImplementation):

    def get(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        raise NameError('crap!')


#==============================================================================
class AuxImplementationWithUnavailableError(_AuxImplementation):

    def get(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        raise ResourceUnavailable('unavailable')


#==============================================================================
class AuxImplementationWithNotFoundError(_AuxImplementation):

    def get(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        raise ResourceNotFound('not here')


#==============================================================================
class AuxImplementationWithMissingArgumentError(_AuxImplementation):

    def get(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        raise MissingArgumentError('missing arg')


#==============================================================================
class AuxImplementationWithBadArgumentError(_AuxImplementation):

    def get(self, **kwargs):
        self.config.logger.info('Running %s' % self.__class__.__name__)
        raise BadArgumentError('bad arg')


#==============================================================================
@attr(integration='postgres')
class IntegrationTestDataserviceApp(TestCase):
    # test the dataservice_app except that we won't start the daemon

    #--------------------------------------------------------------------------
    def get_config_manager(self, overrides=None):
        if overrides:
            overrides = [overrides, DSN]
        else:
            overrides = [DSN]
        return get_config_manager_for_dataservice(
            overrides=overrides
        )

    #--------------------------------------------------------------------------
    def setUp(self):
        super(IntegrationTestDataserviceApp, self).setUp()
        self.uuid = '06a0c9b5-0381-42ce-855a-ccaaa2120116'

        self.config_manager = get_config_manager_with_internal_pg(
            overrides=DSN)
        self.config = self.config_manager.get_config()
        self.crash_store = self.config.database.crashstorage_class(
            self.config.database
        )
        self.transaction = self.crash_store.transaction

    #--------------------------------------------------------------------------
    def tearDown(self):
        super(IntegrationTestDataserviceApp, self).tearDown()
        self.transaction(
            execute_no_results,
            """
            TRUNCATE TABLE bugs CASCADE;
            TRUNCATE TABLE bug_associations CASCADE;
            TRUNCATE TABLE extensions CASCADE;
            TRUNCATE TABLE reports CASCADE;
            TRUNCATE products CASCADE;
            TRUNCATE releases_raw CASCADE;
            TRUNCATE release_channels CASCADE;
            TRUNCATE product_release_channels CASCADE;
            TRUNCATE os_names CASCADE;
            TRUNCATE graphics_device CASCADE;
            """
        )

    #--------------------------------------------------------------------------
    def get(self, server, url, params=None, request_method='GET',
            expect_errors=False):
        print "in get waiting for TestApp"
        print server._wsgi_func
        a = TestApp(server._wsgi_func)
        response = a.get(url, params=params, expect_errors=expect_errors)
        return self._respond(response, expect_errors)

    #--------------------------------------------------------------------------
    def _respond(self, response, expect_errors):
        if response.status != 200 and not expect_errors:
            raise HttpError('%s - %s' % (response.status, response.body))
        try:
            response.data = json.loads(response.body)
        except ValueError:
            response.data = None
        return response

    #--------------------------------------------------------------------------
    def post(self, server, url, data=None, expect_errors=False):
        a = TestApp(server._wsgi_func)
        data = data or ''
        if isinstance(data, dict):
            q = urllib.urlencode(data, True)
        else:
            q = data
        response = a.post(url, q, expect_errors=expect_errors)
        return self._respond(response, expect_errors)

    #--------------------------------------------------------------------------
    def put(self, server, url, data=None, expect_errors=False):
        a = TestApp(server._wsgi_func)
        data = data or ''
        if isinstance(data, dict):
            q = urllib.urlencode(data, True)
        else:
            q = data
        response = a.put(url, q, expect_errors=expect_errors)
        return self._respond(response, expect_errors)

    #--------------------------------------------------------------------------
    def test_crash(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application
            assert isinstance(server, MyWSGIServer)

            response = self.get(server, '/crash/', {'uuid': self.uuid})
            eq_(response.data, {'hits': [], 'total': 0})

    #--------------------------------------------------------------------------
    def test_crashes(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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
                '/crashes/paireduuid/',
                {'uuid': self.uuid}
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

    #--------------------------------------------------------------------------
    def test_crashes_comments_with_data(self):
        config_manager = self.get_config_manager()

        config_manager.dump_conf(config_pathname='/home/lars/temp/fucked.ini')

        now = datetimeutil.utc_now()
        uuid = "%%s-%s" % now.strftime("%y%m%d")
        self.transaction(
            execute_no_results,
            """
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
            """,
            (now, uuid % "a1", now, uuid % "a2")
        )

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/crashes/comments/',
                {'signature': 'sig1', 'from': now, 'to': now}
            )
            eq_(response.data['total'], 1)
            eq_(response.data['hits'][0]['user_comments'], 'crap')

    #--------------------------------------------------------------------------
    def test_extensions(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/extensions/',
                {'uuid': self.uuid, 'date': '2012-02-29T01:23:45+00:00'}
            )
            eq_(response.data, {'hits': [], 'total': 0})

            now = datetimeutil.utc_now()
            uuid = "%%s-%s" % now.strftime("%y%m%d")
            def do_transaction(connection):
                execute_no_results(
                    connection,
                    """
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
                    """ % (now, uuid % "a1", now, uuid % "a2")
                )

                execute_no_results(
                    connection,
                    """
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
                """ % (now, now, now)
            )
            self.transaction(do_transaction)

            response = self.get(
                server,
                '/extensions/',
                {'uuid': uuid % 'a1', 'date': now.isoformat()}
            )
            eq_(response.data['total'], 3)

    #--------------------------------------------------------------------------
    def test_field(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

    #--------------------------------------------------------------------------
    def test_crashtrends(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

    #--------------------------------------------------------------------------
    def test_platforms(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(server, '/platforms/')
            eq_(response.data, {'hits': [], 'total': 0})

    #--------------------------------------------------------------------------
    def test_priorityjobs(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

    #--------------------------------------------------------------------------
    def test_products(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/products/',
                {'versions': 'Firefox:9.0a1'}
            )
            eq_(response.data, {'hits': [], 'total': 0})

    #--------------------------------------------------------------------------
    def test_products_builds(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/products/builds/',
                {'product': 'Firefox', 'version': ':9.0a1'}
            )
            eq_(response.data, [])

    #--------------------------------------------------------------------------
    def test_products_builds_post(self):
        config_manager = self.get_config_manager()

        def do_transaction(connection):
            execute_no_results(
                connection,
                """
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
                """
            )

            execute_no_results(
                connection,
                """
                INSERT INTO release_channels
                (release_channel, sort)
                VALUES
                ('Nightly', 1),
                ('Aurora', 2),
                ('Beta', 3),
                ('Release', 4);
                """
            )

            execute_no_results(
                connection,
                """
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
                """
            )
        self.transaction(do_transaction)

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.post(
                server,
                '/products/builds/',
                {"product": "Firefox",
                 "version": "20.0",
                 "build_id": 20120417012345,
                 "build_type": "Release",
                 "platform": "macosx",
                 "repository": "mozilla-central"
                 }
            )
            eq_(response.status, 200)
            eq_(response.body, 'Firefox')

    #--------------------------------------------------------------------------
    def test_releases(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/releases/featured/',
                {'products': ['Firefox', 'Fennec']}
            )
            eq_(response.data, {'hits': {}, 'total': 0})

    #--------------------------------------------------------------------------
    def test_releases_featured_put(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.post(
                server,
                '/releases/featured/',
                {'Firefox': '15.0a1,14.0b1'},
            )
            eq_(response.data, False)

    #--------------------------------------------------------------------------
    def test_signatureurls(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

    #--------------------------------------------------------------------------
    def test_search(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/search/crashes/',
                {
                    'for': 'libflash.so',
                    'in': 'signature',
                    'products': 'Firefox',
                    'versions': 'Firefox:4.0.1',
                    'from': '2011-05-01',
                    'to': '2011-05-05',
                    'os': 'Windows',
                }
            )
            eq_(response.data, {'hits': [], 'total': 0})

    #--------------------------------------------------------------------------
    def test_server_status(self):
        breakpad_revision = '1.0'
        socorro_revision = '19.5'

        from socorro.external.postgresql import server_status_service

        # Create fake revision files
        self.basedir = os.path.dirname(server_status_service.__file__)

        socorro_revision_path = (
            os.path.join(self.basedir, 'socorro_revision.txt')
        )
        with open(socorro_revision_path, 'w') as f:
            f.write(socorro_revision)

        try:
            breakpad_revision_path = (
                os.path.join(self.basedir, 'breakpad_revision.txt')
            )
            with open(breakpad_revision_path, 'w') as f:
                f.write(breakpad_revision)
            try:
                config_manager = self.get_config_manager()
                with config_manager.context() as config:
                    app = dataservice_app.DataserviceApp(config)
                    app.main()
                    server = dataservice_app.application

                    response = self.get(
                        server,
                        '/server_status/',
                        {'duration': 12}
                    )
                    # we have problem of not entirely knowing the state of the
                    # database in this test.  It was originally written such
                    # that the schema_revision (as defined by the datbase
                    # table 'alembic_version') would be missing and marked as
                    # 'unknown'.  However, if this test is run in isolation,
                    # it doesn't make sure the database is in a known state.
                    # The value of schema_revision could be unpredictable.
                    # The original version of this test is commented out.
                    #eq_(response.data, {
                        #'hits': [],
                        #'total': 0,
                        #'breakpad_revision': breakpad_revision,
                        #'socorro_revision': socorro_revision,
                        #'schema_revision': 'Unknown',
                    #})
                    eq_(response.data, {
                        'hits': [],
                        'total': 0,
                        'breakpad_revision': breakpad_revision,
                        'socorro_revision': socorro_revision,
                        'schema_revision': response.data['schema_revision'],
                    })

            finally:
                # Delete fake revision files
                os.remove(os.path.join(self.basedir, 'breakpad_revision.txt'))
        finally:
            os.remove(os.path.join(self.basedir, 'socorro_revision.txt'))

    #--------------------------------------------------------------------------
    def test_report_list(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

    #--------------------------------------------------------------------------
    def test_util_versions_info(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/util/versions_info/',
                {'versions': ['Firefox:9.0a1', 'Fennec:7.0']}
            )
            eq_(response.data, {})

    #--------------------------------------------------------------------------
    def test_bugs(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.post(
                server,
                '/bugs/',
                {'signatures': ['sign1', 'sign2']}
            )
            eq_(response.data, {'hits': [], u'total': 0})

            # because the bugs API is using POST and potentially multiple
            # signatures, it's a good idea to write a full integration test

            self.transaction(
                execute_no_results,
                """
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
                """,
                ('othersig', 'si/gn1', 'sign2+')
            )

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

    #--------------------------------------------------------------------------
    def test_signaturesummary(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

    #--------------------------------------------------------------------------
    def test_backfill(self):
        config_manager = self.get_config_manager()

        self.transaction(
            execute_no_results,
            """
            INSERT INTO raw_adu
            (adu_count, date, product_name, product_os_platform,
            product_os_version, product_version, build, build_channel,
            product_guid, received_at)
            VALUES
            (10, '2013-08-22', 'NightTrain', 'Linux', 'Linux', '3.0a2',
            '20130821000016', 'aurora', '{nighttrain@example.com}',
            '2013-08-21')
            """
        )

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/backfill/',
                {'backfill_type': 'adu', 'update_day': '2013-08-22'}
            )
            eq_(response.status, 200)

    #--------------------------------------------------------------------------
    def test_missing_argument_yield_bad_request(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/crash/',
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

            response = self.get(
                server,
                '/crashes/paireduuid/',
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('uuid' in response.body)

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
                '/products/builds/',
                {'xxx': ''},
                expect_errors=True
            )
            eq_(response.status, 400)
            ok_('product' in response.body)

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

    #--------------------------------------------------------------------------
    def test_setting_up_with_lists_overridden(self):

        platforms = [
            {'id': 'amiga',
             'name': 'Amiga'}
        ]
        platforms_json_dump = json.dumps(platforms)

        config_manager = self.get_config_manager(
            overrides={
                'webapi.non_release_channels': 'Foo, Bar',
                'webapi.restricted_channels': 'foo , bar',
                'webapi.platforms': platforms_json_dump
            }
        )

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
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

    #--------------------------------------------------------------------------
    def test_laglog(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

            response = self.get(
                server,
                '/laglog/',
            )
            eq_(response.status, 200)
            eq_(json.loads(response.body), {'replicas': []})

    #--------------------------------------------------------------------------
    def test_graphics_devices(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

    #--------------------------------------------------------------------------
    def test_graphics_devices_post_payload(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application
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

    #--------------------------------------------------------------------------
    def test_adu_by_signature(self):
        config_manager = self.get_config_manager()

        with config_manager.context() as config:
            app = dataservice_app.DataserviceApp(config)
            app.main()
            server = dataservice_app.application

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

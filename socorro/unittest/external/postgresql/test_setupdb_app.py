# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
from psycopg2 import ProgrammingError
import psycopg2

from .unittestbase import PostgreSQLTestCase
from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest
from socorro.external.postgresql import setupdb_app
from configman import ConfigurationManager


@attr(integration='postgres')
class IntegrationTestSetupDB(PostgreSQLTestCase):

    def _get_connection(self, database_name, DSN):
        if not database_name:
            database_name = DSN['database_name']
        dsn = (
            'host=%(database_hostname)s '
            'dbname=%(database_name)s '
            'user=%(database_username)s '
            'password=%(database_password)s' %
            dict(DSN, database_name=database_name)
        )
        return psycopg2.connect(dsn)

    def _drop_database(self):
        conn = self._get_connection('template1', self.super_dsn)
        cursor = conn.cursor()
        # double-check there is a crontabber_state row
        conn.set_isolation_level(0)
        try:
            cursor.execute('DROP DATABASE %s' % self.dsn['database_name'])
        except ProgrammingError:
            pass
        conn.set_isolation_level(1)
        conn.close()

    def setUp(self):
        super(IntegrationTestSetupDB, self).setUp()

        config_manager = self._setup_config_manager({'dropdb': True})
        with config_manager.context() as config:
            self.dsn = {
                "database_hostname": config.database_hostname,
                "database_name": config.database_name,
                "database_username": config.database_username,
                "database_password": config.database_password
            }

            self.super_dsn = {
                "database_hostname": config.database_hostname,
                "database_name": config.database_name,
                "database_username": config.database_superusername,
                "database_password": config.database_superuserpassword
            }

        self._drop_database()

    def _setup_config_manager(self, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}
        mock_logging = mock.Mock()

        required_config = setupdb_app.SocorroDB.required_config
        required_config.add_option('logger', default=mock_logging)

        # We manually set the database_name to something deliberately
        # different from all other integration tests. This way we can have
        # tight control over its creation and destruction without affecting
        # the other tests.
        required_config.database_name = 'soccoro_integration_test_setupdb_only'

        required_config.database_hostname = self.config.database_hostname

        config_manager = ConfigurationManager(
            [required_config,
             ],
            app_name='setupdb',
            app_description=__doc__,
            values_source_list=[{
                'logger': mock_logging,
            }, extra_value_source]
        )
        return config_manager

    def test_run_setupdb_app(self):
        # this really touches the DB and causes problems if you do not
        # have a superuser name/pass that match the default. Disable
        # this until there's a way to override. Not sure if this is
        # worth testing here anyway (we have other setupdb_app tests)
        raise SkipTest
        config_manager = self._setup_config_manager({'dropdb': True})
        with config_manager.context() as config:
            db = setupdb_app.SocorroDB(config)
            db.main()

            # we can't know exactly because it would be tedious to have to
            # expect an exact amount of created tables and views so we just
            # expect it to be a relatively large number

            conn = self._get_connection(None, self.dsn)
            cursor = conn.cursor()
            cursor.execute("""
            select count(relname) from pg_class
            where relkind='r' and relname NOT ilike 'pg_%'
            """)
            count_tables, = cursor.fetchone()
            self.assertTrue(count_tables > 50)

            cursor.execute("""
            select count(relname) from pg_class
            where relkind='v' and relname NOT ilike 'pg_%'
            """)
            count_views, = cursor.fetchone()
            self.assertTrue(count_views > 50)

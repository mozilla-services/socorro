# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from psycopg2 import ProgrammingError, OperationalError
from nose.plugins.attrib import attr

import socorro.database.database as db
from socorro.external.postgresql import setupdb_app

from .unittestbase import PostgreSQLTestCase


@attr(integration='postgres')
class IntegrationTestSetupDB(PostgreSQLTestCase):

    PLAYGROUND_DATABASE_NAME = 'socorro_integration_test_setupdb_only'

    required_config = setupdb_app.SocorroDB.required_config
    required_config.add_option(
        name='read_write_users',
        default='postgres, breakpad_rw, monitor',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='read_only_users',
        default='breakpad_ro, breakpad, analyst',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='fakedata',
        default=False,
        doc='Whether or not to fill the data with synthetic test data',
    )

    required_config.add_option(
        name='fakedata_days',
        default=7,
        doc='How many days of synthetic test data to generate'
    )

    required_config.add_option(
        name='alembic_config',
        default=os.path.abspath('config/alembic.ini'),
        doc='Path to alembic configuration file'
    )

    required_config.add_option(
        name='default_password',
        default='aPassword',
        doc='Default password for roles created by setupdb_app.py',
    )

    def _make_connection(self):
        return db.Database(self.config).connection()

    def _drop_database(self):
        # We connect using the integration test db...
        assert self.config.database_name != self.PLAYGROUND_DATABASE_NAME
        connection = self._make_connection()
        cursor = connection.cursor()
        connection.set_isolation_level(0)
        # ...but try to delete the playground db.
        cursor.execute('DROP DATABASE %s' % self.PLAYGROUND_DATABASE_NAME)
        cursor.close()
        connection.set_isolation_level(1)
        connection.close()

    def setUp(self):
        super(IntegrationTestSetupDB, self).setUp()
        self.original_database_name = self.config.database_name
        try:
            self._drop_database()
        except ProgrammingError as exc:
            print "Failed to drop database on setUp()"
            print str(exc)

    def tearDown(self):
        self.config.database_name = self.original_database_name
        try:
            self._drop_database()
        except OperationalError as exc:
            print "Failed to drop the database on tearDown"
            print str(exc)
        super(IntegrationTestSetupDB, self).tearDown()

    def test_run_setupdb_app(self):
        self.config.database_name = self.PLAYGROUND_DATABASE_NAME
        self.config.dropdb = True
        db = setupdb_app.SocorroDB(self.config)
        assert db.main() == 0  # a successful exit

        # we can't know exactly because it would be tedious to have to
        # expect an exact amount of created tables and views so we just
        # expect it to be a relatively large number

        conn = self._make_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(relname) FROM pg_class
            WHERE relkind='r' AND relname NOT ILIKE 'pg_%'
        """)
        count_tables, = cursor.fetchone()
        self.assertTrue(count_tables > 50)

        cursor.execute("""
            SELECT COUNT(relname) FROM pg_class
            WHERE relkind='v' AND relname NOT ILIKE 'pg_%'
        """)
        count_views, = cursor.fetchone()
        self.assertTrue(count_views > 50)
        cursor.close()
        conn.close()

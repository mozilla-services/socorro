# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_, assert_raises

from socorrolib.lib import DatabaseError
from socorro.external.postgresql.base import PostgreSQLBase

from .unittestbase import PostgreSQLTestCase


#==============================================================================
class IntegrationTestBase(PostgreSQLTestCase):

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestBase, self).setUp()

        cursor = self.connection.cursor()

        cursor.execute("""
            INSERT INTO reports
            (id, date_processed, uuid, url, email, success, addons_checked)
            VALUES
            (
                1,
                '2000-01-01T01:01:01+00:00',
                '1',
                'http://mywebsite.com',
                'test@something.com',
                TRUE,
                TRUE
            ),
            (
                2,
                '2000-01-01T01:01:01+00:00',
                '2',
                'http://myotherwebsite.com',
                'admin@example.com',
                NULL,
                FALSE
            );
        """)

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE reports CASCADE;
        """)
        self.connection.commit()
        super(IntegrationTestBase, self).tearDown()

    #--------------------------------------------------------------------------
    def test_utc(self):
        base = PostgreSQLBase(config=self.config)

        # Verify that we've got 'timezone=utc' set
        sql = 'SHOW TIMEZONE'
        results = base.query(sql)
        ok_(
            'UTC' in results[0],
            """Please set PostgreSQL to use the UTC timezone.
               Documentation on how to do this is included in
               the INSTALL instructions."""
        )

    #--------------------------------------------------------------------------
    def test_query(self):
        base = PostgreSQLBase(config=self.config)

        # A working query
        sql = 'SELECT * FROM reports'
        results = base.query(sql)
        eq_(len(results), 2)
        ok_('http://mywebsite.com' in results[0])
        ok_('admin@example.com' in results[1])

        # A working query with parameters
        sql = 'SELECT * FROM reports WHERE url=%(url)s'
        params = {'url': 'http://mywebsite.com'}
        results = base.query(sql, params)
        eq_(len(results), 1)
        ok_('http://mywebsite.com' in results[0])

        # A failing query
        sql = 'SELECT FROM reports LIMIT notanumber'
        assert_raises(DatabaseError, base.query, sql)

    #--------------------------------------------------------------------------
    def test_count(self):
        base = PostgreSQLBase(config=self.config)

        # A working count
        sql = 'SELECT count(*) FROM reports'
        count = base.count(sql)
        eq_(count, 2)

        # A working count with parameters
        sql = 'SELECT count(*) FROM reports WHERE url=%(url)s'
        params = {'url': 'http://mywebsite.com'}
        count = base.count(sql, params)
        eq_(count, 1)

        # A failing count
        sql = 'SELECT count(`invalid_field_name`) FROM reports'
        assert_raises(DatabaseError, base.count, sql)

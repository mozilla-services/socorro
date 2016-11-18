# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_, assert_raises

from socorro.lib import DatabaseError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.unittest.testbase import TestCase

from socorro.lib import util

from .unittestbase import PostgreSQLTestCase


#==============================================================================
class TestPostgreSQLBase(TestCase):
    """Test PostgreSQLBase class. """

    #--------------------------------------------------------------------------
    def get_dummy_context(self):
        """Create a dummy config object to use when testing."""
        context = util.DotDict({
            'database_class': ConnectionContext,
            'database_hostname': 'somewhere',
            'database_port': '8888',
            'database_name': 'somename',
            'database_username': 'someuser',
            'database_password': 'somepasswd',
        })
        context.platforms = (
            {
                "id": "windows",
                "name": "Windows NT"
            },
            {
                "id": "linux",
                "name": "Linux"
            }
        )
        context.non_release_channels = ['beta', 'aurora', 'nightly']
        context.restricted_channels = ['beta']
        return context

    #--------------------------------------------------------------------------
    def get_instance(self, config=None):
        """Return an instance of PostgreSQLBase with the config parameter as
        a context or the default one if config is None.
        """
        args = {
            "config": config or self.get_dummy_context()
        }
        return PostgreSQLBase(**args)

    #--------------------------------------------------------------------------
    def test_parse_versions(self):
        """Test PostgreSQLBase.parse_versions()."""
        pgbase = self.get_instance()

        # .....................................................................
        # Test 1: only product:version args
        versions_list = ["Firefox:9.0", "Fennec:12.1"]
        versions_list_exp = ["Firefox", "9.0", "Fennec", "12.1"]
        products = []
        products_exp = []

        (versions, products) = pgbase.parse_versions(versions_list, products)
        eq_(versions, versions_list_exp)
        eq_(products, products_exp)

        # .....................................................................
        # Test 2: product:version and product only args
        versions_list = ["Firefox:9.0", "Fennec"]
        versions_list_exp = ["Firefox", "9.0"]
        products = []
        products_exp = ["Fennec"]

        (versions, products) = pgbase.parse_versions(versions_list, products)
        eq_(versions, versions_list_exp)
        eq_(products, products_exp)

        # .....................................................................
        # Test 3: product only args
        versions_list = ["Firefox", "Fennec"]
        versions_list_exp = []
        products = []
        products_exp = ["Firefox", "Fennec"]

        (versions, products) = pgbase.parse_versions(versions_list, products)
        eq_(versions, versions_list_exp)
        eq_(products, products_exp)


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

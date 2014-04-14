# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from socorro.external import DatabaseError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import search_common, util

from .unittestbase import PostgreSQLTestCase


#==============================================================================
class TestPostgreSQLBase(unittest.TestCase):
    """Test PostgreSQLBase class. """

    #--------------------------------------------------------------------------
    def get_dummy_context(self):
        """Create a dummy config object to use when testing."""
        context = util.DotDict()
        context.database = util.DotDict({
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

    #--------------------------------------------------------------------------
    def test_build_reports_sql_from(self):
        """Test PostgreSQLBase.build_reports_sql_from()."""
        pgbase = self.get_instance()
        params = util.DotDict()
        params.report_process = ""

        # .....................................................................
        # Test 1: no specific parameter
        sql_exp = "FROM reports r"

        sql = pgbase.build_reports_sql_from(params)
        eq_(sql, sql_exp)

        # .....................................................................
        # Test 2: with a plugin
        params.report_process = "plugin"
        sql_exp = "FROM reports r JOIN plugins_reports ON " \
                  "plugins_reports.report_id = r.id JOIN plugins ON " \
                  "plugins_reports.plugin_id = plugins.id"

        sql = pgbase.build_reports_sql_from(params)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)

    #--------------------------------------------------------------------------
    def test_build_reports_sql_where(self):
        """ Test PostgreSQLBase.build_reports_sql_where()."""
        config = self.get_dummy_context()
        pgbase = self.get_instance()
        params = search_common.get_parameters({})  # Get default search params
        default_params = util.DotDict(params.copy())
        sql_params = {}

        # .....................................................................
        # Test 1: default values for parameters
        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 2: terms and search_mode = is_exactly
        sql_params = {}
        params.terms = "signature"
        params.search_mode = "is_exactly"

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND r.signature=%(term)s"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "term": params.terms
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 3: terms and search_mode != is_exactly
        sql_params = {}
        params.terms = "signature%"
        params.search_mode = "starts_with"

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND r.signature LIKE %(term)s"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "term": params.terms
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 4: products
        sql_params = {}
        params.terms = default_params.terms
        params.search_mode = default_params.search_mode
        params.products = ["Firefox", "Fennec"]

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND (r.product=%(product0)s OR " \
                  "r.product=%(product1)s)"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "product0": "Firefox",
            "product1": "Fennec"
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 5: os
        sql_params = {}
        params.products = default_params.products
        params.os = ["Windows"]

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND (r.os_name=%(os0)s)"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "os0": "Windows"
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 6: build_ids
        sql_params = {}
        params.os = default_params.os
        params.build_ids = ["20120101123456"]

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND (r.build=%(build0)s)"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "build0": "20120101123456"
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 7: reasons
        sql_params = {}
        params.build_ids = default_params.build_ids
        params.reasons = ["EXCEPTION", "OVERFLOW"]

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND (r.reason=%(reason0)s OR " \
                  "r.reason=%(reason1)s)"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "reason0": "EXCEPTION",
            "reason1": "OVERFLOW"
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 8: report_type
        sql_params = {}
        params.reasons = default_params.reasons
        params.report_type = "crash"

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND r.hangid IS NULL"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 9: versions
        sql_params = {}
        params.report_type = default_params.report_type
        params.versions = ["Firefox", "12.0a1", "Fennec", "11.0", "Firefox",
                           "13.0(beta)"]
        params.versions_info = {
            "Firefox:12.0a1": {
                "version_string": "12.0a1",
                "product_name": "Firefox",
                "major_version": "12.0",
                "release_channel": "Nightly",
                "build_id": ["20120101123456"],
                "is_rapid_beta": False,
                "from_rapid_beta": False,
                "rapid_beta_version": "Firefox:12.0a1",
            },
            "Fennec:11.0": {
                "version_string": "11.0",
                "product_name": "Fennec",
                "major_version": None,
                "release_channel": None,
                "build_id": None,
                "is_rapid_beta": False,
                "from_rapid_beta": False,
                "rapid_beta_version": "Fennec:11.0",
            },
            "Firefox:13.0(beta)": {
                "version_string": "13.0(beta)",
                "product_name": "Firefox",
                "major_version": "13.0",
                "release_channel": "Beta",
                "build_id": ["20120101123456", "20120101098765"],
                "is_rapid_beta": False,
                "from_rapid_beta": True,
                "rapid_beta_version": "Firefox:13.0b",
            },
            "Firefox:13.0b": {
                "version_string": "13.0b",
                "product_name": "Firefox",
                "major_version": "13.0b",
                "release_channel": "Beta",
                "build_id": None,
                "is_rapid_beta": True,
                "from_rapid_beta": True,
                "rapid_beta_version": "Firefox:13.0b",
            }
        }

        sql_exp = """
            WHERE r.date_processed BETWEEN %(from_date)s AND %(to_date)s
            AND
                ((r.release_channel ILIKE 'nightly'
                    AND r.product=%(version0)s
                    AND r.version=%(version1)s)
                OR (r.product=%(version2)s
                    AND r.version=%(version3)s)
                OR (r.release_channel ILIKE 'beta'
                    AND r.build IN ('20120101123456', '20120101098765')
                    AND r.product=%(version4)s
                    AND r.version=%(version5)s))
        """
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "version0": "Firefox",
            "version1": "12.0",
            "version2": "Fennec",
            "version3": "11.0",
            "version4": "Firefox",
            "version5": "13.0"
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)

        # squeeze all \s, \r, \t...
        sql = " ".join(sql.split())
        sql_exp = " ".join(sql_exp.split())

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 10: report_process = plugin
        sql_params = {}
        params.versions = default_params.versions
        params.versions_infos = None
        params.report_process = "plugin"

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND r.process_type = 'plugin' AND " \
                  "plugins_reports.date_processed BETWEEN " \
                  "%(from_date)s AND %(to_date)s"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 11: report_process != plugin
        sql_params = {}
        params.report_process = "content"

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND r.process_type = 'content'"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

        # .....................................................................
        # Test 12: plugins
        sql_params = {}
        params.report_process = "plugin"
        params.plugin_terms = "plugin_name"
        params.plugin_search_mode = "is_exactly"
        params.plugin_in = ["name"]

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND r.process_type = 'plugin' AND " \
                  "plugins_reports.date_processed BETWEEN " \
                  "%(from_date)s AND %(to_date)s AND " \
                  "(plugins.name=%(plugin_term)s)"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "plugin_term": params.plugin_terms
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        eq_(sql, sql_exp)
        eq_(sql_params, sql_params_exp)

    #--------------------------------------------------------------------------
    def test_build_version_where(self):
        """Test PostgreSQLBase.build_reports_sql_version_where()."""
        config = self.get_dummy_context()
        pgbase = self.get_instance()

        params = util.DotDict()
        params["versions_info"] = {
            "Firefox:12.0a1": {
                "version_string": "12.0a1",
                "product_name": "Firefox",
                "major_version": "12.0",
                "release_channel": "Nightly",
                "build_id": ["20120101123456"]
            },
            "Fennec:11.0": {
                "version_string": "11.0",
                "product_name": "Fennec",
                "major_version": None,
                "release_channel": None,
                "build_id": None
            },
            "Firefox:13.0(beta)": {
                "version_string": "13.0(beta)",
                "product_name": "Firefox",
                "major_version": "13.0",
                "release_channel": "beta",
                "build_id": ["20120101123456", "20120101098765"]
            },
            "WaterWolf:1.0a1": {
                "version_string": "1.0a1",
                "product_name": "WaterWolf",
                "major_version": "1.0a1",
                "release_channel": "nightly-water",
                "build_id": None
            },
            "WaterWolf:2.0": {
                "version_string": "2.0",
                "product_name": "WaterWolf",
                "major_version": "2.0",
                "release_channel": None,
                "build_id": None
            }
        }

        # test 1
        params["versions"] = ["Firefox", "13.0(beta)"]
        key = "Firefox:13.0(beta)"
        x = 0
        sql_params = {
            "version0": "Firefox",
            "version1": "13.0(beta)"
        }
        sql_params_exp = {
            "version0": "Firefox",
            "version1": "13.0"
        }
        version_where = []
        version_where_exp = (
            "("
            "r.release_channel ILIKE 'beta'"
            " AND r.build IN ('20120101123456', '20120101098765')"
            " AND r.product=%(version0)s"
            " AND r.version=%(version1)s"
            ")"
        )

        version_where = pgbase.build_version_where(
            "Firefox",
            "13.0",
            x,
            sql_params,
            params["versions_info"][key],
            config,
        )

        eq_(version_where, version_where_exp)
        eq_(sql_params, sql_params_exp)

        # test 2, verify release channels get added as expected
        params["versions"] = ["WaterWolf", "1.0a1"]
        key = "WaterWolf:1.0a1"
        x = 0
        sql_params = {
            "version0": "WaterWolf",
            "version1": "1.0a1"
        }
        sql_params_exp = {
            "version0": "WaterWolf",
            "version1": "1.0a1"
        }
        version_where = []
        version_where_exp = (
            "("
            "r.release_channel ILIKE 'nightly-water'"
            " AND r.product=%(version0)s"
            " AND r.version=%(version1)s"
            ")"
        )

        version_where = pgbase.build_version_where(
            "WaterWolf",
            "1.0a1",
            x,
            sql_params,
            params["versions_info"][key],
            config,
        )

        eq_(version_where, version_where_exp)
        eq_(sql_params, sql_params_exp)

        # test 3, what if a release channel is "null"
        params["versions"] = ["WaterWolf", "2.0"]
        key = "WaterWolf:2.0"
        x = 0
        sql_params = {
            "version0": "WaterWolf",
            "version1": "2.0"
        }
        sql_params_exp = {
            "version0": "WaterWolf",
            "version1": "2.0"
        }
        version_where_exp = (
            "("
            "r.product=%(version0)s"
            " AND r.version=%(version1)s"
            ")"
        )

        version_where = pgbase.build_version_where(
            "WaterWolf",
            "2.0",
            x,
            sql_params,
            params["versions_info"][key],
            config,
        )

        eq_(version_where, version_where_exp)
        eq_(sql_params, sql_params_exp)


#==============================================================================
@attr(integration='postgres')  # for nosetests
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
        sql = 'SELECT FROM reports'
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

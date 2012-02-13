import unittest

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import search_common, util

import socorro.unittest.testlib.util as testutil


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestPostgreSQLBase(unittest.TestCase):
    """Test PostgreSQLBase class. """

    #--------------------------------------------------------------------------
    def get_dummy_context(self):
        """Create a dummy config object to use when testing."""
        context = util.DotDict()
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
        context.channels = ['Beta', 'Aurora', 'Nightly', 'beta', 'aurora',
                            'nightly']
        context.restricted_channels = ['Beta', 'beta']
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
        self.assertEqual(versions, versions_list_exp)
        self.assertEqual(products, products_exp)

        # .....................................................................
        # Test 2: product:version and product only args
        versions_list = ["Firefox:9.0", "Fennec"]
        versions_list_exp = ["Firefox", "9.0"]
        products = []
        products_exp = ["Fennec"]

        (versions, products) = pgbase.parse_versions(versions_list, products)
        self.assertEqual(versions, versions_list_exp)
        self.assertEqual(products, products_exp)

        # .....................................................................
        # Test 3: product only args
        versions_list = ["Firefox", "Fennec"]
        versions_list_exp = []
        products = []
        products_exp = ["Firefox", "Fennec"]

        (versions, products) = pgbase.parse_versions(versions_list, products)
        self.assertEqual(versions, versions_list_exp)
        self.assertEqual(products, products_exp)

    #--------------------------------------------------------------------------
    def test_build_reports_sql_from(self):
        """Test PostgreSQLBase.build_reports_sql_from()."""
        pgbase = self.get_instance()
        params = util.DotDict()
        params.report_process = ""
        params.branches = []

        # .....................................................................
        # Test 1: no specific parameter
        sql_exp = "FROM reports r"

        sql = pgbase.build_reports_sql_from(params)
        self.assertEqual(sql, sql_exp)

        # .....................................................................
        # Test 2: with a plugin
        params.report_process = "plugin"
        sql_exp = "FROM reports r JOIN plugins_reports ON " \
                  "plugins_reports.report_id = r.id JOIN plugins ON " \
                  "plugins_reports.plugin_id = plugins.id"

        sql = pgbase.build_reports_sql_from(params)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        self.assertEqual(sql, sql_exp)

        # .....................................................................
        # Test 3: with a branch
        params.report_process = ""
        params.branches = ["2.0"]
        sql_exp = "FROM reports r JOIN branches ON " \
                  "(branches.product = r.product AND branches.version = " \
                  "r.version)"

        sql = pgbase.build_reports_sql_from(params)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        self.assertEqual(sql, sql_exp)

        # .....................................................................
        # Test 4: with a plugin and a branch
        params.report_process = "plugin"
        params.branches = ["2.0"]
        sql_exp = "FROM reports r JOIN plugins_reports ON " \
                  "plugins_reports.report_id = r.id JOIN plugins ON " \
                  "plugins_reports.plugin_id = plugins.id JOIN branches ON " \
                  "(branches.product = r.product AND branches.version = " \
                  "r.version)"

        sql = pgbase.build_reports_sql_from(params)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        self.assertEqual(sql, sql_exp)

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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 6: branches
        sql_params = {}
        params.os = default_params.os
        params.branches = ["2.2", "2.3", "4.0"]

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND (branches.branch=%(branch0)s OR " \
                  "branches.branch=%(branch1)s OR branches.branch=%(branch2)s)"
        sql_params_exp = {
            "from_date": params.from_date,
            "to_date": params.to_date,
            "branch0": "2.2",
            "branch1": "2.3",
            "branch2": "4.0"
        }

        (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params,
                                                           config)
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 7: build_ids
        sql_params = {}
        params.branches = default_params.branches
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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 8: reasons
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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 9: report_type
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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 10: versions
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
                "release_channel": "Beta",
                "build_id": ["20120101123456", "20120101098765"]
            }
        }

        sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND " \
                  "%(to_date)s AND ((r.product=%(version0)s AND " \
                  "r.release_channel ILIKE 'nightly' AND " \
                  "r.version=%(version1)s) OR (r.product=%(version2)s AND " \
                  "r.version=%(version3)s) OR (r.product=%(version4)s AND " \
                  "r.release_channel ILIKE 'beta' AND r.build IN " \
                  "('20120101123456', '20120101098765') AND " \
                  "r.version=%(version5)s))"
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
        sql = " ".join(sql.split())  # squeeze all \s, \r, \t...

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 11: report_process = plugin
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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 12: report_process != plugin
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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

        # .....................................................................
        # Test 13: plugins
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

        self.assertEqual(sql, sql_exp)
        self.assertEqual(sql_params, sql_params_exp)

    #--------------------------------------------------------------------------
    def test_build_reports_sql_version_where(self):
        """Test PostgreSQLBase.build_reports_sql_version_where()."""
        config = self.get_dummy_context()
        pgbase = self.get_instance()

        key = "Firefox:13.0(beta)"
        params = util.DotDict()
        versions = params["versions"] = ["Firefox", "13.0(beta)"]
        versions_info = params["versions_info"] = {
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
                "release_channel": "Beta",
                "build_id": ["20120101123456", "20120101098765"]
            }
        }
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
        version_where_exp = ["r.release_channel ILIKE 'beta'",
                             "r.build IN ('20120101123456', '20120101098765')"]

        version_where = pgbase.build_reports_sql_version_where(
            key,
            params,
            config,
            x,
            sql_params,
            version_where
        )

        self.assertEqual(version_where, version_where_exp)
        self.assertEqual(sql_params, sql_params_exp)

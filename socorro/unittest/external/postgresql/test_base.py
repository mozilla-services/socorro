import datetime
import unittest

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import search_common, util
from socorro.lib.datetimeutil import UTC

import socorro.unittest.testlib.util as tutil


#------------------------------------------------------------------------------
def setup_module():
    tutil.nosePrintModule(__file__)


#------------------------------------------------------------------------------
def get_dummy_context():
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
    return context


#------------------------------------------------------------------------------
def get_instance(config=None):
    """Return an instance of PostgreSQLBase with the config parameter as
    a context or the default one if config is None.
    """
    args = {
        "config": config or get_dummy_context()
    }
    return PostgreSQLBase(**args)


#------------------------------------------------------------------------------
def test_parse_versions():
    """Test PostgreSQLBase.parse_versions()."""
    pgbase = get_instance()

    # Test 1: only product:version args
    versions_list = ["Firefox:9.0", "Fennec:12.1"]
    versions_list_exp = ["Firefox", "9.0", "Fennec", "12.1"]
    products = []
    products_exp = []

    (versions, products) = pgbase.parse_versions(versions_list, products)
    assert versions == versions_list_exp, \
           "Expected versions to be %s, got %s instead" % (versions_list_exp,
                                                           versions_list)
    assert products == products_exp, \
           "Expected products to be %s, got %s instead" % (products_exp,
                                                           products)

    # Test 2: product:version and product only args
    versions_list = ["Firefox:9.0", "Fennec"]
    versions_list_exp = ["Firefox", "9.0"]
    products = []
    products_exp = ["Fennec"]

    (versions, products) = pgbase.parse_versions(versions_list, products)
    assert versions == versions_list_exp, \
           "Expected versions to be %s, got %s instead" % (versions_list_exp,
                                                           versions_list)
    assert products == products_exp, \
           "Expected products to be %s, got %s instead" % (products_exp,
                                                           products)

    # Test 2: product only args
    versions_list = ["Firefox", "Fennec"]
    versions_list_exp = []
    products = []
    products_exp = ["Firefox", "Fennec"]

    (versions, products) = pgbase.parse_versions(versions_list, products)
    assert versions == versions_list_exp, \
           "Expected versions to be %s, got %s instead" % (versions_list_exp,
                                                           versions_list)
    assert products == products_exp, \
           "Expected products to be %s, got %s instead" % (products_exp,
                                                           products)


#------------------------------------------------------------------------------
def test_build_reports_sql_from():
    """Test PostgreSQLBase.build_reports_sql_from()."""
    pgbase = get_instance()
    params = util.DotDict()
    params.report_process = ""
    params.branches = []

    # Test 1: no specific parameter
    sql_exp = "FROM reports r"

    sql = pgbase.build_reports_sql_from(params)
    assert sql == sql_exp, "Expected sql to be %s, got %s instead" % (sql_exp,
                                                                      sql)

    # Test 2: with a plugin
    params.report_process = "plugin"
    sql_exp = "FROM reports r JOIN plugins_reports ON " \
              "plugins_reports.report_id = r.id JOIN plugins ON " \
              "plugins_reports.plugin_id = plugins.id"

    sql = pgbase.build_reports_sql_from(params)
    sql = " ".join(sql.split()) # squeeze all \s, \r, \t...

    assert sql == sql_exp, "Expected sql to be %s, got %s instead" % (sql_exp,
                                                                      sql)

    # Test 3: with a branch
    params.report_process = ""
    params.branches = ["2.0"]
    sql_exp = "FROM reports r JOIN branches ON " \
              "(branches.product = r.product AND branches.version = r.version)"

    sql = pgbase.build_reports_sql_from(params)
    sql = " ".join(sql.split()) # squeeze all \s, \r, \t...

    assert sql == sql_exp, "Expected sql to be %s, got %s instead" % (sql_exp,
                                                                      sql)

    # Test 4: with a plugin and a branch
    params.report_process = "plugin"
    params.branches = ["2.0"]
    sql_exp = "FROM reports r JOIN plugins_reports ON " \
              "plugins_reports.report_id = r.id JOIN plugins ON " \
              "plugins_reports.plugin_id = plugins.id JOIN branches ON " \
              "(branches.product = r.product AND branches.version = r.version)"

    sql = pgbase.build_reports_sql_from(params)
    sql = " ".join(sql.split()) # squeeze all \s, \r, \t...

    assert sql == sql_exp, "Expected sql to be %s, got %s instead" % (sql_exp,
                                                                      sql)


#------------------------------------------------------------------------------
def test_build_reports_sql_where():
    """ Test PostgreSQLBase.build_reports_sql_where()."""
    pgbase = get_instance()
    params = search_common.get_parameters({}) # Get default search params
    sql_params = {}

    # Test 1: default values for parameters
    sql_exp = "WHERE r.date_processed BETWEEN %(from_date)s AND %(to_date)s"
    sql_params_exp = {
        "from_date": params.from_date,
        "to_date": params.to_date
    }

    (sql, sql_params) = pgbase.build_reports_sql_where(params, sql_params)
    sql = " ".join(sql.split()) # squeeze all \s, \r, \t...

    assert sql == sql_exp, "Expected sql to be %s, got %s instead" % (sql_exp,
                                                                      sql)
    assert sql_params == sql_params_exp, "Expected sql params to be %s, got " \
                                         "%s instead" % (sql_params_exp,
                                                         sql_params)

    # WE NEED MOAR TEST


#------------------------------------------------------------------------------
def test_build_reports_sql_version_where():
    """Test PostgreSQLBase.build_reports_sql_version_where()."""
    # There ought to be tests here.
    pass

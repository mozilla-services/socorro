import unittest
import datetime
import psycopg2

from socorro.external.postgresql.crashes import Crashes
from socorro.external.postgresql.crashes import MissingOrBadArgumentException
from socorro.lib import datetimeutil, util

import socorro.unittest.testlib.util as testutil
from unittestbase import PostgreSQLTestCase


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestCrashes(unittest.TestCase):
    """Test socorro.external.postgresql.crashes.Crashes class. """

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
            },
            {
                "id": "mac",
                "name": "Mac OS X"
            }
        )
        return context

    #--------------------------------------------------------------------------
    def get_instance(self, config=None):
        """Return an instance of Crashes with the config parameter as
        a context or the default one if config is None.
        """
        args = {
            "config": config or self.get_dummy_context()
        }
        return Crashes(**args)

    #--------------------------------------------------------------------------
    def test_prepare_search_params(self):
        """Test Crashes.prepare_search_params()."""
        crashes = self.get_instance()

        # .....................................................................
        # Test 1: no args
        args = {}
        self.assertRaises(MissingOrBadArgumentException,
                          crashes.prepare_search_params,
                          **args)

        # .....................................................................
        # Test 2: a signature
        args = {
            "signature": "something"
        }

        params = crashes.prepare_search_params(**args)
        self.assertTrue("signature" in params)
        self.assertTrue("terms" in params)
        self.assertEqual(params["signature"], "something")
        self.assertEqual(params["signature"], params["terms"])

        # .....................................................................
        # Test 3: some OS
        args = {
            "signature": "something",
            "os": ["windows", "linux"]
        }

        params = crashes.prepare_search_params(**args)
        self.assertTrue("os" in params)
        self.assertEqual(len(params["os"]), 2)
        self.assertEqual(params["os"][0], "Windows NT")
        self.assertEqual(params["os"][1], "Linux")

        # .....................................................................
        # Test 4: with a plugin
        args = {
            "signature": "something",
            "report_process": "plugin",
            "plugin_terms": ["some", "plugin"],
            "plugin_search_mode": "contains",
        }

        params = crashes.prepare_search_params(**args)
        self.assertTrue("plugin_terms" in params)
        self.assertEqual(params["plugin_terms"], "%some plugin%")


#==============================================================================
class IntegrationTestCrashes(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crashes.Crashes class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestCrashes, self).setUp()

        cursor = self.connection.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE reports
            (
                date_processed timestamp with time zone,
                uuid character varying(50) NOT NULL,
                hangid character varying(50)
            );
        """)

        # Insert data
        now = datetimeutil.utc_now()
        yesterday = now - datetime.timedelta(days=1)
        uuid = "%%s-%s" % now.strftime("%y%m%d")
        yesterday_uuid = "%%s-%s" % yesterday.strftime("%y%m%d")

        cursor.execute("""
            INSERT INTO reports VALUES
            ('%s', '%s', '%s'),
            ('%s', '%s', '%s'),
            ('%s', '%s', '%s'),
            ('%s', '%s', '%s'),
            ('%s', '%s', '%s'),
            ('%s', '%s', '%s')
            ;
        """ % (now, uuid % "a1", "ab1",
               now, uuid % "a2", "ab1",
               now, uuid % "a3", "ab1",
               now, uuid % "b1", "xxx",
               now, uuid % "c1", "cb1",
               now, yesterday_uuid % "c2", "cb1"))

        self.connection.commit()
        cursor.close()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            DROP TABLE reports;
        """)
        self.connection.commit()
        cursor.close()
        super(IntegrationTestCrashes, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get_paireduuid(self):
        crashes = Crashes(config=self.config)
        now = datetimeutil.utc_now()
        yesterday = now - datetime.timedelta(days=1)
        uuid = "%%s-%s" % now.strftime("%y%m%d")
        yesterday_uuid = "%%s-%s" % yesterday.strftime("%y%m%d")

        #......................................................................
        # Test 1: a uuid and a hangid
        params = {
            "uuid": uuid % "a1",
            "hangid": "ab1"
        }
        res = crashes.get_paireduuid(**params)
        res_expected = {
            "hits": [
                {
                    "uuid": uuid % "a2"
                }
            ],
            "total": 1
        }
        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: a uuid only
        params = {
            "uuid": uuid % "a1"
        }
        res = crashes.get_paireduuid(**params)
        res_expected = {
            "hits": [
                {
                    "uuid": uuid % "a2"
                },
                {
                    "uuid": uuid % "a3"
                }
            ],
            "total": 2
        }
        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 3: a query with no result
        params = {
            "uuid": uuid % "b1"
        }
        res = crashes.get_paireduuid(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }
        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 4: one result that was yesterday
        params = {
            "uuid": uuid % "c1"
        }
        res = crashes.get_paireduuid(**params)
        res_expected = {
            "hits": [
                {
                    "uuid": yesterday_uuid % "c2"
                }
            ],
            "total": 1
        }
        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 5: missing argument
        params = {
            "hangid": "c1"
        }
        self.assertRaises(MissingOrBadArgumentException,
                          crashes.get_paireduuid,
                          **params)

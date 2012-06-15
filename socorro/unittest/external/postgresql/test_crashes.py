import unittest
import datetime

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

        # Insert data for paireduuid test
        now = datetimeutil.utc_now()
        yesterday = now - datetime.timedelta(days=1)
        uuid = "%%s-%s" % now.strftime("%y%m%d")
        yesterday_uuid = "%%s-%s" % yesterday.strftime("%y%m%d")

        cursor.execute("""
            INSERT INTO reports (date_processed, uuid, hangid)
            VALUES
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

        # Insert data for frequency test
        cursor.execute("""
            INSERT INTO reports
            (id, uuid, build, signature, os_name, date_processed)
            VALUES
            (1, 'abc', '2012033116', 'js', 'Windows NT', '%(now)s'),
            (2, 'def', '2012033116', 'js', 'Linux', '%(now)s'),
            (3, 'hij', '2012033117', 'js', 'Windows NT', '%(now)s'),
            (4, 'klm', '2012033117', 'blah', 'Unknown', '%(now)s')
        """ % {"now": now})

        self.connection.commit()
        cursor.close()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE reports
            CASCADE
        """)
        self.connection.commit()
        cursor.close()
        super(IntegrationTestCrashes, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get_frequency(self):
        self.config.platforms = (
            {
                "id": "windows",
                "name": "Windows NT"
            },
            {
                "id": "linux",
                "name": "Linux"
            }
        )
        crashes = Crashes(config=self.config)

        #......................................................................
        # Test 1
        params = {
            "signature": "js"
        }
        res_expected = {
            "hits": [
                {
                    "build_date": "2012033117",
                    "count": 1,
                    "frequency": 1.0,
                    "total": 1,
                    "count_windows": 1,
                    "frequency_windows": 1.0,
                    "count_linux": 0,
                    "frequency_linux": 0
                },
                {
                    "build_date": "2012033116",
                    "count": 2,
                    "frequency": 1.0,
                    "total": 2,
                    "count_windows": 1,
                    "frequency_windows": 1.0,
                    "count_linux": 1,
                    "frequency_linux": 1.0
                }
            ],
            "total": 2
        }
        res = crashes.get_frequency(**params)

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2
        params = {
            "signature": "blah"
        }
        res_expected = {
            "hits": [
                {
                    "build_date": "2012033117",
                    "count": 1,
                    "frequency": 1.0,
                    "total": 1,
                    "count_windows": 0,
                    "frequency_windows": 0.0,
                    "count_linux": 0,
                    "frequency_linux": 0.0
                }
            ],
            "total": 1
        }
        res = crashes.get_frequency(**params)

        self.assertEqual(res, res_expected)

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

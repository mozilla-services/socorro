# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import datetime
from nose.plugins.attrib import attr

from socorro.external import MissingOrBadArgumentError
from socorro.external.postgresql.crashes import Crashes
from socorro.lib import datetimeutil, util

from unittestbase import PostgreSQLTestCase


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
        self.assertRaises(MissingOrBadArgumentError,
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
@attr(integration='postgres')  # for nosetests
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

        build_date = now - datetime.timedelta(days=30)
        sunset_date = now + datetime.timedelta(days=30)

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

        # Insert data for daily crashes test

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, release_name)
            VALUES
            (
                'Firefox',
                1,
                'firefox'
            );
        """)

        cursor.execute("""
            INSERT INTO product_versions
            (product_version_id, product_name, major_version, release_version,
             version_string, version_sort, build_date, sunset_date,
             featured_version, build_type)
            VALUES
            (
                1,
                'Firefox',
                '11.0',
                '11.0',
                '11.0',
                '00000011000',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly'
            ),
            (
                2,
                'Firefox',
                '12.0',
                '12.0',
                '12.0',
                '00000012000',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly'
            ),
            (
                3,
                'Firefox',
                '13.0',
                '13.0',
                '13.0',
                '00000013000',
                '%(build_date)s',
                '%(sunset_date)s',
                'f',
                'Nightly'
            );
        """ % {"build_date": build_date, "sunset_date": sunset_date})

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1)
        """)

        cursor.execute("""
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            ('Firefox', 'Nightly', 0.1)
        """)

        cursor.execute("""
            INSERT INTO os_names
            (os_short_name, os_name)
            VALUES
            ('win', 'Windows'),
            ('mac', 'Mac OS X'),
            ('lin', 'Linux')
        """)

        cursor.execute("""
            INSERT INTO process_types
            (process_type)
            VALUES
            ('crash'),
            ('hang')
        """)

        cursor.execute("""
            INSERT INTO crash_types
            (crash_type_id, crash_type, crash_type_short, process_type,
             old_code, include_agg)
            VALUES
            (1, 'Browser', 'crash', 'crash', 'c', TRUE),
            (2, 'Hang', 'hang', 'hang', 'h', TRUE)
        """)

        cursor.execute("""
            INSERT INTO home_page_graph
            (product_version_id, report_date, report_count, adu, crash_hadu)
            VALUES
            (1, '%(now)s', 5, 20, 0.12),
            (2, '%(yesterday)s', 2, 14, 0.12)
        """ % {"now": now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO home_page_graph_build
            (product_version_id, report_date, build_date, report_count, adu)
            VALUES
            (1, '%(now)s', '%(now)s', 5, 200),
            (1, '%(now)s', '%(yesterday)s', 3, 274),
            (2, '%(yesterday)s', '%(now)s', 3, 109)
        """ % {"now": now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO crashes_by_user
            (product_version_id, os_short_name, crash_type_id, report_date,
             report_count, adu)
            VALUES
            (1, 'win', 1, '%(now)s', 5, 200),
            (1, 'lin', 2, '%(now)s', 5, 200),
            (1, 'win', 2, '%(now)s', 5, 200),
            (2, 'win', 1, '%(now)s', 5, 200),
            (3, 'win', 1, '%(now)s', 1, 10),
            (3, 'lin', 1, '%(now)s', 1, 10),
            (3, 'mac', 1, '%(now)s', 1, 10),
            (3, 'win', 2, '%(now)s', 1, 10),
            (3, 'lin', 2, '%(now)s', 1, 10),
            (3, 'mac', 2, '%(now)s', 1, 10)
        """ % {"now": now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO crashes_by_user_build
            (product_version_id, os_short_name, crash_type_id, build_date,
             report_date, report_count, adu)
            VALUES
            (1, 'win', 1, '%(now)s', '%(now)s', 1, 10),
            (1, 'lin', 2, '%(now)s', '%(yesterday)s', 1, 10),
            (1, 'win', 2, '%(yesterday)s', '%(now)s', 1, 10),
            (1, 'mac', 1, '%(yesterday)s', '%(now)s', 1, 10),
            (1, 'win', 1, '%(yesterday)s', '%(now)s', 1, 10),
            (2, 'lin', 1, '%(yesterday)s', '%(now)s', 1, 10)
        """ % {"now": now, "yesterday": yesterday})

        self.connection.commit()
        cursor.close()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE reports, home_page_graph_build, home_page_graph,
                     crashes_by_user, crashes_by_user_build, crash_types,
                     process_types, os_names,
                     product_versions, product_release_channels,
                     release_channels, products
            CASCADE
        """)
        self.connection.commit()
        cursor.close()
        super(IntegrationTestCrashes, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get_daily(self):
        crashes = Crashes(config=self.config)
        now = datetimeutil.utc_now().date()
        today = now.isoformat()
        yesterday = (now - datetime.timedelta(days=1)).isoformat()

        # Test 1: one product, one version
        params = {
            "product": "Firefox",
            "versions": ["11.0"]
        }
        res_expected = {
            "hits": {
                "Firefox:11.0": {
                    today: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": today,
                        "report_count": 5,
                        "adu": 20,
                        "crash_hadu": 0.12
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 2: one product, several versions, range by build date
        params = {
            "product": "Firefox",
            "versions": ["11.0", "12.0"],
            "date_range_type": "build"
        }
        res_expected = {
            "hits": {
                "Firefox:11.0": {
                    today: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": today,
                        "report_count": 5,
                        "adu": 200,
                        "crash_hadu": 25.0
                    },
                    yesterday: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": yesterday,
                        "report_count": 3,
                        "adu": 274,
                        "crash_hadu": 10.949
                    }
                },
                "Firefox:12.0": {
                    today: {
                        "product": "Firefox",
                        "version": "12.0",
                        "date": today,
                        "report_count": 3,
                        "adu": 109,
                        "crash_hadu": 27.523
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 3: one product, one version, extended fields
        params = {
            "product": "Firefox",
            "versions": ["11.0"],
            "os": "windows",
            "separated_by": "report_type"
        }
        res_expected = {
            "hits": {
                "Firefox:11.0:crash": {
                    today: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": today,
                        "report_count": 5,
                        "report_type": "Browser",
                        "os": "Windows",
                        "adu": 200,
                        "crash_hadu": 25.0,
                        "throttle": 0.1
                    }
                },
                "Firefox:11.0:hang": {
                    today: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": today,
                        "report_count": 5,
                        "report_type": "Hang",
                        "os": "Windows",
                        "adu": 200,
                        "crash_hadu": 25.0,
                        "throttle": 0.1
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 4:
        params = {
            "product": "Firefox",
            "versions": ["13.0"],
            "report_type": "hang"
        }
        res_expected = {
            "hits": {
                "Firefox:13.0": {
                    today: {
                        "product": "Firefox",
                        "version": "13.0",
                        "date": today,
                        "report_count": 3,
                        "report_type": "Hang",
                        "adu": 30,
                        "crash_hadu": 100.0,
                        "throttle": 0.1
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 5: extended fields, by build date and with report type
        params = {
            "product": "Firefox",
            "versions": ["11.0", "12.0"],
            "report_type": "crash",
            "date_range_type": "build"
        }
        res_expected = {
            "hits": {
                "Firefox:11.0": {
                    today: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": today,
                        "report_count": 1,
                        "report_type": "Browser",
                        "adu": 10,
                        "crash_hadu": 100.0,
                        "throttle": 0.1
                    },
                    yesterday: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": yesterday,
                        "report_count": 2,
                        "report_type": "Browser",
                        "adu": 20,
                        "crash_hadu": 100.0,
                        "throttle": 0.1
                    }
                },
                "Firefox:12.0": {
                    yesterday: {
                        "product": "Firefox",
                        "version": "12.0",
                        "date": yesterday,
                        "report_count": 1,
                        "report_type": "Browser",
                        "adu": 10,
                        "crash_hadu": 100.0,
                        "throttle": 0.1
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 6: missing parameters
        self.assertRaises(MissingOrBadArgumentError, crashes.get_daily)
        self.assertRaises(MissingOrBadArgumentError,
                          crashes.get_daily,
                          **{"product": "Firefox"})

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
        self.assertRaises(MissingOrBadArgumentError,
                          crashes.get_paireduuid,
                          **params)

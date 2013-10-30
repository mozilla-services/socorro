# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import random
import unittest
import datetime
from nose.plugins.attrib import attr

from socorro.external import (
    MissingArgumentError,
    BadArgumentError
)
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
        context.database = util.DotDict({
            'database_hostname': 'somewhere',
            'database_port': '8888',
            'database_name': 'somename',
            'database_username': 'someuser',
            'database_password': 'somepasswd',
        })
        context.webapi = util.DotDict()
        context.webapi.platforms = (
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
        self.assertRaises(MissingArgumentError,
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
        self.now = datetimeutil.utc_now()
        yesterday = self.now - datetime.timedelta(days=1)
        uuid = "%%s-%s" % self.now.strftime("%y%m%d")
        yesterday_uuid = "%%s-%s" % yesterday.strftime("%y%m%d")

        build_date = self.now - datetime.timedelta(days=30)
        sunset_date = self.now + datetime.timedelta(days=30)

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
        """ % (self.now, uuid % "a1", "ab1",
               self.now, uuid % "a2", "ab1",
               self.now, uuid % "a3", "ab1",
               self.now, uuid % "b1", "xxx",
               self.now, uuid % "c1", "cb1",
               self.now, yesterday_uuid % "c2", "cb1"))

        # Insert data for frequency test
        cursor.execute("""
            INSERT INTO reports
            (
                id,
                uuid,
                build,
                signature,
                os_name,
                date_processed,
                user_comments
            )
            VALUES
            (1, 'abc', '2012033116', 'js', 'Windows NT', '%(now)s', null),
            (2, 'def', '2012033116', 'js', 'Linux', '%(now)s', 'hello'),
            (3, 'hij', '2012033117', 'js', 'Windows NT', '%(now)s', 'hah'),
            (4, 'klm', '2012033117', 'blah', 'Unknown', '%(now)s', null)
        """ % {"now": self.now})

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
        """ % {"now": self.now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO home_page_graph_build
            (product_version_id, report_date, build_date, report_count, adu)
            VALUES
            (1, '%(now)s', '%(now)s', 5, 200),
            (1, '%(now)s', '%(yesterday)s', 3, 274),
            (2, '%(yesterday)s', '%(now)s', 3, 109)
        """ % {"now": self.now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO crashes_by_user
            (product_version_id, os_short_name, crash_type_id, report_date,
             report_count, adu)
            VALUES
            (1, 'win', 1, '%(now)s', 2, 3000),
            (1, 'win', 2, '%(now)s', 3, 3000),
            (1, 'lin', 2, '%(now)s', 1, 1000),
            (2, 'win', 1, '%(now)s', 5, 2000),
            (3, 'win', 1, '%(now)s', 6, 2000),
            (3, 'win', 2, '%(now)s', 5, 2000),
            (3, 'lin', 1, '%(now)s', 4, 4000),
            (3, 'lin', 2, '%(now)s', 3, 4000),
            (3, 'mac', 1, '%(now)s', 2, 6000),
            (3, 'mac', 2, '%(now)s', 1, 6000)
        """ % {"now": self.now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO crashes_by_user_build
            (product_version_id, os_short_name, crash_type_id, build_date,
             report_date, report_count, adu)
            VALUES
            (1, 'win', 1, '%(now)s', '%(now)s', 1, 2000),
            (1, 'win', 1, '%(yesterday)s', '%(now)s', 2, 3000),
            (1, 'win', 2, '%(yesterday)s', '%(now)s', 3, 1000),
            (1, 'lin', 2, '%(now)s', '%(yesterday)s', 4, 5000),
            (1, 'mac', 1, '%(yesterday)s', '%(now)s', 5, 4000),
            (2, 'lin', 1, '%(yesterday)s', '%(now)s', 1, 1000)
        """ % {"now": self.now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO signatures
            (signature_id, signature, first_build, first_report)
            VALUES
            (1, 'canIhaveYourSignature()', 2008120122, '%(now)s'),
            (2, 'ofCourseYouCan()', 2008120122, '%(now)s')
        """ % {"now": self.now.date()})

        cursor.execute("""
            INSERT INTO exploitability_reports
            (signature_id, signature, report_date,
             null_count, none_count, low_count, medium_count, high_count)
            VALUES
            (1, 'canIhaveYourSignature()', '%(now)s', 0, 1, 2, 3, 4),
            (2, 'ofCourseYouCan()', '%(yesterday)s', 4, 3, 2, 1, 0)
        """ % {"now": self.now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO signatures
            (signature_id, signature)
            VALUES
            (5, 'js')
        """)

        cursor.execute("""
        INSERT INTO
            reports_clean
            (signature_id, date_processed, uuid, release_channel, reason_id,
             process_type, os_version_id, os_name, flash_version_id, domain_id,
             address_id)
        VALUES
            (5, '{now}', 'this-is-suppose-to-be-a-uuid1',
             'Beta', 245, 'Browser', 71, 'Windows', 215, 631719, 11427500),

            (5, '{now}', 'this-is-suppose-to-be-a-uuid2',
             'Beta', 245, 'Browser', 71, 'Windows', 215, 631719, 11427500),

            (5, '{now}', 'this-is-suppose-to-be-a-uuid3',
             'Beta', 245, 'Browser', 71, 'Windows', 215, 631719, 11427500),

            (5, '{yesterday}', 'this-is-suppose-to-be-a-uuid4',
             'Beta', 245, 'Browser', 71, 'Windows', 215, 631719, 11427500),

            (5, '{yesterday}', 'this-is-suppose-to-be-a-uuid5',
             'Beta', 245, 'Browser', 71, 'Windows', 215, 631719, 11427500)
        """.format(now=self.now, yesterday=yesterday))

        self.connection.commit()
        cursor.close()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE reports, home_page_graph_build, home_page_graph,
                     crashes_by_user, crashes_by_user_build, crash_types,
                     process_types, os_names, signatures,
                     product_versions, product_release_channels,
                     release_channels, products, exploitability_reports,
                     reports_clean
            CASCADE
        """)
        self.connection.commit()
        cursor.close()
        super(IntegrationTestCrashes, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get_comments(self):
        crashes = Crashes(config=self.config)
        today = datetimeutil.date_to_string(self.now)

        # Test 1: results
        params = {
            "signature": "js",
        }
        res_expected = {
            "hits": [
                {
                    "email": None,
                    "date_processed": today,
                    "uuid": "def",
                    "user_comments": "hello"
                },
                {
                    "email": None,
                    "date_processed": today,
                    "uuid": "hij",
                    "user_comments": "hah"
                }
            ],
            "total": 2
        }

        res = crashes.get_comments(**params)
        self.assertEqual(res, res_expected)

        # Test 2: no results
        params = {
            "signature": "blah",
        }
        res_expected = {
            "hits": [],
            "total": 0
        }

        res = crashes.get_comments(**params)
        self.assertEqual(res, res_expected)

        # Test 3: missing parameter
        self.assertRaises(MissingArgumentError, crashes.get_comments)

    #--------------------------------------------------------------------------
    def test_get_daily(self):
        crashes = Crashes(config=self.config)
        now = self.now.date()
        today = now.isoformat()
        yesterday = (now - datetime.timedelta(days=1)).isoformat()

        # Test 1: one product, one version (simple version)
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

        # Test 2: one product, several versions, range by build date,
        # simple version
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

        # Test 3: one product, one version, extended fields, complex version
        params = {
            "product": "Firefox",
            "versions": ["11.0"],
            "separated_by": "os"
        }
        res_expected = {
            "hits": {
                "Firefox:11.0:win": {
                    today: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": today,
                        "os": "Windows",
                        "report_count": 50,
                        "adu": 3000,
                        "crash_hadu": 1.667,
                        "throttle": 0.1
                    }
                },
                "Firefox:11.0:lin": {
                    today: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": today,
                        "os": "Linux",
                        "report_count": 10,
                        "adu": 1000,
                        "crash_hadu": 1.0,
                        "throttle": 0.1
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 4: report type filter, complex version
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
                        "report_count": 90,
                        "adu": 12000,
                        "crash_hadu": 0.75,
                        "throttle": 0.1
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 5: extended fields, by build date and with report type,
        # complex version
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
                        "report_count": 10,
                        "adu": 2000,
                        "crash_hadu": 0.5,
                        "throttle": 0.1
                    },
                    yesterday: {
                        "product": "Firefox",
                        "version": "11.0",
                        "date": yesterday,
                        "report_count": 70,
                        "adu": 7000,
                        "crash_hadu": 1.0,
                        "throttle": 0.1
                    }
                },
                "Firefox:12.0": {
                    yesterday: {
                        "product": "Firefox",
                        "version": "12.0",
                        "date": yesterday,
                        "report_count": 10,
                        "adu": 1000,
                        "crash_hadu": 1.0,
                        "throttle": 0.1
                    }
                }
            }
        }

        res = crashes.get_daily(**params)
        self.assertEqual(res, res_expected)

        # Test 6: missing parameters
        self.assertRaises(MissingArgumentError, crashes.get_daily)
        self.assertRaises(MissingArgumentError,
                          crashes.get_daily,
                          **{"product": "Firefox"})

    def test_get_count_by_day(self):
        crashes = Crashes(config=self.config)
        now = datetime.datetime.utcnow()
        yesterday = now - datetime.timedelta(1)
        tomorrow = now + datetime.timedelta(1)

        now = now.strftime("%Y-%m-%d")
        yesterday = yesterday.strftime("%Y-%m-%d")
        tomorrow = tomorrow.strftime("%Y-%m-%d")

        params = {
            'signature': 'js',
            'start_date': now
        }

        expected = {
            'hits': {now: 3},
            'total': 1
        }

        res = crashes.get_count_by_day(**params)
        self.assertEquals(res, expected)

        params = {
            'signature': 'nothing',
            'start_date': now
        }

        expected = {
            'hits': {now: 0},
            'total': 1
        }

        res = crashes.get_count_by_day(**params)
        self.assertEquals(res, expected)

        params = {
            'signature': 'js',
            'start_date': yesterday,
            'end_date': tomorrow
        }

        expected = {
            'hits': {
                yesterday: 2,
                now: 3
            },
            'total': 2
        }

        res = crashes.get_count_by_day(**params)
        self.assertEquals(res, expected)

    #--------------------------------------------------------------------------
    def test_get_frequency(self):
        self.config.webapi = util.DotDict()
        self.config.webapi.platforms = (
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
        yesterday = self.now - datetime.timedelta(days=1)
        uuid = "%%s-%s" % self.now.strftime("%y%m%d")
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
        self.assertRaises(MissingArgumentError,
                          crashes.get_paireduuid,
                          **params)

    #--------------------------------------------------------------------------
    def test_get_exploitibility(self):
        crashes = Crashes(config=self.config)
        today = datetimeutil.date_to_string(self.now.date())
        yesterday_date = (self.now - datetime.timedelta(days=1)).date()
        yesterday = datetimeutil.date_to_string(yesterday_date)

        res_expected = {
            "hits": [
                {
                    "signature": "canIhaveYourSignature()",
                    "report_date": today,
                    "null_count": 0,
                    "none_count": 1,
                    "low_count": 2,
                    "medium_count": 3,
                    "high_count": 4,
                },
                {
                    "signature": "ofCourseYouCan()",
                    "report_date": yesterday,
                    "null_count": 4,
                    "none_count": 3,
                    "low_count": 2,
                    "medium_count": 1,
                    "high_count": 0,
                }
            ],
            "total": 2,
        }

        res = crashes.get_exploitability()
        self.assertEqual(res, res_expected)

    def test_get_exploitibility_with_pagination(self):
        crashes = Crashes(config=self.config)
        today = datetimeutil.date_to_string(self.now.date())
        yesterday_date = (self.now - datetime.timedelta(days=1)).date()
        day_before_yesterday = (self.now - datetime.timedelta(days=2)).date()

        j = 100  # some number so it's not used by other tests or fixtures

        rand = lambda: random.randint(0, 10)
        exploit_values = []
        signature_values = []
        for day in day_before_yesterday, yesterday_date, self.now:
            for i in range(10):
                exploit_values.append(
                    "(%s, 'Signature%s%s', '%s', %s, %s, %s, %s, %s)" % (
                        j + 1, j, i, day, rand(), rand(), rand(), rand(), rand()
                    )
                )
                signature_values.append(
                    "(%s, 'Signature%s%s', %s, '%s')" % (
                        j + 1, j, i, day.strftime('%Y%m%d%H'), day
                    )
                )
                j += 1
        cursor = self.connection.cursor()

        insert = """
        INSERT INTO signatures
            (signature_id, signature, first_build, first_report)
        VALUES
        """
        insert += ',\n'.join(signature_values)
        cursor.execute(insert)

        insert = """
        INSERT INTO exploitability_reports
           (signature_id, signature, report_date,
            null_count, none_count, low_count, medium_count, high_count)
        VALUES
        """
        insert += ',\n'.join(exploit_values)
        cursor.execute(insert)
        self.connection.commit()

        res = crashes.get_exploitability()
        self.assertEqual(len(res['hits']), res['total'])
        self.assertTrue(res['total'] >= 3 * 10)

        res = crashes.get_exploitability(
            start_date=yesterday_date,
            end_date=self.now
        )
        self.assertEqual(len(res['hits']), res['total'])
        self.assertTrue(res['total'] >= 2 * 10)
        self.assertTrue(res['total'] < 3 * 10)

        # passing a `page` without `batch` will yield an error
        self.assertRaises(
            MissingArgumentError,
            crashes.get_exploitability,
            page=2
        )
        # `page` starts on one so anything smaller is bad
        self.assertRaises(
            BadArgumentError,
            crashes.get_exploitability,
            page=0,
            batch=15
        )

        # Note, `page=1` is on number line starting on 1
        res = crashes.get_exploitability(
            page=1,
            batch=15
        )
        self.assertNotEqual(len(res['hits']), res['total'])
        self.assertEqual(len(res['hits']), 15)
        self.assertTrue(res['total'] >= 3 * 10)
        # since it's ordered by `report_date`...
        report_dates = [x['report_date'] for x in res['hits']]
        self.assertEqual(
            report_dates[0],
            datetimeutil.date_to_string(self.now.date())
        )
        self.assertEqual(
            report_dates[-1],
            datetimeutil.date_to_string(yesterday_date)
        )

        res = crashes.get_exploitability(
            page=2,
            batch=5,
            start_date=day_before_yesterday,
            end_date=yesterday_date
        )

        self.assertEqual(len(res['hits']), 5)
        self.assertTrue(res['total'] >= 2 * 10)
        self.assertTrue(res['total'] < 3 * 10)
        report_dates = [x['report_date'] for x in res['hits']]
        self.assertEqual(
            report_dates[0],
            datetimeutil.date_to_string(yesterday_date)
        )

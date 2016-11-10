# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import random
import datetime
from nose.tools import eq_, ok_, assert_raises

from socorro.lib import (
    MissingArgumentError,
    BadArgumentError,
    datetimeutil,
    util,
)
from socorro.external.postgresql.crashes import (
    Crashes,
    AduBySignature,
)
from socorro.unittest.testbase import TestCase
from socorro.external.postgresql.connection_context import ConnectionContext

from unittestbase import PostgreSQLTestCase


# =============================================================================
class TestCrashes(TestCase):
    """Test socorro.external.postgresql.crashes.Crashes class. """

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    def get_instance(self, config=None):
        """Return an instance of Crashes with the config parameter as
        a context or the default one if config is None.
        """
        args = {
            "config": config or self.get_dummy_context()
        }
        return Crashes(**args)

    # -------------------------------------------------------------------------
    def test_prepare_search_params(self):
        """Test Crashes.prepare_search_params()."""
        crashes = self.get_instance()

        # .....................................................................
        # Test 1: no args
        args = {}
        assert_raises(MissingArgumentError,
                      crashes.prepare_search_params,
                      **args)

        # .....................................................................
        # Test 2: a signature
        args = {
            "signature": "something"
        }

        params = crashes.prepare_search_params(**args)
        ok_("signature" in params)
        ok_("terms" in params)
        eq_(params["signature"], "something")
        eq_(params["signature"], params["terms"])

        # .....................................................................
        # Test 3: some OS
        args = {
            "signature": "something",
            "os": ["windows", "linux"]
        }

        params = crashes.prepare_search_params(**args)
        ok_("os" in params)
        eq_(len(params["os"]), 2)
        eq_(params["os"][0], "Windows NT")
        eq_(params["os"][1], "Linux")

        # .....................................................................
        # Test 4: with a plugin
        args = {
            "signature": "something",
            "report_process": "plugin",
            "plugin_terms": ["some", "plugin"],
            "plugin_search_mode": "contains",
        }

        params = crashes.prepare_search_params(**args)
        ok_("plugin_terms" in params)
        eq_(params["plugin_terms"], "%some plugin%")

    def test_get_signatures_with_too_big_date_range(self):
        # This can all be some fake crap because we're testing that
        # the implementation class throws out the request before
        # it gets to doing any queries.
        config = util.DotDict({
            'database_class': ConnectionContext,
            'database_hostname': None,
            'database_port': None,
            'database_name': None,
            'database_username': None,
            'database_password': None,
        })
        crashes = Crashes(config=config)
        params = {}
        params['duration'] = 31 * 24  # 31 days
        assert_raises(
            BadArgumentError,
            crashes.get_signatures,
            **params
        )


# =============================================================================
class IntegrationTestCrashes(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crashes.Crashes class. """

    # -------------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestCrashes, cls).setUpClass()

        cursor = cls.connection.cursor()

        cls.now = datetimeutil.utc_now()
        yesterday = cls.now - datetime.timedelta(days=1)

        build_date = cls.now - datetime.timedelta(days=30)
        sunset_date = cls.now + datetime.timedelta(days=30)

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
                user_comments,
                product,
                version,
                release_channel
            )
            VALUES
            (
                1,
                'abc',
                '2012033116',
                'js',
                'Windows NT',
                '%(now)s',
                null,
                'Firefox',
                '11.0',
                'Nightly'
            ),
            (
                2,
                'def',
                '2012033116',
                'js',
                'Linux',
                '%(now)s',
                'hello',
                'Firefox',
                '11.0',
                'Nightly'
            ),
            (
                3,
                'hij',
                '2012033117',
                'js',
                'Windows NT',
                '%(now)s',
                'hah',
                'Firefox',
                '11.0',
                'Nightly'
            ),
            (
                4,
                'klm',
                '2012033117',
                'blah',
                'Unknown',
                '%(now)s',
                null,
                'Firefox',
                '14.0b1',
                'Beta'
            ),
            (
                5,
                'nop',
                '2012033117',
                'cool_sig',
                'Unknown',
                '%(now)s',
                'hi!',
                'Firefox',
                '14.0b',
                'Beta'
            ),
            (
                6,
                'qrs',
                '2012033117',
                'cool_sig',
                'Linux',
                '%(now)s',
                'meow',
                'WaterWolf',
                '2.0b',
                'Beta'
            )
        """ % {"now": cls.now})

        # Insert data for daily crashes test

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, release_name)
            VALUES
            (
                'Firefox',
                1,
                'firefox'
            ),
            (
                'WaterWolf',
                2,
                'WaterWolf'
            );
        """)

        cursor.execute("""
            INSERT INTO product_versions
            (product_version_id, product_name, major_version, release_version,
             version_string, version_sort, build_date, sunset_date,
             featured_version, build_type, is_rapid_beta, rapid_beta_id)
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
                'Nightly',
                False,
                NULL
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
                'Nightly',
                False,
                NULL
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
                'Nightly',
                False,
                NULL
            ),
            (
                4,
                'Firefox',
                '14.0b321241',
                '14.0b',
                '14.0b',
                '00000013000',
                '%(build_date)s',
                '%(sunset_date)s',
                'f',
                'Beta',
                True,
                3
            ),
            (
                5,
                'Firefox',
                '14.0b1',
                '14.0b',
                '14.0b1',
                '00000013000',
                '%(build_date)s',
                '%(sunset_date)s',
                'f',
                'Beta',
                False,
                4
            ),
            (
                6,
                'WaterWolf',
                '2.0b',
                '2.0b',
                '2.0b',
                '00000013000',
                '%(build_date)s',
                '%(sunset_date)s',
                'f',
                'Nightly',
                True,
                NULL
            );
        """ % {"build_date": build_date, "sunset_date": sunset_date})

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1),
            ('Beta', 2)
        """)

        cursor.execute("""
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            ('Firefox', 'Nightly', 0.1),
            ('Firefox', 'Beta', 1.0)
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
        """ % {"now": cls.now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO home_page_graph_build
            (product_version_id, report_date, build_date, report_count, adu)
            VALUES
            (1, '%(now)s', '%(now)s', 5, 200),
            (1, '%(now)s', '%(yesterday)s', 3, 274),
            (2, '%(yesterday)s', '%(now)s', 3, 109)
        """ % {"now": cls.now, "yesterday": yesterday})

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
        """ % {"now": cls.now, "yesterday": yesterday})

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
        """ % {"now": cls.now, "yesterday": yesterday})

        cursor.execute("""
            INSERT INTO signatures
            (signature_id, signature, first_build, first_report)
            VALUES
            (1, 'canIhaveYourSignature()', 2008120122, '%(now)s'),
            (2, 'ofCourseYouCan()', 2008120122, '%(now)s')
        """ % {"now": cls.now.date()})

        # Remember your product versions...
        #   1) Firefox:11.0
        #   2) Firefox:12.0
        #   4) Firefox:14.0b
        #   6) WaterWolf:2.0b
        cursor.execute("""
            INSERT INTO exploitability_reports
            (signature_id, product_version_id, signature, report_date,
             null_count, none_count, low_count, medium_count, high_count)
            VALUES
            (1, 1, 'canIhaveYourSignature()', '%(now)s', 0, 1, 2, 3, 4),
            (2, 1, 'ofCourseYouCan()', '%(yesterday)s', 4, 3, 2, 1, 0),
            (2, 4, 'ofCourseYouCan()', '%(now)s', 1, 4, 0, 1, 0),
            (2, 6, 'canIhaveYourSignature()', '%(yesterday)s', 2, 2, 2, 2, 2)
        """ % {"now": cls.now, "yesterday": yesterday})

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
        """.format(now=cls.now, yesterday=yesterday))

        cursor.execute("""
            INSERT INTO crash_adu_by_build_signature
            (signature_id, signature, adu_date, build_date, buildid,
             crash_count, adu_count, os_name, channel, product_name)
            VALUES
            (1, 'canIhaveYourSignature()', '{yesterday}', '2014-03-01',
             '201403010101', 3, 1023, 'Mac OS X', 'release', 'WaterWolf'),
            (1, 'canIhaveYourSignature()', '{yesterday}', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf'),
            (1, 'canIhaveYourSignature()', '2014-01-01', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf'),
            (2, 'youMayNotHaveMySignature()', '{yesterday}', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf'),
            (2, 'youMayNotHaveMySignature()', '{yesterday}', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf')
        """.format(yesterday=yesterday))

        cls.connection.commit()
        cursor.close()

    # -------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        """Clean up the database, delete tables and functions. """
        cursor = cls.connection.cursor()
        cursor.execute("""
            TRUNCATE reports, home_page_graph_build, home_page_graph,
                     crashes_by_user, crashes_by_user_build, crash_types,
                     process_types, os_names, signatures,
                     product_versions, product_release_channels,
                     release_channels, products, exploitability_reports,
                     reports_clean, crash_adu_by_build_signature
            CASCADE
        """)
        cls.connection.commit()
        cursor.close()
        super(IntegrationTestCrashes, cls).tearDownClass()

    # -------------------------------------------------------------------------
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
        eq_(res, res_expected)

        # Test 2: no results
        params = {
            "signature": "blah",
        }
        res_expected = {
            "hits": [],
            "total": 0
        }

        res = crashes.get_comments(**params)
        eq_(res, res_expected)

        # Test 3: missing parameter
        assert_raises(MissingArgumentError, crashes.get_comments)

        # Test a valid rapid beta versions
        params = {
            "signature": "cool_sig",
            "products": "Firefox",
            "versions": "Firefox:14.0b",
        }
        res_expected = {
            'hits': [
                {
                    'email': None,
                    'date_processed': today,
                    'uuid': 'nop',
                    'user_comments': 'hi!'
                }
            ],
            'total': 1
        }

        res = crashes.get_comments(**params)
        eq_(res, res_expected)

        # Test an invalid rapid beta versions
        params = {
            "signature": "cool_sig",
            "versions": "WaterWolf:2.0b",
        }
        res_expected = {
            'hits': [
                {
                    'email': None,
                    'date_processed': today,
                    'uuid': 'qrs',
                    'user_comments': 'meow'
                }
            ],
            'total': 1
        }

        res = crashes.get_comments(**params)
        eq_(res, res_expected)

        # use pagination
        params = {
            "signature": "cool_sig",
            "result_number": 1,
            "result_offset": 0,
        }
        params['result_number'] = 1
        params['result_offset'] = 0
        res = crashes.get_comments(**params)
        eq_(len(res['hits']), 1)
        eq_(res['total'], 2)

    # -------------------------------------------------------------------------
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
        eq_(res, res_expected)

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
        eq_(res, res_expected)

        # Test 3: report type filter, complex version
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
        eq_(res, res_expected)

        # Test 4: extended fields, by build date and with report type,
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
        eq_(res, res_expected)

        # Test 5: missing parameters
        assert_raises(MissingArgumentError, crashes.get_daily)
        assert_raises(MissingArgumentError,
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
        eq_(res, expected)

        params = {
            'signature': 'nothing',
            'start_date': now
        }

        expected = {
            'hits': {now: 0},
            'total': 1
        }

        res = crashes.get_count_by_day(**params)
        eq_(res, expected)

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
        eq_(res, expected)

    # -------------------------------------------------------------------------
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

        # .....................................................................
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

        eq_(res, res_expected)

        # .....................................................................
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

        eq_(res, res_expected)

        # .....................................................................
        # Verify that it is not possible to break the query.
        params = {
            "signature": "sig'"
        }
        res = crashes.get_frequency(**params)
        eq_(res["total"], 0)

    # -------------------------------------------------------------------------
    def test_get_exploitibility(self):
        crashes = Crashes(config=self.config)

        res_expected = {
            "hits": [
                {
                    "signature": "canIhaveYourSignature()",
                    "null_count": 2,
                    "none_count": 3,
                    "low_count": 4,
                    "medium_count": 5,
                    "high_count": 6
                },
                {
                    "signature": "ofCourseYouCan()",
                    "null_count": 5,
                    "none_count": 7,
                    "low_count": 2,
                    "medium_count": 2,
                    "high_count": 0
                }
            ],
            "total": 2,
        }

        res = crashes.get_exploitability()
        eq_(res, res_expected)

    def test_get_exploitibility_by_report_date(self):
        crashes = Crashes(config=self.config)
        yesterday_date = (self.now - datetime.timedelta(days=1)).date()
        yesterday = datetimeutil.date_to_string(yesterday_date)

        res_expected = {
            "hits": [
                {
                    "signature": "canIhaveYourSignature()",
                    "null_count": 2,
                    "none_count": 2,
                    "low_count": 2,
                    "medium_count": 2,
                    "high_count": 2
                },
                {
                    "signature": "ofCourseYouCan()",
                    "null_count": 4,
                    "none_count": 3,
                    "low_count": 2,
                    "medium_count": 1,
                    "high_count": 0
                }
            ],
            "total": 2,
        }

        res = crashes.get_exploitability(
            start_date=yesterday,
            end_date=yesterday
        )
        eq_(res, res_expected)

    def test_get_exploitibility_by_product(self):
        crashes = Crashes(config=self.config)

        res_expected = {
            "hits": [
                {
                    "signature": "canIhaveYourSignature()",
                    "null_count": 0,
                    "none_count": 1,
                    "low_count": 2,
                    "medium_count": 3,
                    "high_count": 4
                },
                {
                    "signature": "ofCourseYouCan()",
                    "null_count": 5,
                    "none_count": 7,
                    "low_count": 2,
                    "medium_count": 2,
                    "high_count": 0
                },

            ],
            "total": 2,
        }
        res = crashes.get_exploitability(product='Firefox')
        eq_(res, res_expected)

    def test_get_exploitibility_by_product_and_version(self):
        crashes = Crashes(config=self.config)

        res_expected = {
            "hits": [
                {
                    "signature": "ofCourseYouCan()",
                    "null_count": 1,
                    "none_count": 4,
                    "low_count": 0,
                    "medium_count": 1,
                    "high_count": 0
                }
            ],
            "total": 1,
        }

        res = crashes.get_exploitability(product='Firefox', version='14.0b')
        eq_(res, res_expected)

    def test_get_exploitibility_with_pagination(self):
        crashes = Crashes(config=self.config)
        yesterday_date = (self.now - datetime.timedelta(days=1)).date()
        day_before_yesterday = (self.now - datetime.timedelta(days=2)).date()

        j = 100  # some number so it's not used by other tests or fixtures

        def rand():
            return random.randint(0, 10)

        exploit_values = []
        signature_values = []
        for day in day_before_yesterday, yesterday_date, self.now:
            for i in range(10):
                exploit_values.append(
                    "(%s, 3, 'Signature%s%s', '%s', %s, %s, %s, %s, %s)" % (
                        j + 1, j, i, day,
                        rand(), rand(), rand(), rand(), rand()
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
           (signature_id, product_version_id, signature, report_date,
            null_count, none_count, low_count, medium_count, high_count)
        VALUES
        """
        insert += ',\n'.join(exploit_values)
        cursor.execute(insert)
        self.connection.commit()

        res = crashes.get_exploitability()
        eq_(len(res['hits']), res['total'])
        ok_(res['total'] >= 3 * 10)

        res = crashes.get_exploitability(
            start_date=yesterday_date,
            end_date=self.now
        )
        eq_(len(res['hits']), res['total'])
        ok_(res['total'] >= 2 * 10)
        ok_(res['total'] < 3 * 10)

        # passing a `page` without `batch` will yield an error
        assert_raises(
            MissingArgumentError,
            crashes.get_exploitability,
            page=2
        )
        # `page` starts on one so anything smaller is bad
        assert_raises(
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
        eq_(len(res['hits']), 15)
        ok_(res['total'] >= 3 * 10)
        # since it's ordered by "medium + high"...

        med_or_highs = [
            x['medium_count'] + x['high_count']
            for x in res['hits']
        ]
        eq_(
            med_or_highs[0],
            max(med_or_highs)
        )
        eq_(
            med_or_highs[-1],
            min(med_or_highs)
        )

    # -------------------------------------------------------------------------
    def test_get_adu_by_signature(self):
        adu_by_signature = AduBySignature(config=self.config)

        signature = "canIhaveYourSignature()"
        channel = "release"
        yesterday_date = (self.now - datetime.timedelta(days=1)).date()
        yesterday = datetimeutil.date_to_string(yesterday_date)

        res_expected = {
            "hits": [
                {
                    "product_name": "WaterWolf",
                    "signature": signature,
                    "adu_date": yesterday,
                    "build_date": "2014-03-01",
                    "buildid": '201403010101',
                    "crash_count": 3,
                    "adu_count": 1023,
                    "os_name": "Mac OS X",
                    "channel": channel,
                },
                {
                    "product_name": "WaterWolf",
                    "signature": signature,
                    "adu_date": yesterday,
                    "build_date": "2014-04-01",
                    "buildid": '201404010101',
                    "crash_count": 4,
                    "adu_count": 1024,
                    "os_name": "Windows NT",
                    "channel": channel,
                },
            ],
            "total": 2,
        }

        res = adu_by_signature.get(
            product_name="WaterWolf",
            start_date=yesterday,
            end_date=yesterday,
            signature=signature,
            channel=channel,
        )
        eq_(res, res_expected)

        assert_raises(
            BadArgumentError,
            adu_by_signature.get,
            start_date=(yesterday_date - datetime.timedelta(days=366)),
            end_date=yesterday,
            signature=signature,
            channel=channel
        )

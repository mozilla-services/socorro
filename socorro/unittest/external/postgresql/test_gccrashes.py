# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr
from nose.tools import eq_, assert_raises

from socorro.external import MissingArgumentError

from socorro.external.postgresql.gccrashes import GCCrashes
from socorro.lib import datetimeutil, util
from socorro.unittest.testbase import TestCase

from unittestbase import PostgreSQLTestCase


#==============================================================================
class TestGCCrashes(TestCase):
    """Test socorro.external.postgresql.gccrashes.GCCrashes class. """

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
        return context


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

        self.now = datetimeutil.utc_now()
        yesterday = self.now - datetime.timedelta(days=1)
        day_before_yesterday = self.now - datetime.timedelta(days=2)

        build_date = self.now - datetime.timedelta(days=30)
        sunset_date = self.now + datetime.timedelta(days=30)

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, release_name)
            VALUES
            (
                'WaterWolf',
                1,
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
                'WaterWolf',
                '1.0',
                '1.0',
                '1.0',
                '10000011000',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly',
                False,
                NULL
            ),
            (
                2,
                'WaterWolf',
                '2.0',
                '2.0',
                '2.0',
                '10000012000',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly',
                False,
                NULL
            );
        """ % {"build_date": build_date, "sunset_date": sunset_date})

        cursor.execute("""
            INSERT INTO gccrashes (report_date, product_version_id, build,
                                   gc_count_madu)
            VALUES
            ('%s', '%s', '%s', '%s'),
            ('%s', '%s', '%s', '%s'),
            ('%s', '%s', '%s', '%s');
        """ % (yesterday, "1", "10000011000", "42",
               day_before_yesterday, "1", "10000011000", "42",
               yesterday, "2", "10000012000", "24"))

        self.connection.commit()
        cursor.close()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE gccrashes, reports_clean, products
            CASCADE
        """)
        self.connection.commit()
        cursor.close()
        super(IntegrationTestCrashes, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get_gccrashes(self):
        gccrashes = GCCrashes(config=self.config)

        # Test 1: results
        params = {
            "product": "WaterWolf",
            "version": "1.0"
        }
        res_expected = {
            "hits": [
                (
                    "10000011000",
                    84
                )
            ],
            "total": 1
        }

        res = gccrashes.get(**params)
        eq_(res, res_expected)

        # Test 2: no results
        params = {
            "product": "blah",
            "version": "blah",
        }
        res_expected = {
            "hits": [],
            "total": 0
        }

        res = gccrashes.get(**params)
        eq_(res, res_expected)

        # Test 3: missing parameter
        assert_raises(MissingArgumentError, gccrashes.get)

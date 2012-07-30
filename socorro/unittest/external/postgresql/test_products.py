# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external.postgresql.products import Products
from socorro.lib import datetimeutil

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestProducts(PostgreSQLTestCase):
    """Test socorro.external.postgresql.products.Products class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate product_info table with fake data """
        super(IntegrationTestProducts, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        now = datetimeutil.utc_now().date()
        # throttle in product_release_channels
        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name)
            VALUES
            (
                '%s',
                %d,
                '%s',
                '%s'
            ),
            (
                '%s',
                %d,
                '%s',
                '%s'
            ),
            (
                '%s',
                %d,
                '%s',
                '%s'
            );
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            (
                'Release', 1
            );
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            (
                'Firefox', 'Release', '0.1'
            ),
            (
                'Fennec', 'Release', '0.1'
            ),
            (
                'Thunderbird', 'Release', '0.1'
            );
            INSERT INTO product_versions
            (product_name, major_version, release_version, version_string,
             build_date, sunset_date, featured_version, build_type)
            VALUES
            (
                'Firefox',
                '8.0',
                '8.0',
                '8.0',
                '%s',
                '%s',
                False,
                'Release'
            ),
            (
                'Fennec',
                '11.0',
                '11.0',
                '11.0.1',
                '%s',
                '%s',
                False,
                'Release'
            ),
            (
                'Thunderbird',
                '10.0',
                '10.0',
                '10.0.2b',
                '%s',
                '%s',
                False,
                'Release'
            );
        """ % ("Firefox", 1, '8.0', "firefox",
               "Fennec", 3, '11.0', "mobile",
               "Thunderbird", 2, '10.0', "thunderbird",
               now, now,
               now, now,
               now, now))

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE products, product_version_builds, product_versions,
                     product_release_channels, release_channels,
                     product_versions
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestProducts, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        products = Products(config=self.config)
        now = datetimeutil.utc_now().date()
        now_str = datetimeutil.date_to_string(now)

        #......................................................................
        # Test 1: find one exact match for one product and one version
        params = {
            "versions": "Firefox:8.0"
        }
        res = products.get(**params)
        res_expected = {
            "hits": [
                {
                    "product": "Firefox",
                    "version": "8.0",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 10.0,
                    "has_builds": False
                 }
            ],
            "total": 1
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: Find two different products with their correct verions
        params = {
            "versions": ["Firefox:8.0", "Thunderbird:10.0.2b"]
        }
        res = products.get(**params)
        res_expected = {
            "hits": [
                {
                    "product": "Firefox",
                    "version": "8.0",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 10.0,
                    "has_builds": False
                 },
                 {
                    "product": "Thunderbird",
                    "version": "10.0.2b",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 10.0,
                    "has_builds": False
                 }
            ],
            "total": 2
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 3: empty result, no products:version found
        params = {
            "versions": "Firefox:14.0"
        }
        res = products.get(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 4: Test products list is returned with no parameters
        params = {}
        res = products.get(**params)
        res_expected = {
                "hits": [
                    {
                        "product_name": "Firefox",
                        "release_name": "firefox",
                        "sort": 1,
                        "default_version": "8.0",
                        "rapid_release_version": "8.0"
                    },
                    {
                        "product_name": "Thunderbird",
                        "release_name": "thunderbird",
                        "sort": 2,
                        "default_version": "10.0.2b",
                        "rapid_release_version": "10.0"
                    },
                    {
                        "product_name": "Fennec",
                        "release_name": "mobile",
                        "sort": 3,
                        "default_version": "11.0.1",
                        "rapid_release_version": "11.0"
                    }
                ],
                "total": 3
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 5: An unvalid versions list is passed, all versions are returned
        params = {
            'versions': [1]
        }
        res = products.get(**params)
        res_expected = {
            "hits": [
                {
                    "product": "Fennec",
                    "version": "11.0.1",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 10.0,
                    "has_builds": False
                },
                {
                    "product": "Firefox",
                    "version": "8.0",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 10.0,
                    "has_builds": False
                 },
                 {
                    "product": "Thunderbird",
                    "version": "10.0.2b",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 10.0,
                    "has_builds": False
                 }
            ],
            "total": 3
        }

        self.assertEqual(res, res_expected)

    def test_get_default_version(self):
        products = Products(config=self.config)

        # Test 1: default versions for all existing products
        res = products.get_default_version()
        res_expected = {
            "hits": {
                "Firefox": "8.0",
                "Thunderbird": "10.0.2b",
                "Fennec": "11.0.1",
            }
        }

        self.assertEqual(res, res_expected)

        # Test 2: default version for one product
        params = {"products": "Firefox"}
        res = products.get_default_version(**params)
        res_expected = {
            "hits": {
                "Firefox": "8.0"
            }
        }

        self.assertEqual(res, res_expected)

        # Test 3: default version for two products
        params = {"products": ["Firefox", "Thunderbird"]}
        res = products.get_default_version(**params)
        res_expected = {
            "hits": {
                "Firefox": "8.0",
                "Thunderbird": "10.0.2b"
            }
        }

        self.assertEqual(res, res_expected)

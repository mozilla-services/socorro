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
        self.now = datetimeutil.utc_now()
        now = self.now.date()
        lastweek = now - datetime.timedelta(days=7)

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name)
            VALUES
            (
                'Firefox',
                1,
                '8.0',
                'firefox'
            ),
            (
                'Fennec',
                3,
                '11.0',
                'mobile'
            ),
            (
                'Thunderbird',
                2,
                '10.0',
                'thunderbird'
            );
        """)

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            (
                'Release', 1
            ),
            (
                'Beta', 2
            );
        """)

        cursor.execute("""
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
                'Fennec', 'Beta', '1.0'
            ),
            (
                'Thunderbird', 'Release', '0.1'
            );
        """)

        # Insert versions, contains an expired version
        cursor.execute("""
            INSERT INTO product_versions
            (product_name, major_version, release_version, version_string,
             build_date, sunset_date, featured_version, build_type,
             version_sort)
            VALUES
            (
                'Firefox',
                '8.0',
                '8.0',
                '8.0',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '0008000'
            ),
            (
                'Firefox',
                '9.0',
                '9.0',
                '9.0',
                '%(lastweek)s',
                '%(lastweek)s',
                False,
                'Nightly',
                '0009000'
            ),
            (
                'Fennec',
                '11.0',
                '11.0',
                '11.0.1',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '0011001'
            ),
            (
                'Fennec',
                '12.0',
                '12.0',
                '12.0b1',
                '%(now)s',
                '%(now)s',
                False,
                'Beta',
                '00120b1'
            ),
            (
                'Thunderbird',
                '10.0',
                '10.0',
                '10.0.2b',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '001002b'
            );
        """ % {'now': now, 'lastweek': lastweek})

        # insert bixie errors
        cursor.execute("""
            INSERT INTO bixie.raw_product_releases
            (id, product_name, version, build, build_type, platform,
             repository, stability)
            VALUES
            (
                1,
                'EmailApp',
                '0.1',
                1234567890,
                'Release',
                'mobile',
                'repo',
                'stable'
            ),
            (
                2,
                'EmailApp',
                '0.2',
                1234567890,
                'Beta',
                'mobile',
                'repo',
                'stable'
            ),
            (
                3,
                'ClockOClock',
                '1.0.18',
                1234567890,
                'Release',
                'mobile',
                'repo',
                'stable'
            )
        """)

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE products, product_version_builds, product_versions,
                     product_release_channels, release_channels,
                     product_versions,
                     bixie.raw_product_releases
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestProducts, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        products = Products(config=self.config)
        now = self.now.date()
        lastweek = now - datetime.timedelta(days=7)
        now_str = datetimeutil.date_to_string(now)
        lastweek_str = datetimeutil.date_to_string(lastweek)

        #......................................................................
        # Test 1: find one exact match for one product and one version
        params = {
            "versions": "Firefox:8.0"
        }
        res = products.get(**params)
        res_expected = {
            "hits": [
                {
                    "is_featured": False,
                    "version": "8.0",
                    "throttle": 10.0,
                    "start_date": now_str,
                    "end_date": now_str,
                    "has_builds": False,
                    "product": "Firefox",
                    "build_type": "Release"
                 }
            ],
            "total": 1
        }

        self.assertEqual(
            sorted(res['hits'][0]),
            sorted(res_expected['hits'][0])
        )

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

        self.assertEqual(
            sorted(res['hits'][0]),
            sorted(res_expected['hits'][0])
        )

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
        # Note that the expired version is not returned
        params = {}
        res = products.get(**params)
        res_expected = {
                "products": ["Firefox", "Thunderbird", "Fennec"],
                "hits": {
                    "Firefox": [
                        {
                            "product": "Firefox",
                            "version": "8.0",
                            "start_date": now_str,
                            "end_date": now_str,
                            "throttle": 10.00,
                            "featured": False,
                            "release": "Release",
                            "has_builds": False
                        }
                    ],
                    "Thunderbird": [
                        {
                            "product": "Thunderbird",
                            "version": "10.0.2b",
                            "start_date": now_str,
                            "end_date": now_str,
                            "throttle": 10.00,
                            "featured": False,
                            "release": "Release",
                            "has_builds": False,
                        }
                    ],
                    "Fennec": [
                        {
                            "product": "Fennec",
                            "version": "12.0b1",
                            "start_date": now_str,
                            "end_date": now_str,
                            "throttle": 100.00,
                            "featured": False,
                            "release": "Beta",
                            "has_builds": False
                        },
                        {
                            "product": "Fennec",
                            "version": "11.0.1",
                            "start_date": now_str,
                            "end_date": now_str,
                            "throttle": 10.00,
                            "featured": False,
                            "release": "Release",
                            "has_builds": False
                        }
                    ]
                },
                "total": 4
        }

        self.assertEqual(res['total'], res_expected['total'])
        self.assertEqual(
            sorted(res['products']),
            sorted(res_expected['products'])
        )
        self.assertEqual(sorted(res['hits']), sorted(res_expected['hits']))
        for product in sorted(res['hits'].keys()):
            self.assertEqual(
                sorted(res['hits'][product][0]),
                sorted(res_expected['hits'][product][0])
            )

        # test returned order of versions
        assert len(res['hits']['Fennec']) == 2
        self.assertEqual(res['hits']['Fennec'][0]['version'], '12.0b1')
        self.assertEqual(res['hits']['Fennec'][1]['version'], '11.0.1')

        #......................................................................
        # Test 5: An invalid versions list is passed, all versions are returned
        params = {
            'versions': [1]
        }
        res = products.get(**params)
        self.assertEqual(res['total'], 4)

    def test_get_webapp_products(self):
        api = Products(config=self.config)

        res = api.get(type='webapp')
        res_expected = {
            'products': ['ClockOClock', 'EmailApp'],
            'hits': {
                'EmailApp': [
                    {
                        "product": "EmailApp",
                        "version": "0.2",
                        "start_date": None,
                        "end_date": None,
                        "throttle": 1.0,
                        "featured": False,
                        "release": "Beta",
                        "has_builds": False
                    },
                    {
                        "product": "EmailApp",
                        "version": "0.1",
                        "start_date": None,
                        "end_date": None,
                        "throttle": 1.0,
                        "featured": False,
                        "release": "Release",
                        "has_builds": False
                    }
                ],
                'ClockOClock': [
                    {
                        "product": "ClockOClock",
                        "version": "1.0.18",
                        "start_date": None,
                        "end_date": None,
                        "throttle": 1.0,
                        "featured": False,
                        "release": "Release",
                        "has_builds": False
                    }
                ]
            },
            'total': 3
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
                "Fennec": "12.0b1",
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

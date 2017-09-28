# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.external.postgresql.products import ProductVersions
from socorro.lib import datetimeutil
from socorro.unittest.external.postgresql.unittestbase import PostgreSQLTestCase


class IntegrationTestProductVersionsBase(PostgreSQLTestCase):

    @classmethod
    def setUpClass(cls):
        super(IntegrationTestProductVersionsBase, cls).setUpClass()

        cls.truncate()

        cursor = cls.connection.cursor()

        # Insert data
        cls.now = datetimeutil.utc_now()
        now = cls.now.date()
        lastweek = now - datetime.timedelta(days=7)
        nextweek = now + datetime.timedelta(days=7)

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
                'Nightly', 1
            ),
            (
                'Release', 3
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
                'Firefox', 'Nightly', '1.0'
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
             version_sort, has_builds, is_rapid_beta)
            VALUES
            (
                'Firefox',
                '8.0',
                '8.0',
                '8.0',
                '%(lastweek)s',
                '%(lastweek)s',
                False,
                'Release',
                '0008000',
                false,
                false
            ),
            (
                'Firefox',
                '9.0',
                '9.0',
                '9.0',
                '%(now)s',
                '%(nextweek)s',
                True,
                'Nightly',
                '0009000',
                true,
                false
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
                '0011001',
                false,
                false
            ),
            (
                'Fennec',
                '12.0',
                '12.0',
                '12.0b1',
                '%(now)s',
                '%(nextweek)s',
                False,
                'Beta',
                '00120b1',
                true,
                false
            ),
            (
                'Thunderbird',
                '10.0',
                '10.0',
                '10.0.2b',
                '%(now)s',
                '%(nextweek)s',
                False,
                'Release',
                '001002b',
                false,
                true
            );
        """ % {'now': now, 'lastweek': lastweek, 'nextweek': nextweek})

        cls.connection.commit()

    @classmethod
    def tearDownClass(cls):
        """ Cleanup the database, delete tables and functions """
        cls.truncate()
        super(IntegrationTestProductVersionsBase, cls).tearDownClass()

    @classmethod
    def truncate(cls):
        cursor = cls.connection.cursor()
        cursor.execute("""
            TRUNCATE products, product_version_builds, product_versions,
                     product_release_channels, release_channels,
                     product_versions
            CASCADE
        """)
        cls.connection.commit()


class IntegrationTestProductVersions(IntegrationTestProductVersionsBase):
    """Test socorro.external.postgresql.products.ProductVersions class. """

    def test_get_basic(self):
        productversions = ProductVersions(config=self.config)
        now = self.now.date()
        lastweek = now - datetime.timedelta(days=7)

        # Find one exact match for one product and one version
        params = {
            "product": "Firefox",
            "version": "8.0",
        }
        res = productversions.get(**params)
        res_expected = {
            "hits": [{
                "is_featured": False,
                "version": "8.0",
                "throttle": 10.0,
                "start_date": lastweek,
                "end_date": lastweek,
                "has_builds": False,
                "product": "Firefox",
                "build_type": "Release",
                "is_rapid_beta": False,
            }],
            "total": 1
        }

        assert res['total'] == res_expected['total']
        assert sorted(res['hits'][0]) == sorted(res_expected['hits'][0])
        assert res['hits'] == res_expected['hits']

    def test_get_with_one_product_multiple_versions(self):
        productversions = ProductVersions(config=self.config)
        now = self.now.date()
        nextweek = now + datetime.timedelta(days=7)

        params = {
            "product": "Fennec",
            "version": ["11.0.1", "12.0b1"],
        }
        res = productversions.get(**params)
        res_expected = {
            "hits": [
                {
                    "is_featured": False,
                    "version": "12.0b1",
                    "throttle": 100.0,
                    "start_date": now,
                    "end_date": nextweek,
                    "has_builds": True,
                    "product": "Fennec",
                    "build_type": "Beta",
                    "is_rapid_beta": False,
                },
                {
                    "is_featured": False,
                    "version": "11.0.1",
                    "throttle": 10.0,
                    "start_date": now,
                    "end_date": now,
                    "has_builds": False,
                    "product": "Fennec",
                    "build_type": "Release",
                    "is_rapid_beta": False,
                }
            ],
            "total": 2
        }

        assert res['total'] == res_expected['total']
        assert sorted(res['hits'][0]) == sorted(res_expected['hits'][0])
        assert res['hits'][0] == res_expected['hits'][0]
        assert res['hits'][1] == res_expected['hits'][1]

    def test_get_no_parameter_returning_all(self):
        productversions = ProductVersions(config=self.config)
        now = self.now.date()
        lastweek = now - datetime.timedelta(days=7)
        nextweek = now + datetime.timedelta(days=7)

        # Test products list is returned with no parameters
        # Note that the expired version is not returned
        res = productversions.get()
        res_expected = {
            "hits":
                [
                    {
                        "product": "Firefox",
                        "version": "9.0",
                        "start_date": now,
                        "end_date": nextweek,
                        "throttle": 100.00,
                        "is_featured": True,
                        "build_type": "Nightly",
                        "has_builds": True,
                        "is_rapid_beta": False,
                    },
                    {
                        "product": "Firefox",
                        "version": "8.0",
                        "start_date": lastweek,
                        "end_date": lastweek,
                        "throttle": 10.00,
                        "is_featured": False,
                        "build_type": "Release",
                        "has_builds": False,
                        "is_rapid_beta": False,
                    },
                    {
                        "product": "Thunderbird",
                        "version": "10.0.2b",
                        "start_date": now,
                        "end_date": nextweek,
                        "throttle": 10.00,
                        "is_featured": False,
                        "build_type": "Release",
                        "has_builds": False,
                        "is_rapid_beta": True,
                    },
                    {
                        "product": "Fennec",
                        "version": "12.0b1",
                        "start_date": now,
                        "end_date": nextweek,
                        "throttle": 100.00,
                        "is_featured": False,
                        "build_type": "Beta",
                        "has_builds": True,
                        "is_rapid_beta": False,
                    },
                    {
                        "product": "Fennec",
                        "version": "11.0.1",
                        "start_date": now,
                        "end_date": now,
                        "throttle": 10.00,
                        "is_featured": False,
                        "build_type": "Release",
                        "has_builds": False,
                        "is_rapid_beta": False,

                    }
                ],
            "total": 5
        }

        assert res['total'] == res_expected['total']
        assert res['total'] == len(res['hits'])
        # same keys
        keys = set(res['hits'][0].keys())
        expected_keys = set(res_expected['hits'][0].keys())
        assert keys == expected_keys
        assert res['hits'] == res_expected['hits']

    def test_filter_by_featured(self):
        productversions = ProductVersions(config=self.config)

        res = productversions.get(is_featured=True)
        assert len(res['hits']) == 1
        assert res['total'] == 1
        assert all(x['is_featured'] for x in res['hits'])
        res = productversions.get(is_featured=False)
        assert res['total'] == 4
        assert len(res['hits']) == 4
        assert all(not x['is_featured'] for x in res['hits'])

    def test_filter_by_start_date(self):
        productversions = ProductVersions(config=self.config)
        now = self.now.date()

        res = productversions.get(start_date='>=' + now.isoformat())
        assert res['total'] == 4
        res = productversions.get(start_date='<' + now.isoformat())
        assert res['total'] == 1

    def test_filter_by_end_date(self):
        productversions = ProductVersions(config=self.config)
        now = self.now.date()
        nextweek = now + datetime.timedelta(days=7)

        res = productversions.get(end_date='=' + nextweek.isoformat())
        assert res['total'] == 3
        for hit in res['hits']:
            assert hit['end_date'] == nextweek

    def test_filter_by_active(self):
        productversions = ProductVersions(config=self.config)
        now = self.now.date()
        nextweek = now + datetime.timedelta(days=7)

        res = active_results = productversions.get(active=True)
        assert res['total'] == 4
        res_expected = {
            "hits":
                [
                    {
                        "product": "Firefox",
                        "version": "9.0",
                        "start_date": now,
                        "end_date": nextweek,
                        "throttle": 100.00,
                        "is_featured": True,
                        "build_type": "Nightly",
                        "has_builds": True,
                        "is_rapid_beta": False,
                    },
                    {
                        "product": "Thunderbird",
                        "version": "10.0.2b",
                        "start_date": now,
                        "end_date": nextweek,
                        "throttle": 10.00,
                        "is_featured": False,
                        "build_type": "Release",
                        "has_builds": False,
                        "is_rapid_beta": True,
                    },
                    {
                        "product": "Fennec",
                        "version": "12.0b1",
                        "start_date": now,
                        "end_date": nextweek,
                        "throttle": 100.00,
                        "is_featured": False,
                        "build_type": "Beta",
                        "has_builds": True,
                        "is_rapid_beta": False,
                    },
                    {
                        "product": "Fennec",
                        "version": "11.0.1",
                        "start_date": now,
                        "end_date": now,
                        "throttle": 10.00,
                        "is_featured": False,
                        "build_type": "Release",
                        "has_builds": False,
                        "is_rapid_beta": False,
                    },
                ],
            "total": 3
        }
        assert res['hits'][0] == res_expected['hits'][0]
        assert res['hits'][1] == res_expected['hits'][1]
        assert res['hits'][2] == res_expected['hits'][2]
        assert res['hits'][3] == res_expected['hits'][3]
        for hit in res['hits']:
            assert hit['end_date'] >= now

        res = not_active_results = productversions.get(active=False)
        assert res['total'] == 1

        both_results = productversions.get()
        assert both_results['total'] == active_results['total'] + not_active_results['total']

    def test_filter_by_is_rapid_beta(self):
        productversions = ProductVersions(config=self.config)

        res = true_results = productversions.get(is_rapid_beta=True)
        assert res['total'] == 1
        for hit in res['hits']:
            assert hit['is_rapid_beta']

        res = false_results = productversions.get(is_rapid_beta=False)
        assert res['total'] == 4
        for hit in res['hits']:
            assert not hit['is_rapid_beta']

        both_results = productversions.get()
        assert both_results['total'] == true_results['total'] + false_results['total']

    def test_filter_by_build_type(self):
        productversions = ProductVersions(config=self.config)

        res = productversions.get(
            build_type=['Beta'],
        )
        assert res['total'] == 1
        for hit in res['hits']:
            assert hit['build_type'] == 'Beta'

        res = productversions.get(
            build_type=['JUNK'],
        )
        assert res['total'] == 0

    def test_post(self):
        products = ProductVersions(config=self.config)

        assert products.post(product='KillerApp', version='1.0')

        # let's check certain things got written to certain tables
        cursor = self.connection.cursor()
        try:
            # expect there to be a new product
            cursor.execute(
                'select product_name from products '
                "where product_name=%s",
                ('KillerApp',)
            )
            product_name, = cursor.fetchone()
            assert product_name, 'KillerApp'
        finally:
            self.connection.rollback()

    def test_post_bad_product_name(self):
        products = ProductVersions(config=self.config)

        assert not products.post(product='Spaces not allowed', version='')

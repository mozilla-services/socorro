# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_

from socorro.external.postgresql.releases_service import Releases
from socorro.external.postgresql.products_service import Products
from socorro.lib import datetimeutil
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestReleases(PostgreSQLTestCase):
    """Test socorro.external.postgresql.releases.Releases class. """

    #--------------------------------------------------------------------------
    def _insert_test_data(self, connection):
        # Insert data
        now = datetimeutil.utc_now()
        build_date = now - datetime.timedelta(days=30)
        sunset_date = now + datetime.timedelta(days=30)

        execute_no_results(
            connection,
            """
            INSERT INTO products
            (product_name, sort, release_name)
            VALUES
            (
                'Firefox',
                1,
                'firefox'
            ),
            (
                'FennecAndroid',
                2,
                'fennecandroid'
            ),
            (
                'Thunderbird',
                3,
                'thunderbird'
            );
        """)

        execute_no_results(
            connection,
            """
            INSERT INTO product_versions
            (product_version_id, product_name, major_version, release_version,
             version_string, version_sort, build_date, sunset_date,
             featured_version, build_type)
            VALUES
            (
                1,
                'Firefox',
                '15.0',
                '15.0',
                '15.0a1',
                '000000150a1',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly'
            ),
            (
                2,
                'Firefox',
                '14.0',
                '14.0',
                '14.0a2',
                '000000140a2',
                '%(build_date)s',
                '%(sunset_date)s',
                'f',
                'Aurora'
            ),
            (
                3,
                'Firefox',
                '13.0',
                '13.0',
                '13.0b1',
                '000000130b1',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Beta'
            ),
            (
                4,
                'FennecAndroid',
                '15.0',
                '15.0',
                '15.0a1',
                '000000150a1',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly'
            ),
            (
                5,
                'FennecAndroid',
                '14.0',
                '14.0',
                '14.0a1',
                '000000140a1',
                '%(build_date)s',
                '%(sunset_date)s',
                'f',
                'Aurora'
            ),
            (
                6,
                'Thunderbird',
                '15.0',
                '15.0',
                '15.0a1',
                '000000150a1',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly'
            ),
            (
                7,
                'Firefox',
                '24.5',
                '24.5.0esr',
                '24.5.0esr',
                '024005000x000',
                '%(build_date)s',
                '%(sunset_date)s',
                'f',
                'ESR'
            )
            ;
        """ % {"build_date": build_date, "sunset_date": sunset_date})

        execute_no_results(
            connection,
            """
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1),
            ('Aurora', 2),
            ('Beta', 3),
            ('Release', 4),
            ('ESR', 5);
        """)

        execute_no_results(
            connection,
            """
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            ('Firefox', 'Nightly', 1),
            ('Firefox', 'Aurora', 1),
            ('Firefox', 'Beta', 1),
            ('Firefox', 'Release', 1),
            ('Firefox', 'ESR', 1),
            ('Thunderbird', 'Nightly', 1),
            ('Thunderbird', 'Aurora', 1),
            ('Thunderbird', 'Beta', 1),
            ('Thunderbird', 'Release', 1),
            ('FennecAndroid', 'Nightly', 1),
            ('FennecAndroid', 'Aurora', 1),
            ('FennecAndroid', 'Beta', 1),
            ('FennecAndroid', 'Release', 1);
        """)

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestReleases, self).setUp((Releases, Products))
        self.transaction(self._insert_test_data)

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        self.transaction(
            execute_no_results,
            """
        TRUNCATE product_versions CASCADE;
        TRUNCATE products CASCADE;
        TRUNCATE releases_raw CASCADE;
        TRUNCATE release_channels CASCADE;
        TRUNCATE product_release_channels CASCADE;
            """
        )
        super(IntegrationTestReleases, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get_featured(self):
        service = Releases(config=self.config)

        #......................................................................
        # Test 1: one product
        params = {
            "products": ["Firefox"]
        }
        res = service.get_featured(**params)
        res_expected = {
            "hits": {
                "Firefox": ["13.0b1", "15.0a1"]
            },
            "total": 2
        }
        eq_(res, res_expected)

        #......................................................................
        # Test 2: several products, several versions
        params = {
            "products": ["Firefox", "FennecAndroid", "Thunderbird"]
        }
        res = service.get_featured(**params)
        res_expected = {
            "hits": {
                "Firefox": ["13.0b1", "15.0a1"],
                "FennecAndroid": ["15.0a1"],
                "Thunderbird": ["15.0a1"]
            },
            "total": 4
        }
        eq_(res, res_expected)

        #......................................................................
        # Test 3: an unknown product
        params = {
            "products": ["Unknown"]
        }
        res = service.get_featured(**params)
        res_expected = {
            "hits": {},
            "total": 0
        }
        eq_(res, res_expected)

        #......................................................................
        # Test 4: all products
        res = service.get_featured()
        res_expected = {
            "hits": {
                "Firefox": ["13.0b1", "15.0a1"],
                "FennecAndroid": ["15.0a1"],
                "Thunderbird": ["15.0a1"]
            },
            "total": 4
        }
        eq_(res, res_expected)

    #--------------------------------------------------------------------------
    def test_update_featured(self):
        service = Releases(config=self.config)

        #......................................................................
        # Test 1: one product, several versions
        params = {
            "Firefox": [
                "15.0a1",
                "14.0a2",
                "13.0b1"
            ]
        }
        res = service.post(**params)
        ok_(res)

        res = service.get_featured()
        res_expected = {
            "hits": {
                "Firefox": ["13.0b1", "14.0a2", "15.0a1"],
                "Thunderbird": ["15.0a1"],
                "FennecAndroid": ["15.0a1"]
            },
            "total": 5
        }
        eq_(res, res_expected)

        #......................................................................
        # Test 2: several products, several versions
        params = {
            "Firefox": [
                "13.0b1"
            ],
            "FennecAndroid": [
                "14.0a1"
            ]
        }
        res = service.post(**params)
        ok_(res)

        res = service.get_featured()
        res_expected = {
            "hits": {
                "Firefox": ["13.0b1"],
                "Thunderbird": ["15.0a1"],
                "FennecAndroid": ["14.0a1"]
            },
            "total": 3
        }
        eq_(res, res_expected)

        #......................................................................
        # Test 3: an unknown product
        params = {
            "Unknown": [
                "15.0a1"
            ]
        }
        res = service.post(**params)
        ok_(not res)

        res = service.get_featured()
        res_expected = {
            "hits": {
                "Firefox": ["13.0b1"],
                "Thunderbird": ["15.0a1"],
                "FennecAndroid": ["14.0a1"]
            },
            "total": 3
        }
        eq_(res, res_expected)

        #......................................................................
        # Test 4: an unknown product and an existing product
        params = {
            "Firefox": [
                "14.0a2"
            ],
            "Unknown": [
                "15.0a1"
            ]
        }
        res = service.post(**params)
        ok_(res)

        res = service.get_featured()
        res_expected = {
            "hits": {
                "Firefox": ["14.0a2"],
                "Thunderbird": ["15.0a1"],
                "FennecAndroid": ["14.0a1"]
            },
            "total": 3
        }
        eq_(res, res_expected)

        #......................................................................
        # Test 4: an unknown version
        params = {
            "Firefox": [
                "200.0a1"  # that's like, in 2035, dude
            ]
        }
        res = service.post(**params)
        ok_(res)

        res = service.get_featured()
        res_expected = {
            "hits": {
                "Thunderbird": ["15.0a1"],
                "FennecAndroid": ["14.0a1"]
            },
            "total": 2
        }
        eq_(res, res_expected)

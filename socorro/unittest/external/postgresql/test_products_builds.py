# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
import psycopg2
import psycopg2.extras

from socorro.external.postgresql import products_builds
import socorro.database.database as db

from unittestbase import PostgreSQLTestCase

import logging
logger = logging.getLogger("webapi")

from decimal import Decimal


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestProductsBuilds(PostgreSQLTestCase):
    """Test socorro.external.postgresql.products_builds.ProductsBuilds class.
    """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestProductsBuilds, self).setUp()

        cursor = self.connection.cursor()

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

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1),
            ('Aurora', 2),
            ('Beta', 3),
            ('Release', 4),
            ('ESR', 4);
        """)

        cursor.execute("""
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

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE products CASCADE;
            TRUNCATE releases_raw CASCADE;
            TRUNCATE release_channels CASCADE;
            TRUNCATE product_release_channels CASCADE;
        """)
        self.connection.commit()
        super(IntegrationTestProductsBuilds, self).tearDown()

    #--------------------------------------------------------------------------
    def _get_builds_for_product(self, product):
        cursor = self.connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        result = db.execute(cursor, """
            SELECT product_name as product,
                   version,
                   build_id,
                   build_type,
                   platform,
                   repository
            FROM releases_raw
            WHERE product_name = %(product)s
        """, {"product": product})
        return list(result)

    #--------------------------------------------------------------------------
    def _get_builds_for_version(self, version):
        cursor = self.connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        result = db.execute(cursor, """
            SELECT product_name as product,
                   version,
                   build_id,
                   build_type,
                   platform,
                   repository
            FROM releases_raw
            WHERE version = %(version)s
        """, {"version": version})
        return list(result)

    #--------------------------------------------------------------------------
    def test_create(self):
        builds = products_builds.ProductsBuilds(config=self.config)

        #......................................................................
        # Test 1: a new build
        params = {
            "product": "firefox",
            "version": "20.0",
            "build_id": Decimal('20120417012345'),
            "build_type": "Release",
            "platform": "macosx",
            "repository": "mozilla-central"
        }
        product, version = builds.create(**params)
        self.assertEqual(params["product"], product)
        self.assertEqual(params["version"], version)

        # Verify that build has been created in the DB
        res = self._get_builds_for_product(params["product"])

        self.assertEqual(1, len(res))
        self.assertEqual(params, res[0])

        #......................................................................
        # Test 2: required parameters
        params = {}
        self.assertRaises(products_builds.MissingArgumentError,
                          builds.create,
                          **params)

        #......................................................................
        # Test 3: optional parameters
        params = {
            "product": "thunderbird",
            "version": "17.0",
            "build_id": Decimal('20120416012345'),
            "build_type": "Aurora",
            "platform": "win32"
        }
        product, version = builds.create(**params)
        self.assertEqual(params["product"], product)
        self.assertEqual(params["version"], version)

        # Verify that build has been created in the DB
        res = self._get_builds_for_product(params["product"])

        # create() supplies an empty repository as the default
        params["repository"] = ""

        self.assertEqual(1, len(res))
        self.assertEqual(params, res[0])

        #......................................................................
        # Test 4: beta_number required if build_type is beta
        params = {
            "product": "Firefox",
            "version": "1.0",
            "build_id": 20110316000005,
            "build_type": "Beta",
            "platform": "linux"
        }
        self.assertRaises(products_builds.MissingArgumentError,
                          builds.create,
                          **params)

        #......................................................................
        # Test 5: ESR releases with Gecko security fixes
        params = {
            "product": "Firefox",
            "version": "24.5.0esr",
            "build_id": 20110316000005,
            "build_type": "ESR",
            "platform": "windows"
        }
        product, version = builds.create(**params)
        self.assertEqual(params["product"], product)
        self.assertEqual(params["version"], version)

        # Verify that build has been created in the DB
        res = self._get_builds_for_version(params["version"])

        self.assertEqual(1, len(res))

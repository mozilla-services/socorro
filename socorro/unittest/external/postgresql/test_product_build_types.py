# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, assert_raises

from socorro.external import MissingArgumentError
from socorro.external.postgresql.product_build_types import ProductBuildTypes

from .unittestbase import PostgreSQLTestCase


#==============================================================================
class IntegrationTestProductBuildTypes(PostgreSQLTestCase):
    """Test socorro.external.postgresql.product_build_types.ProductBuildTypes
     class. """

    @classmethod
    def setUpClass(cls):
        """ Populate product_info table with fake data """
        super(IntegrationTestProductBuildTypes, cls).setUpClass()

        cursor = cls.connection.cursor()

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
            INSERT INTO product_build_types
            (product_name, build_type, throttle)
            VALUES
            (
                'Firefox',
                'beta',
                1.0
            ),
            (
                'Firefox',
                'release',
                0.2
            ),
            (
                'Fennec',
                'release',
                0.1
            )
        """)

        cls.connection.commit()

    #--------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        """ Cleanup the database, delete tables and functions """
        cursor = cls.connection.cursor()
        cursor.execute("""
            TRUNCATE products, product_build_types
            CASCADE
        """)
        cls.connection.commit()
        super(IntegrationTestProductBuildTypes, cls).tearDownClass()

    #--------------------------------------------------------------------------
    def test_get(self):
        product_build_types = ProductBuildTypes(config=self.config)

        # Test: find match for one product
        res = product_build_types.get(product='Firefox')
        res_expected = {
            'hits': {
                'release': 0.2,
                'beta': 1.0,
            }
        }
        eq_(res, res_expected)

        # Test: find no match for unrecognized product
        res = product_build_types.get(product='Neverheardof')
        res_expected = {
            'hits': {}
        }
        eq_(res, res_expected)

        # Test: missing product parameter
        assert_raises(
            MissingArgumentError,
            product_build_types.get,
        )
        assert_raises(
            MissingArgumentError,
            product_build_types.get,
            product=''
        )

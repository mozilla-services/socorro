# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import psycopg2

from socorro.unittest.external.postgresql.unittestbase import \
     PostgreSQLTestCase
from socorro.lib import buildutil


#==============================================================================
class TestBuildUtil(PostgreSQLTestCase):

    def setUp(self):
        """Set up this test class by populating the products table with fake
        data. """
        super(TestBuildUtil, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name)
            VALUES
            (
                'Firefox',
                '0',
                '15.0',
                'firefox'
            ),
            (
                'Product',
                '0',
                '1.0',
                'product'
            );
        """)

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Release', 1),
            ('Beta', 2),
            ('Aurora', 3),
            ('Nightly', 4);
        """)

        cursor.execute("""
            SELECT add_new_release(
                'Product', '1.0', 'Release', 20111223, 'Linux', NULL,
                'mozilla-central'
            );
        """)

        self.connection.commit()

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE products CASCADE;
            TRUNCATE release_channels CASCADE;
            TRUNCATE releases_raw CASCADE;
        """)
        self.connection.commit()
        super(TestBuildUtil, self).tearDown()

    def build_exists(self, cursor, product_name, version, platform, build_id,
                     build_type, beta_number, repository):
        """ Determine whether or not a particular release build exists already.
        """
        sql = """
            SELECT *
            FROM releases_raw
            WHERE product_name = %s
            AND version = %s
            AND platform = %s
            AND build_id = %s
            AND build_type = %s
        """

        if beta_number is not None:
            sql += """ AND beta_number = %s """
        else:
            sql += """ AND beta_number IS %s """

        sql += """ AND repository = %s """

        params = (product_name, version, platform, build_id, build_type,
                  beta_number, repository)
        cursor.execute(sql, params)
        exists = cursor.fetchone()

        return exists is not None


    def test_insert_build(self):
        cursor = self.connection.cursor()

        # Test 1: successfully insert a build
        buildutil.insert_build(cursor, 'Firefox', 'VERSIONAME5',
              'PLATFORMNAME5', '20110101', 'Release', '5', 'REPO5')
        actual = self.build_exists(cursor, 'Firefox',
              'VERSIONAME5', 'PLATFORMNAME5', '20110101', 'Release',
              '5', 'REPO5')
        self.assertTrue(actual)

        # Test 2: fail at inserting a build
        buildutil.insert_build(cursor, 'Unknown', 'VERSIONAME5', 'PLATFORMNAME5',
                  '20110101', 'Release', '5', 'REPO5')
        actual = self.build_exists(cursor, 'Unknown',
              'VERSIONAME5', 'PLATFORMNAME5', '20110101', 'Release',
              '5', 'REPO5')
        self.assertFalse(actual)

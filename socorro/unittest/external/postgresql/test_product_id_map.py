# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.postgresql.product_id_map import ProductIDMap
from socorro.unittest.external.postgresql.unittestbase import PostgreSQLTestCase


class IntegrationTestProductIDMap(PostgreSQLTestCase):

    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestProductIDMap, self).setUp()
        self._truncate()

        return_value = (
            ('FennecAndroid', '{ec8030f7-c20a-464f-9b0e-13a3a9e97384-fa}', True),
            ('Chrome', '{ec8030f7-c20a-464f-9b0e-13b3a9e97384-c}', True),
            ('Safari', '{ec8030f7-c20a-464f-9b0e-13c3a9e97384-s}', True),
            ('MoonMoon', '{ec8030f7-c20a-464f-9b0e-13c3a9e97384-mm}', False),
        )

        cursor = self.connection.cursor()
        for product_name, productid, rewrite in return_value:
            cursor.execute("""
                INSERT INTO products
                (product_name, sort, release_name)
                VALUES
                (%s, 1, %s)
            """, (
                product_name, product_name.lower()
            ))
            cursor.execute("""
                INSERT INTO product_productid_map
                (product_name, productid, rewrite)
                VALUES
                (%s, %s, %s)
            """, (product_name, productid, rewrite))
        self.connection.commit()

        cursor = self.connection.cursor()
        cursor.execute('select count(*) from product_productid_map')
        count, = cursor.fetchone()

        assert count == 4

    def tearDown(self):
        self._truncate()
        super(IntegrationTestProductIDMap, self).tearDown()

    def _truncate(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE
                product_productid_map
            CASCADE
        """)
        self.connection.commit()

    def test_get(self):
        impl = ProductIDMap(config=self.config)

        response = impl.get()
        assert len(response.keys()) == 3  # only rewrite=true
        assert all([entry['rewrite'] for entry in response.values()])

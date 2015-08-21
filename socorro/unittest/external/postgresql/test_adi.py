# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.plugins.attrib import attr
from nose.tools import eq_, assert_raises

from socorro.external.postgresql.adi import ADI
from socorro.external import MissingArgumentError

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestADI(PostgreSQLTestCase):

    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestADI, self).setUp()
        self._truncate()
        cursor = self.connection.cursor()

        self.date = datetime.datetime(2015, 7, 1)
        yesterday = self.date - datetime.timedelta(hours=24)
        products = ('Firefox', 'Thunderbird')

        versions = ('39.0', '40.0')
        platforms = ('Linux', 'Windows')
        channels = ('release', 'beta')

        build_date = yesterday - datetime.timedelta(days=30)
        sunset_date = yesterday + datetime.timedelta(days=30)

        for platform in platforms:
            cursor.execute("""
                INSERT INTO os_names
                (os_short_name, os_name)
                VALUES
                (%s, %s)
            """, (platform.lower()[:3], platform))
            cursor.execute("""
                INSERT INTO os_name_matches
                (match_string, os_name)
                VALUES
                (%s, %s)
            """, (platform, platform))

        adi_count = 1
        product_version_id = 0
        for product in products:
            cursor.execute("""
                INSERT INTO products
                (product_name, sort, release_name)
                VALUES
                (%s, 1, %s)
            """, (
                product, product.lower()
            ))
            cursor.execute("""
                INSERT into product_productid_map (
                    product_name,
                    productid
                ) VALUES (
                    %s, %s
                )
            """, (
                product,
                product.lower() + '-guid',
            ))
            for version in versions:
                for platform in platforms:
                    for channel in channels:
                        cursor.execute("""
                            INSERT INTO raw_adi (
                                adi_count,
                                date,
                                product_name,
                                product_os_platform,
                                product_os_version,
                                product_version,
                                build,
                                product_guid,
                                update_channel,
                                received_at
                            )
                            VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                            )
                        """, (
                            adi_count,
                            yesterday,
                            product,
                            platform,
                            '1.0',
                            version,
                            '20140903141017',
                            '{abc}',
                            channel,
                        ))
                        adi_count *= 2

                product_version_id += 1
                cursor.execute("""
                    INSERT INTO product_versions
                    (product_version_id, product_name, major_version,
                     release_version, version_string, version_sort,
                     build_date, sunset_date, featured_version,
                     build_type, build_type_enum)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 't', %s, %s)
                """, (
                    product_version_id,
                    product,
                    version,
                    version,
                    version,
                    '0000' + version.replace('.', ''),
                    build_date,
                    sunset_date,
                    'release',
                    'release',
                ))

        cursor.callproc('update_adu', [yesterday.date()])
        self.connection.commit()

        cursor = self.connection.cursor()
        cursor.execute('select count(*) from product_adu')
        count, = cursor.fetchone()
        # expect there to be 2 * 2 * 2 rows of product_adu
        assert count == 8, count

    def tearDown(self):
        self._truncate()
        super(IntegrationTestADI, self).tearDown()

    def _truncate(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE
                raw_adi, products, product_versions, product_adu,
                product_productid_map, os_names, os_name_matches
            CASCADE
        """)
        self.connection.commit()

    def test_get(self):
        impl = ADI(config=self.config)
        assert_raises(
            MissingArgumentError,
            impl.get
        )
        start = self.date - datetime.timedelta(days=1)
        end = self.date
        stats = impl.get(
            start_date=start,
            end_date=end,
            product='Firefox',
            versions=['42'],
            platforms=['Linux', 'Windows'],
        )
        eq_(stats['hits'], [])
        eq_(stats['total'], 0)

        stats = impl.get(
            start_date=start,
            end_date=end,
            product='Firefox',
            versions=['40.0'],
            platforms=['Linux', 'Windows'],
        )
        start_formatted = start.strftime('%Y-%m-%d')
        eq_(stats['total'], 1)
        hit, = stats['hits']
        eq_(hit, {
            'adi_count': 64L + 16L,
            'date': start_formatted,
            'version': '40.0',
            'build_type': 'release'
        })

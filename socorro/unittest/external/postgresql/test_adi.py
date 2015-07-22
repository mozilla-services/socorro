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
        versions = ('39', '40')
        platforms = ('Linux', 'Darwin')
        channels = ('release', 'beta')
        adi_count = 1
        for product in products:
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
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
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
        cursor.execute('select count(*) from raw_adi')
        count, = cursor.fetchone()
        # We expect there to be 2 channels per every 2 platforms,
        # per every 2 versions per every 2 products.
        assert count == 2 * 2 * 2 * 2, count
        self.connection.commit()

    def tearDown(self):
        self._truncate()
        super(IntegrationTestADI, self).tearDown()

    def _truncate(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE raw_adi CASCADE
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
            version='42'
        )
        eq_(stats['hits'], [])

        stats = impl.get(
            start_date=start,
            end_date=end,
            product='Firefox',
            version='40'
        )
        start_formatted = start.strftime('%Y-%m-%d')
        hits = stats['hits']
        # Because the results come back in no particular order,
        # to make it easier to compare, sort by something predictable.
        hits.sort(key=lambda x: x['adi_count'])

        eq_(stats['hits'][0], {
            'adi_count': 16L,
            'date': start_formatted,
            'product': 'Firefox',
            'version': '40',
            'platform': 'Linux',
            'release_channel': 'release'
        })
        eq_(stats['hits'][1], {
            'adi_count': 32L,
            'date': start_formatted,
            'product': 'Firefox',
            'version': '40',
            'platform': 'Linux',
            'release_channel': 'beta'
        })
        eq_(stats['hits'][2], {
            'adi_count': 64L,
            'date': start_formatted,
            'product': 'Firefox',
            'version': '40',
            'platform': 'Darwin',
            'release_channel': 'release'
        })
        eq_(stats['hits'][3], {
            'adi_count': 128L,
            'date': start_formatted,
            'product': 'Firefox',
            'version': '40',
            'platform': 'Darwin',
            'release_channel': 'beta'
        })

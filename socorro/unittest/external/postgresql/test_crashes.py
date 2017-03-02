# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.tools import eq_, assert_raises

from socorro.lib import (
    BadArgumentError,
    datetimeutil,
)
from socorro.external.postgresql.crashes import AduBySignature

from unittestbase import PostgreSQLTestCase


class IntegrationTestCrashes(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crashes.Crashes class. """

    @classmethod
    def setUpClass(cls):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestCrashes, cls).setUpClass()

        cursor = cls.connection.cursor()

        cls.now = datetimeutil.utc_now()
        yesterday = cls.now - datetime.timedelta(days=1)

        cursor.execute("""
            INSERT INTO crash_adu_by_build_signature
            (signature_id, signature, adu_date, build_date, buildid,
             crash_count, adu_count, os_name, channel, product_name)
            VALUES
            (1, 'canIhaveYourSignature()', '{yesterday}', '2014-03-01',
             '201403010101', 3, 1023, 'Mac OS X', 'release', 'WaterWolf'),
            (1, 'canIhaveYourSignature()', '{yesterday}', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf'),
            (1, 'canIhaveYourSignature()', '2014-01-01', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf'),
            (2, 'youMayNotHaveMySignature()', '{yesterday}', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf'),
            (2, 'youMayNotHaveMySignature()', '{yesterday}', '2014-04-01',
             '201404010101', 4, 1024, 'Windows NT', 'release', 'WaterWolf')
        """.format(yesterday=yesterday))

        cls.connection.commit()
        cursor.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up the database, delete tables and functions. """
        cursor = cls.connection.cursor()
        cursor.execute("""
            TRUNCATE reports, home_page_graph_build, home_page_graph,
                     crashes_by_user, crashes_by_user_build, crash_types,
                     process_types, os_names, signatures,
                     product_versions, product_release_channels,
                     release_channels, products,
                     reports_clean, crash_adu_by_build_signature
            CASCADE
        """)
        cls.connection.commit()
        cursor.close()
        super(IntegrationTestCrashes, cls).tearDownClass()

    def test_get_adu_by_signature(self):
        adu_by_signature = AduBySignature(config=self.config)

        signature = "canIhaveYourSignature()"
        channel = "release"
        yesterday_date = (self.now - datetime.timedelta(days=1)).date()
        yesterday = datetimeutil.date_to_string(yesterday_date)

        res_expected = {
            "hits": [
                {
                    "product_name": "WaterWolf",
                    "signature": signature,
                    "adu_date": yesterday,
                    "build_date": "2014-03-01",
                    "buildid": '201403010101',
                    "crash_count": 3,
                    "adu_count": 1023,
                    "os_name": "Mac OS X",
                    "channel": channel,
                },
                {
                    "product_name": "WaterWolf",
                    "signature": signature,
                    "adu_date": yesterday,
                    "build_date": "2014-04-01",
                    "buildid": '201404010101',
                    "crash_count": 4,
                    "adu_count": 1024,
                    "os_name": "Windows NT",
                    "channel": channel,
                },
            ],
            "total": 2,
        }

        res = adu_by_signature.get(
            product_name="WaterWolf",
            start_date=yesterday,
            end_date=yesterday,
            signature=signature,
            channel=channel,
        )
        eq_(res, res_expected)

        assert_raises(
            BadArgumentError,
            adu_by_signature.get,
            start_date=(yesterday_date - datetime.timedelta(days=366)),
            end_date=yesterday,
            signature=signature,
            channel=channel
        )

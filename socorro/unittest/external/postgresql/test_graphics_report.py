# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.tools import eq_, ok_

from socorro.external.postgresql.graphics_report import GraphicsReport

from .unittestbase import PostgreSQLTestCase


#==============================================================================
class IntegrationTestGraphicsReport(PostgreSQLTestCase):
    """Test socorro.external.postgresql.graphics_report.GraphicsReport
     class. """

    @classmethod
    def setUpClass(cls):
        """ Populate product_info table with fake data """
        super(IntegrationTestGraphicsReport, cls).setUpClass()
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
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        # To make it safe, make this be the 0th hour of the day
        # so when we insert the second one, which is 60 seconds later
        # it can't be the next day
        yesterday = yesterday.replace(hour=0)

        cursor.execute("""
            INSERT INTO reports
            (id, signature, date_processed, uuid, product,
             url, email, success, addons_checked, release_channel)
            VALUES
            (
                1,
                'signature',
                %s,
                '1',
                'Firefox',
                'http://mywebsite.com',
                'test@something.com',
                TRUE,
                TRUE,
                'alpha'
            ),
            (
                2,
                'my signature',
                %s,
                '2',
                'Firefox',
                'http://myotherwebsite.com',
                'admin@example.com',
                NULL,
                FALSE,
                'beta'
            );
        """, (
            yesterday,
            # make one 1 minute later so we can test the sort order
            yesterday + datetime.timedelta(seconds=60)
        ))

        cls.connection.commit()

    #--------------------------------------------------------------------------
    @classmethod
    def tearDownClass(cls):
        """ Cleanup the database, delete tables and functions """
        cursor = cls.connection.cursor()
        cursor.execute("""
            TRUNCATE products, reports
            CASCADE
        """)
        cls.connection.commit()
        super(IntegrationTestGraphicsReport, cls).tearDownClass()

    #--------------------------------------------------------------------------
    def test_get(self):
        api = GraphicsReport(config=self.config)
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        res = api.get(product='Firefox', date=yesterday.date())
        assert res['hits']
        assert len(res['hits']) == res['total']
        ok_(isinstance(res['hits'], list))
        crash_ids = [x.crash_id for x in res['hits']]
        eq_(crash_ids, ['1', '2'])
        release_channels = [x.release_channel for x in res['hits']]
        eq_(release_channels, ['alpha', 'beta'])
        signatures = [x.signature for x in res['hits']]
        eq_(signatures, ['signature', 'my signature'])
        date_processed = [x.date_processed for x in res['hits']]
        # should be ordered ascending
        first, second = date_processed
        ok_(first < second)
        bug_associations = [x.bug_list for x in res['hits']]
        eq_(bug_associations, [[], []])

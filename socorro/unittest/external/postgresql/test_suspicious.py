# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.plugins.attrib import attr

from socorro.external.postgresql.suspicious import SuspiciousCrashSignatures
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestSuspicious(PostgreSQLTestCase):

    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestSuspicious, self).setUp()

        cursor = self.connection.cursor()
        # inserts some signatures.
        cursor.execute("""
            INSERT INTO signatures
                (signature)
            VALUES
                ('testsignature1'),
                ('testsignature2')
        """)

        self.connection.commit()
        cursor = self.connection.cursor()

        # get the id
        cursor.execute("""
            SELECT signature_id
            FROM signatures
            WHERE signature='testsignature1' OR signature='testsignature2'
            ORDER BY signature_id
        """)

        sigs = []
        for s in cursor:
            sigs.append(s[0])

        # Insert data
        now = datetimeutil.utc_now()
        cursor.execute("""
            INSERT INTO suspicious_crash_signatures
                (signature_id, report_date)
            VALUES
                ({0}, '{1}'::timestamp without time zone)
        """.format(sigs[0], now.strftime('%Y-%m-%d')))

        now -= datetime.timedelta(15)

        cursor.execute("""
            INSERT INTO suspicious_crash_signatures
                (signature_id, report_date)
            VALUES
                ({0}, '{1}'::timestamp without time zone)
        """.format(sigs[1], now.strftime('%Y-%m-%d')))

        self.connection.commit()

    def test_get_today(self):
        mware = SuspiciousCrashSignatures(config=self.config)
        stats = mware.get()

        self.assertEquals(1, len(stats))
        now = datetimeutil.utc_now().strftime('%Y-%m-%d')
        self.assertTrue(now in stats)
        self.assertEquals(1, len(stats[now]))
        self.assertEquals('testsignature1', stats[now][0])

    def test_get_with_start(self):
        mware = SuspiciousCrashSignatures(config=self.config)

        sometimeago = datetimeutil.utc_now() - datetime.timedelta(16)
        sometimeago = sometimeago.strftime('%Y-%m-%d')

        now = datetimeutil.utc_now()
        fifteen = now - datetime.timedelta(15)
        now = now.strftime('%Y-%m-%d')
        fifteen = fifteen.strftime('%Y-%m-%d')
        stats = mware.get(start_date=sometimeago)
        self.assertEquals(2, len(stats))
        self.assertTrue(fifteen in stats)
        self.assertTrue(now in stats)
        self.assertEquals(1, len(stats[now]))
        self.assertEquals(1, len(stats[fifteen]))
        self.assertEquals('testsignature1', stats[now][0])
        self.assertEquals('testsignature2', stats[fifteen][0])

    def test_get_with_start_end(self):
        mware = SuspiciousCrashSignatures(config=self.config)

        start = datetimeutil.utc_now() - datetime.timedelta(16)
        end = start + datetime.timedelta(5)

        start = start.strftime('%Y-%m-%d')
        end = end.strftime('%Y-%m-%d')

        stats = mware.get(start_date=start, end_date=end)
        fifteen = datetimeutil.utc_now() - datetime.timedelta(15)
        fifteen = fifteen.strftime('%Y-%m-%d')
        self.assertEquals(1, len(stats))
        self.assertTrue(fifteen in stats)
        self.assertEquals(1, len(stats[fifteen]))
        self.assertEquals('testsignature2', stats[fifteen][0])

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE suspicious_crash_signatures, signatures CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestSuspicious, self).tearDown()

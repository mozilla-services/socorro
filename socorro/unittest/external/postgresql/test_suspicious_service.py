# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.plugins.attrib import attr
from nose.tools import eq_

from socorro.external.postgresql.suspicious_service import (
    SuspiciousCrashSignatures
)
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
)
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestSuspicious(PostgreSQLTestCase):

    #--------------------------------------------------------------------------
    def _insert_test_data(self, connection):
        execute_no_results(
            connection,
            """
                TRUNCATE suspicious_crash_signatures, signatures CASCADE
            """
        )
        # Insert data

        # inserts some signatures.
        execute_no_results(
            connection,
            """
            INSERT INTO signatures
                (signature)
            VALUES
                ('testsignature1'),
                ('testsignature2')
            """
        )

        # get the id
        result = execute_query_fetchall(
            connection,
            """
            SELECT signature_id
            FROM signatures
            WHERE signature='testsignature1' OR signature='testsignature2'
            ORDER BY signature_id
        """)

        sigs = [s[0] for s in result]

        # Insert data
        now = datetimeutil.utc_now()
        execute_no_results(
            connection,
            """
            INSERT INTO suspicious_crash_signatures
                (signature_id, report_date)
            VALUES
                ({0}, '{1}'::timestamp with time zone)
        """.format(sigs[0], now.strftime('%Y-%m-%d')))

        now -= datetime.timedelta(15)

        execute_no_results(
            connection,
            """
            INSERT INTO suspicious_crash_signatures
                (signature_id, report_date)
            VALUES
                ({0}, '{1}'::timestamp with time zone)
        """.format(sigs[1], now.strftime('%Y-%m-%d')))

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestSuspicious, self).setUp(SuspiciousCrashSignatures)
        self.transaction(self._insert_test_data)

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        self.transaction(
            execute_no_results,
            """
                TRUNCATE suspicious_crash_signatures, signatures CASCADE
            """
        )
        super(IntegrationTestSuspicious, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get_today(self):
        mware = SuspiciousCrashSignatures(config=self.config)
        stats = mware.get()

        eq_(1, len(stats['hits']))
        now = datetimeutil.utc_now().strftime('%Y-%m-%d')
        eq_(now, stats['hits'][0]['date'])
        eq_(1, len(stats['hits'][0]['signatures']))
        eq_('testsignature1', stats['hits'][0]['signatures'][0])

    #--------------------------------------------------------------------------
    def test_get_with_start(self):
        mware = SuspiciousCrashSignatures(config=self.config)

        sometimeago = datetimeutil.utc_now() - datetime.timedelta(16)
        sometimeago = sometimeago.strftime('%Y-%m-%d')

        now = datetimeutil.utc_now()
        fifteen = now - datetime.timedelta(15)
        now = now.strftime('%Y-%m-%d')
        fifteen = fifteen.strftime('%Y-%m-%d')
        stats = mware.get(start_date=sometimeago)
        eq_(2, len(stats['hits']))

        stats['hits'].sort(key=lambda x: x['date'])
        eq_(fifteen, stats['hits'][0]['date'])
        eq_(now, stats['hits'][1]['date'])

        eq_(1, len(stats['hits'][0]['signatures']))
        eq_(1, len(stats['hits'][1]['signatures']))
        eq_('testsignature2', stats['hits'][0]['signatures'][0])
        eq_('testsignature1', stats['hits'][1]['signatures'][0])

    #--------------------------------------------------------------------------
    def test_get_with_start_end(self):
        mware = SuspiciousCrashSignatures(config=self.config)

        start = datetimeutil.utc_now() - datetime.timedelta(16)
        end = start + datetime.timedelta(5)

        start = start.strftime('%Y-%m-%d')
        end = end.strftime('%Y-%m-%d')

        stats = mware.get(start_date=start, end_date=end)
        fifteen = datetimeutil.utc_now() - datetime.timedelta(15)
        fifteen = fifteen.strftime('%Y-%m-%d')
        eq_(1, len(stats['hits']))
        eq_(fifteen, stats['hits'][0]['date'])
        eq_(1, len(stats['hits'][0]['signatures']))
        eq_('testsignature2', stats['hits'][0]['signatures'][0])


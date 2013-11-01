# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import mock
import socorro.external.postgresql.tcbs as tcbs
from nose.plugins.attrib import attr
from socorro.lib import datetimeutil, util
from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')
class IntegrationTestTCBS(PostgreSQLTestCase):
    """Test TopCrashers By Signature functions"""
    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate product_info table with fake data """
        super(IntegrationTestTCBS, self).setUp()

        cursor = self.connection.cursor()

        self.now = datetimeutil.utc_now()
        now = self.now.date()
        yesterday = now - datetime.timedelta(days=1)
        lastweek = now - datetime.timedelta(days=7)

        self.params = util.DotDict()
        self.params.startDate = lastweek
        self.params.product = 'Firefox'
        self.params.version = '8.0'
        self.params.limit = 100
        self.params.to_date = yesterday
        self.params.date_range_type = None
        self.params.duration = datetime.timedelta(7)
        self.params.os = None
        self.params.crash_type = 'all'
        self.params.logger = mock.Mock()

        cursor.execute("""
            INSERT INTO signatures
            (signature_id, signature, first_report)
            VALUES
            (1, 'Fake Signature #1', '%(first_date)s'),
            (2, 'Fake Signature #2', '%(first_date)s'),
            (3, 'Fake Signature #3', '%(first_date)s');
        """ % {'first_date': lastweek})

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name)
            VALUES
            ('Firefox', 1, '8.0', 'firefox'),
            ('Fennec', 2, '11.0', 'mobile');
        """)

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Release', 1);
        """)

        cursor.execute("""
            INSERT INTO product_versions
            (product_version_id, product_name, major_version, release_version,
             version_string, build_date, sunset_date, featured_version,
             build_type)
            VALUES
            (
                1,
                'Firefox',
                '8.0',
                '8.0',
                '8.0',
                '%(start_date)s',
                '%(end_date)s',
                False,
                'Release'
            ),
            (
                2,
                'Fennec',
                '11.0',
                '11.0',
                '11.0.1',
                '%(start_date)s',
                '%(end_date)s',
                False,
                'Release'
            );
        """ % {'start_date': self.now - datetime.timedelta(days=8),
               'end_date': self.now})

        cursor.execute("""
            INSERT INTO signature_products_rollup
            (signature_id, product_name, ver_count, version_list)
            VALUES
            (
                1,
                'Firefox',
                2,
                '{plugin1, plugin2}'
            ),
            (
                2,
                'Firefox',
                6,
                '{plugin1, plugin2, plugin3, plugin4, plugin5, plugin6}'
            ),
            (
                3,
                'Fennec',
                3,
                '{plugin1, plugin2}'
            );
        """)

        cursor.execute("""
            INSERT INTO tcbs
            (
                signature_id,
                report_date,
                product_version_id,
                process_type,
                release_channel,
                report_count,
                win_count,
                mac_count,
                lin_count,
                hang_count,
                is_gc_count
            )
            VALUES
            (1, '%(lastweek)s', 1, 'type', 'Release', 14, 12, 1, 1, 0, 1),
            (2, '%(now)s', 1, 'crash', 'Release', 3, 1, 1, 1, 0, 1),
            (1, '%(now)s', 1, 'hang', 'Release', 5, 0, 0, 5, 5, 10),
            (2, '%(lastweek)s', 1, 'crash', 'Release', 10, 7, 2, 1, 0, 3);
        """ % {'now': self.now,
               'lastweek': self.now - datetime.timedelta(days=8)})

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """

        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE tcbs, signature_products_rollup, product_versions,
                     products, release_channels, signatures
            CASCADE;
        """)
        self.connection.commit()

        super(IntegrationTestTCBS, self).tearDown()

    #--------------------------------------------------------------------------
    def test_getListOfTopCrashersBySignature(self):

        lastweek = self.now.date() - datetime.timedelta(days=7)
        params = self.params
        params.startDate = self.now.date() - datetime.timedelta(days=8)

        res = tcbs.getListOfTopCrashersBySignature(
            self.connection,
            self.params
        )

        sig_1 = res.next()
        sig_2 = res.next()
        self.assertEqual(sig_1[0], "Fake Signature #1")
        self.assertEqual(sig_2[0], "Fake Signature #2")
        self.assertEqual(sig_1[8].date(), lastweek)
        self.assertEqual(sig_2[8].date(), lastweek)
        self.assertEqual(sig_1[10], 0.58333333333333304)
        self.assertEqual(sig_2[10], 0.41666666666666702)
        self.assertRaises(StopIteration, res.next)

        # Test if raises ValueError when are passed wrong parameters
        params.product = None
        self.assertRaises(
            ValueError,
            tcbs.getListOfTopCrashersBySignature,
            self.connection,
            params
        )

    #--------------------------------------------------------------------------
    def test_rangeOfQueriesGenerator(self):

        lastweek = self.now.date() - datetime.timedelta(days=7)

        query_list = tcbs.getListOfTopCrashersBySignature
        res = tcbs.rangeOfQueriesGenerator(
            self.connection,
            self.params,
            query_list
        )

        generate = res.next()
        sig_1 = generate.next()
        sig_2 = generate.next()
        self.assertEqual(sig_1[0], "Fake Signature #1")
        self.assertEqual(sig_2[0], "Fake Signature #2")
        self.assertEqual(sig_1[8].date(), lastweek)
        self.assertEqual(sig_2[8].date(), lastweek)
        self.assertEqual(sig_1[10], 0.625)
        self.assertEqual(sig_2[10], 0.375)
        self.assertRaises(StopIteration, generate.next)

    #--------------------------------------------------------------------------
    def test_listOfListsWithChangeInRank(self):

        lastweek = self.now - datetime.timedelta(days=7)
        lastweek_str = datetimeutil.date_to_string(lastweek.date())

        params = self.params
        params.startDate = self.now.date() - datetime.timedelta(days=14)

        query_list = tcbs.getListOfTopCrashersBySignature
        query_range = tcbs.rangeOfQueriesGenerator(
            self.connection,
            self.params,
            query_list
        )
        res = tcbs.listOfListsWithChangeInRank(query_range)

        res_expected = [[{
            'count': 5L,
            'mac_count': 0L,
            'content_count': 0,
            'first_report': lastweek_str,
            'previousRank': 0,
            'currentRank': 0,
            'startup_percent': None,
            'versions': 'plugin1, plugin2',
            'first_report_exact': lastweek_str + ' 00:00:00',
            'percentOfTotal': 0.625,
            'changeInRank': 0,
            'is_gc_count': 10L,
            'win_count': 0L,
            'changeInPercentOfTotal': 0.041666666666666963,
            'linux_count': 5L,
            'hang_count': 5L,
            'signature': 'Fake Signature #1',
            'versions_count': 2,
            'previousPercentOfTotal': 0.58333333333333304,
            'plugin_count': 0
        }, {
            'count': 3L,
            'mac_count': 1L,
            'content_count': 0,
            'first_report': lastweek_str,
            'previousRank': 1,
            'currentRank': 1,
            'startup_percent': None,
            'versions': 'plugin1, plugin2, plugin3, plugin4, plugin5, plugin6',
            'first_report_exact': lastweek_str + ' 00:00:00',
            'percentOfTotal': 0.375,
            'changeInRank': 0,
            'is_gc_count': 1L,
            'win_count': 1L,
            'changeInPercentOfTotal': -0.041666666666667018,
            'linux_count': 1L,
            'hang_count': 0L,
            'signature': 'Fake Signature #2',
            'versions_count': 6,
            'previousPercentOfTotal': 0.41666666666666702,
            'plugin_count': 0
        }]]

        self.assertEqual(res, res_expected)

    #--------------------------------------------------------------------------
    def test_latestEntryBeforeOrEqualTo(self):

        product = 'Firefox'
        version = '8.0'
        now = self.now.date()
        to_date = now - datetime.timedelta(days=1)
        lastweek = now - datetime.timedelta(days=7)

        res = tcbs.latestEntryBeforeOrEqualTo(
            self.connection,
            to_date,
            product,
            version
        )
        self.assertEqual(res, lastweek)

    #--------------------------------------------------------------------------
    def test_twoPeriodTopCrasherComparison(self):

        lastweek = self.now - datetime.timedelta(days=7)
        lastweek_str = datetimeutil.date_to_string(lastweek.date())
        two_weeks = datetimeutil.date_to_string(self.now.date() -
                                                datetime.timedelta(days=14))

        res = tcbs.twoPeriodTopCrasherComparison(
            self.connection,
            self.params
        )

        res_expected = {
            'totalPercentage': 1.0,
            'end_date': lastweek_str,
            'start_date': two_weeks,
            'crashes': [{
                'count': 14L,
                'mac_count': 1L,
                'content_count': 0,
                'first_report': lastweek_str,
                'previousRank': 'null',
                'currentRank': 0,
                'startup_percent': None,
                'versions': 'plugin1, plugin2',
                'first_report_exact': lastweek_str + ' 00:00:00',
                'percentOfTotal': 0.58333333333333304,
                'changeInRank': 'new',
                'is_gc_count': 1L,
                'win_count': 12L,
                'changeInPercentOfTotal': 'new',
                'linux_count': 1L,
                'hang_count': 0L,
                'signature': 'Fake Signature #1',
                'versions_count': 2,
                'previousPercentOfTotal': 'null',
                'plugin_count': 0
            }, {
                'count': 10L,
                'mac_count': 2L,
                'content_count': 0,
                'first_report': lastweek_str,
                'previousRank': 'null',
                'currentRank': 1,
                'startup_percent': None,
                'versions': 'plugin1, plugin2, plugin3, '
                            'plugin4, plugin5, plugin6',
                'first_report_exact': lastweek_str + ' 00:00:00',
                'percentOfTotal': 0.41666666666666702,
                'changeInRank': 'new',
                'is_gc_count': 3L,
                'win_count': 7L,
                'changeInPercentOfTotal': 'new',
                'linux_count': 1L,
                'hang_count': 0L,
                'signature': 'Fake Signature #2',
                'versions_count': 6,
                'previousPercentOfTotal': 'null',
                'plugin_count': 0
            }],
            'totalNumberOfCrashes': 24L
        }

        self.assertEqual(res, res_expected)

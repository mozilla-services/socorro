# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external import MissingArgumentError
from socorro.external.postgresql.crashes import Crashes
from socorro.lib import datetimeutil

from .unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestCrashesSignatures(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crashes.Crashes.get_signatures method.

    Although it tests a method of the Crashes class, this test is not in
    test_crashes.py. This is because it has a lot of lines of code and thus is
    better on its own here.
    """

    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestCrashesSignatures, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        self.now = datetimeutil.utc_now()
        today = datetime.datetime(
            self.now.year,
            self.now.month,
            self.now.day
        )

        cursor.execute("""
            INSERT INTO signatures
            (signature_id, signature, first_report)
            VALUES
            (1, 'signature1', '%(first_date)s'),
            (2, 'signature2', '%(first_date)s'),
            (3, 'signature3', '%(first_date)s'),
            (4, 'signature4', '%(first_date)s');
        """ % {'first_date': today - datetime.timedelta(days=7)})

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
                2,
                '11.0',
                'mobile'
            );
        """)

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            (
                'Release', 1
            );
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
        """ % {'start_date': self.now - datetime.timedelta(weeks=4),
               'end_date': self.now + datetime.timedelta(weeks=4)})

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
                2,
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
            (
                1,
                '%(now)s',
                1,
                'type',
                'Release',
                14,
                12,
                1,
                1,
                0,
                1
            ),
            (
                2,
                '%(now)s',
                1,
                'crash',
                'Release',
                3,
                1,
                1,
                1,
                0,
                1
            ),
            (
                1,
                '%(now)s',
                1,
                'hang',
                'Release',
                5,
                0,
                0,
                5,
                5,
                10
            ),
            (
                1,
                '%(lastweek)s',
                1,
                'crash',
                'Release',
                10,
                7,
                2,
                1,
                0,
                3
            ),
            (
                3,
                '%(now)s',
                2,
                'plugin',
                'Release',
                14,
                12,
                1,
                1,
                0,
                4
            );
        """ % {
            'now': self.now,
            'lastweek': self.now - datetime.timedelta(days=8)
        })

        cursor.execute("""
            INSERT INTO tcbs_build
            (
                signature_id,
                build_date,
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
            (
                1,
                '%(now)s',
                '%(now)s',
                1,
                'type',
                'Release',
                14,
                12,
                1,
                1,
                0,
                3
            ),
            (
                2,
                '%(now)s',
                '%(now)s',
                1,
                'crash',
                'Release',
                3,
                1,
                1,
                1,
                0,
                1
            ),
            (
                1,
                '%(now)s',
                '%(now)s',
                1,
                'hang',
                'Release',
                5,
                0,
                0,
                5,
                5,
                2
            ),
            (
                1,
                '%(lastweek)s',
                '%(lastweek)s',
                1,
                'crash',
                'Release',
                10,
                7,
                2,
                1,
                0,
                2
            ),
            (
                3,
                '%(yesterday)s',
                '%(now)s',
                2,
                'plugin',
                'Release',
                14,
                12,
                1,
                1,
                0,
                10
            );
        """ % {
            'now': self.now,
            'lastweek': self.now - datetime.timedelta(days=8),
            'yesterday': self.now - datetime.timedelta(days=1)
        })

        self.connection.commit()

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE tcbs, tcbs_build, product_versions, products,
                     release_channels, signatures
            CASCADE;
        """)
        self.connection.commit()
        super(IntegrationTestCrashesSignatures, self).tearDown()

    def test_get_signatures(self):
        tcbs = Crashes(config=self.config)
        now = self.now
        today = datetime.datetime(now.year, now.month, now.day)
        lastweek = today - datetime.timedelta(days=7)

        tomorrow_str = (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        sixdaysago_str = (lastweek + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        lastweek_str = lastweek.strftime('%Y-%m-%d')
        lastweek_str_full = lastweek.strftime('%Y-%m-%d %H:%M:%S')

        # Test 1: all TCBS for Firefox
        params = {
            "product": "Firefox",
            "version": "8.0"
        }
        res = tcbs.get_signatures(**params)
        res_expected = {
            'totalPercentage': 1.0,
            'end_date': tomorrow_str,
            'start_date': sixdaysago_str,
            'crashes': [
                {
                    'count': 19L,
                    'mac_count': 1L,
                    'content_count': 0,
                    'first_report': lastweek_str,
                    'previousRank': 0,
                    'currentRank': 0,
                    'startup_percent': None,
                    'versions': 'plugin1, plugin2',
                    'first_report_exact': lastweek_str_full,
                    'percentOfTotal': 0.86363636363636398,
                    'changeInRank': 0,
                    'win_count': 12L,
                    'changeInPercentOfTotal': -0.13636363636363602,
                    'linux_count': 6L,
                    'hang_count': 5L,
                    'signature': 'signature1',
                    'versions_count': 2,
                    'previousPercentOfTotal': 1.0,
                    'plugin_count': 0,
                    'is_gc_count': 11L
                },
                {
                    'count': 3L,
                    'mac_count': 1L,
                    'content_count': 0,
                    'first_report': lastweek_str,
                    'previousRank': 'null',
                    'currentRank': 1,
                    'startup_percent': None,
                    'versions': 'plugin1, plugin2, plugin3, plugin4, plugin5, plugin6',
                    'first_report_exact': lastweek_str_full,
                    'percentOfTotal': 0.13636363636363599,
                    'changeInRank': 'new',
                    'win_count': 1L,
                    'changeInPercentOfTotal': 'new',
                    'linux_count': 1L,
                    'hang_count': 0L,
                    'signature': 'signature2',
                    'versions_count': 6,
                    'previousPercentOfTotal': 'null',
                    'plugin_count': 0,
                    'is_gc_count': 1L
                }
            ],
            'totalNumberOfCrashes': 22L
        }

        self.assertEqual(res, res_expected)

        # Test 2: Limit to one crash type
        params = {
            "product": "Firefox",
            "version": "8.0",
            "crash_type": "hang"
        }
        res = tcbs.get_signatures(**params)
        res_expected = {
            'totalPercentage': 1.0,
            'end_date': tomorrow_str,
            'start_date': sixdaysago_str,
            'crashes': [
                {
                    'count': 5L,
                    'mac_count': 0L,
                    'content_count': 0,
                    'first_report': lastweek_str,
                    'previousRank': 'null',
                    'currentRank': 0,
                    'startup_percent': None,
                    'versions': 'plugin1, plugin2',
                    'first_report_exact': lastweek_str_full,
                    'percentOfTotal': 1.0,
                    'changeInRank': 'new',
                    'win_count': 0L,
                    'changeInPercentOfTotal': 'new',
                    'linux_count': 5L,
                    'hang_count': 5L,
                    'signature': 'signature1',
                    'versions_count': 2,
                    'previousPercentOfTotal': 'null',
                    'plugin_count': 0,
                    'is_gc_count': 10L
                }
            ],
            'totalNumberOfCrashes': 5L
        }

        self.assertEqual(res, res_expected)

        # Test 3: Limit to one OS
        params = {
            "product": "Firefox",
            "version": "8.0",
            "os": "Windows"
        }
        res = tcbs.get_signatures(**params)
        res_expected = {
            'totalPercentage': 0.76470588235294168,
            'end_date': tomorrow_str,
            'start_date': sixdaysago_str,
            'crashes': [
                {
                    'count': 14L,
                    'mac_count': 1L,
                    'content_count': 0,
                    'first_report': lastweek_str,
                    'previousRank': 0,
                    'currentRank': 0,
                    'startup_percent': None,
                    'versions': 'plugin1, plugin2',
                    'first_report_exact': lastweek_str_full,
                    'percentOfTotal': 0.70588235294117696,
                    'changeInRank': 0,
                    'win_count': 12L,
                    'changeInPercentOfTotal': 0.0058823529411770048,
                    'linux_count': 1L,
                    'hang_count': 0L,
                    'signature': 'signature1',
                    'versions_count': 2,
                    'previousPercentOfTotal': 0.69999999999999996,
                    'plugin_count': 0,
                    'is_gc_count': 1L
                },
                {
                    'count': 3L,
                    'mac_count': 1L,
                    'content_count': 0,
                    'first_report': lastweek_str,
                    'previousRank': 'null',
                    'currentRank': 1,
                    'startup_percent': None,
                    'versions': 'plugin1, plugin2, plugin3, plugin4, plugin5, plugin6',
                    'first_report_exact': lastweek_str_full,
                    'percentOfTotal': 0.058823529411764698,
                    'changeInRank': 'new',
                    'win_count': 1L,
                    'changeInPercentOfTotal': 'new',
                    'linux_count': 1L,
                    'hang_count': 0L,
                    'signature': 'signature2',
                    'versions_count': 6,
                    'previousPercentOfTotal': 'null',
                    'plugin_count': 0,
                    'is_gc_count': 1L
                }
            ],
            'totalNumberOfCrashes': 17L
        }

        self.assertEqual(res, res_expected)

        # Test 4: No results
        params = {
            "product": "Unknown",
            "version": "8.0",
        }
        res = tcbs.get_signatures(**params)

        self.assertTrue('totalNumberOfCrashes' in res)
        self.assertEqual(res['totalNumberOfCrashes'], 0)
        self.assertEqual(res['crashes'], [])

        # Test 5: Results ranged by build date
        params = {
            "product": "Fennec",
            "version": "11.0.1",
            "date_range_type": "build"
        }
        res = tcbs.get_signatures(**params)
        res_expected = {
            'totalPercentage': 1.0,
            'end_date': tomorrow_str,
            'start_date': sixdaysago_str,
            'crashes': [
                {
                    'count': 14L,
                    'mac_count': 1L,
                    'content_count': 0,
                    'first_report': lastweek_str,
                    'previousRank': 'null',
                    'currentRank': 0,
                    'startup_percent': None,
                    'versions': 'plugin1, plugin2',
                    'first_report_exact': lastweek_str_full,
                    'percentOfTotal': 1.0,
                    'changeInRank': 'new',
                    'win_count': 12L,
                    'changeInPercentOfTotal': 'new',
                    'linux_count': 1L,
                    'hang_count': 0L,
                    'signature': 'signature3',
                    'versions_count': 2,
                    'previousPercentOfTotal': 'null',
                    'plugin_count': 14,
                    'is_gc_count': 10L
                }
            ],
            'totalNumberOfCrashes': 14L
        }

        self.assertEqual(res, res_expected)

    def test_get_signature_history(self):
        api = Crashes(config=self.config)
        now = self.now
        lastweek = now - datetime.timedelta(days=7)

        params = {
            'product': 'Firefox',
            'version': '8.0',
            'signature': 'signature1',
            'start_date': lastweek,
            'end_date': now,
        }
        res = api.get_signature_history(**params)

        self.assertEqual(len(res['hits']), 2)
        self.assertEqual(len(res['hits']), res['total'])

        date = datetimeutil.date_to_string(now.date())
        self.assertEqual(res['hits'][0]['date'], date)
        self.assertEqual(res['hits'][1]['date'], date)

        self.assertEqual(res['hits'][0]['count'], 5)
        self.assertEqual(res['hits'][1]['count'], 14)

        self.assertEqual(
            round(res['hits'][0]['percent_of_total'], 2),
            round(5.0 / 19.0 * 100, 2)
        )
        self.assertEqual(
            round(res['hits'][1]['percent_of_total'], 2),
            round(14.0 / 19.0 * 100, 2)
        )

        # Test no results
        params = {
            'product': 'Firefox',
            'version': '9.0',
            'signature': 'signature1',
            'start_date': lastweek,
            'end_date': now,
        }
        res = api.get_signature_history(**params)
        res_expected = {
            'hits': [],
            'total': 0
        }
        self.assertEqual(res, res_expected)

        # Test default date parameters
        params = {
            'product': 'Fennec',
            'version': '11.0.1',
            'signature': 'signature3',
        }
        res = api.get_signature_history(**params)
        res_expected = {
            'hits': [
                {
                    'date': now.date().isoformat(),
                    'count': 14,
                    'percent_of_total': 100
                }
            ],
            'total': 1
        }
        self.assertEqual(res, res_expected)

        # Test missing parameters
        self.assertRaises(
            MissingArgumentError,
            api.get_signature_history
        )
        self.assertRaises(
            MissingArgumentError,
            api.get_signature_history,
            **{'product': 'Firefox'}
        )
        self.assertRaises(
            MissingArgumentError,
            api.get_signature_history,
            **{'product': 'Firefox', 'version': '8.0'}
        )
        self.assertRaises(
            MissingArgumentError,
            api.get_signature_history,
            **{'signature': 'signature1', 'version': '8.0'}
        )

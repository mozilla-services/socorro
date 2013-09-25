# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external.postgresql.report import Report
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestReport(PostgreSQLTestCase):
    """Test socorro.external.postgresql.report.Report class. """

    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestReport, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        self.now = datetimeutil.utc_now()
        yesterday = self.now - datetime.timedelta(days=1)

        cursor.execute("""
            INSERT INTO reports
            (
                id,
                uuid,
                date_processed,
                product,
                version,
                build,
                signature,
                reason,
                os_name,
                hangid,
                process_type,
                release_channel
            )
            VALUES
            (
                1,
                '1',
                '%(yesterday)s',
                'WaterWolf',
                '1.0',
                '20001212010203',
                'sig1',
                'STACK_OVERFLOW',
                'Linux',
                1,
                'browser',
                'Release'
            ),
            (
                2,
                '2',
                '%(yesterday)s',
                'WaterWolf',
                '2.0',
                '20001212010204',
                'sig1',
                'SIGFAULT',
                'Windows NT',
                2,
                'browser',
                'Release'
            ),
            (
                3,
                '3',
                '%(yesterday)s',
                'WaterWolf',
                '1.0',
                '20001212010205',
                'sig1',
                'BIG_FAILURE',
                'Windows NT',
                null,
                'plugin',
                'Release'
            ),
            (
                4,
                '4',
                '%(yesterday)s',
                'WaterWolf',
                '1.0',
                '20001212010203',
                'sig1',
                'STACK_OVERFLOW',
                'Windows NT',
                null,
                'browser',
                'Release'
            ),
            (
                5,
                '5',
                '%(yesterday)s',
                'WaterWolf',
                '1.0',
                '20001212010203',
                'sig2',
                'STACK_OVERFLOW',
                'Linux',
                null,
                'browser',
                'Release'
            ),
            (
                6,
                '6',
                '%(yesterday)s',
                'WaterWolf',
                '3.0',
                '20001212010203',
                'sig2',
                'STACK_OVERFLOW',
                'Linux',
                null,
                'browser',
                'Release'
            ),
            (
                7,
                '7',
                '%(yesterday)s',
                'WaterWolf',
                '3.0',
                '20001212010203',
                'sig1',
                'STACK_OVERFLOW',
                'Windows NT',
                null,
                'plugin',
                'Release'
            ),
            (
                8,
                '8',
                '%(yesterday)s',
                'WaterWolf',
                '1.0',
                '20001212010204',
                'sig3',
                'STACK_OVERFLOW',
                'Linux',
                null,
                'browser',
                'Release'
            ),
            (
                9,
                '9',
                '%(yesterday)s',
                'NightlyTrain',
                '1.0',
                '20001212010203',
                'js::functions::call::hello_world',
                'SIGFAULT',
                'Linux',
                null,
                'browser',
                'Release'
            ),
            (
                10,
                '10',
                '%(yesterday)s',
                'WindBear',
                '1.0',
                '20001212010203',
                'this/is+a=C|signature',
                'STACK_OVERFLOW',
                'Linux',
                null,
                'browser',
                'Release'
            );
        """ % {
            'yesterday': yesterday
        })

        cursor.execute("""
            INSERT INTO plugins_reports
            (
                report_id,
                plugin_id,
                date_processed,
                version
            )
            VALUES
            (
                3,
                1,
                '%(yesterday)s',
                '1.23.001'
            ),
            (
                7,
                2,
                '%(yesterday)s',
                '2.0.1'
            );
        """ % {
            'yesterday': yesterday
        })

        cursor.execute("""
            INSERT INTO plugins
            (
                id,
                filename,
                name
            )
            VALUES
            (
                1,
                'flash.dll',
                'Flash'
            ),
            (
                2,
                'NPSWF32_11_5_502_146.dll',
                'someplugin'
            );
        """)

        self.connection.commit()

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE reports, plugins_reports, plugins
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestReport, self).tearDown()

    def test_get_list(self):
        now = self.now
        yesterday = now - datetime.timedelta(days=1)
        yesterday = datetimeutil.date_to_string(yesterday)
        report = Report(config=self.config)

        # Test 1
        params = {
            'signature': 'sig1'
        }
        res = report.get_list(**params)
        self.assertEqual(res['total'], 5)

        # Test 2
        params = {
            'signature': 'sig1',
            'products': 'WaterWolf',
            'versions': 'WaterWolf:2.0'
        }
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

        # Test 3
        params = {
            'signature': 'sig1',
            'products': 'WaterWolf',
            'versions': ['WaterWolf:1.0', 'WaterWolf:3.0'],
            'os': 'win',
            'build_ids': '20001212010203',
            'reasons': 'STACK_OVERFLOW'
        }
        res = report.get_list(**params)
        self.assertEqual(res['total'], 2)

        res_expected = {
            'hits': [
                {
                    'hangid': None,
                    'product': 'WaterWolf',
                    'os_name': 'Windows NT',
                    'uuid': '4',
                    'cpu_info': None,
                    'url': None,
                    'last_crash': None,
                    'date_processed': yesterday,
                    'cpu_name': None,
                    'uptime': None,
                    'process_type': 'browser',
                    'os_version': None,
                    'reason': 'STACK_OVERFLOW',
                    'version': '1.0',
                    'build': '20001212010203',
                    'install_age': None,
                    'signature': 'sig1',
                    'install_time': None,
                    'duplicate_of': None,
                    'address': None,
                    'user_comments': None
                },
                {
                    'hangid': None,
                    'product': 'WaterWolf',
                    'os_name': 'Windows NT',
                    'uuid': '7',
                    'cpu_info': None,
                    'url': None,
                    'last_crash': None,
                    'date_processed': yesterday,
                    'cpu_name': None,
                    'uptime': None,
                    'process_type': 'plugin',
                    'os_version': None,
                    'reason': 'STACK_OVERFLOW',
                    'version': '3.0',
                    'build': '20001212010203',
                    'install_age': None,
                    'signature': 'sig1',
                    'install_time': None,
                    'duplicate_of': None,
                    'address': None,
                    'user_comments': None
                }
            ],
            'total': 2
        }
        self.assertEqual(res, res_expected)

        # Test 5
        params = {
            'signature': 'this/is+a=C|signature'
        }
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

        res_expected = {
            'hits': [{
                'hangid': None,
                'product': 'WindBear',
                'os_name': 'Linux',
                'uuid': '10',
                'cpu_info': None,
                'url': None,
                'last_crash': None,
                'date_processed': yesterday,
                'cpu_name': None,
                'uptime': None,
                'process_type': 'browser',
                'os_version': None,
                'reason': 'STACK_OVERFLOW',
                'version': '1.0',
                'build': '20001212010203',
                'install_age': None,
                'signature': 'this/is+a=C|signature',
                'install_time': None,
                'duplicate_of': None,
                'address': None,
                'user_comments': None
            }],
            'total': 1
        }
        self.assertEqual(res, res_expected)

        # Test 6: plugins
        params = {
            'signature': 'sig1',
            'report_process': 'plugin',
            'plugin_in': 'filename',
            'plugin_terms': 'NPSWF',
            'plugin_search_mode': 'contains',
        }
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

        # Test 7: plugins
        params = {
            'signature': 'sig1',
            'report_process': 'plugin',
            'plugin_in': 'name',
            'plugin_terms': 'Flash',
            'plugin_search_mode': 'starts_with',
        }
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

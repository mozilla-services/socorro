# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external.postgresql.search import Search
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestSearch(PostgreSQLTestCase):
    """Test socorro.external.postgresql.search.Search class. """

    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestSearch, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        now = datetimeutil.utc_now()
        self.yesterday = now - datetime.timedelta(days=1)
        self.twodaysago = self.yesterday - datetime.timedelta(days=1)

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
                '%(twodaysago)s',
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
                'Windows NT',
                null,
                'browser',
                'Release'
            ),
            (
                7,
                '7',
                '%(yesterday)s',
                'NightlyTrain',
                '1.0',
                '20001212010203',
                'sig2',
                'STACK_OVERFLOW',
                'Linux',
                null,
                'plugin',
                'Nightly'
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
                '%(twodaysago)s',
                'NightlyTrain',
                '1.0',
                '20001212010203',
                'js::functions::call::hello_world',
                'SIGFAULT',
                'Linux',
                null,
                'browser',
                'Nightly'
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
            'yesterday': self.yesterday,
            'twodaysago': self.twodaysago
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
            'yesterday': self.yesterday
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
        super(IntegrationTestSearch, self).tearDown()

    def test_get(self):
        search = Search(config=self.config)

        # Test 1
        params = {}
        res = search.get(**params)
        self.assertEqual(res['total'], 5)

        # Test 2
        params = {
            'products': 'WaterWolf'
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 3)

        # Test 3
        params = {
            'products': 'WaterWolf',
            'versions': 'WaterWolf:2.0'
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 1)

        # Test 4
        params = {
            'products': 'WaterWolf',
            'versions': ['WaterWolf:1.0', 'WaterWolf:3.0'],
            'os': 'win',
            'build_ids': '20001212010203',
            'reasons': 'STACK_OVERFLOW'
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 2)

        res_expected = {
            'hits': [{
                'signature': 'sig1',
                'count': 1,
                'is_windows': 1,
                'is_linux': 0,
                'is_mac': 0,
                'numhang': 0,
                'numplugin': 0,
                'numcontent': 0
            },
            {
                'signature': 'sig2',
                'count': 1,
                'is_windows': 1,
                'is_linux': 0,
                'is_mac': 0,
                'numhang': 0,
                'numplugin': 0,
                'numcontent': 0
            }],
            'total': 2
        }
        self.assertEqual(res, res_expected)

        # Test 5
        params = {
            'terms': 'sig1'
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 1)

        res_expected = {
            'hits': [{
                'signature': 'sig1',
                'count': 4,
                'is_windows': 3,
                'is_linux': 1,
                'is_mac': 0,
                'numhang': 2,
                'numplugin': 1,
                'numcontent': 0
            }],
            'total': 1
        }
        self.assertEqual(res, res_expected)

        # with parameters renaming
        params = {
            'for': 'sig1'
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 1)
        self.assertEqual(res, res_expected)

        # Test 6: plugins
        params = {
            'report_process': 'plugin',
            'plugin_in': 'filename',
            'plugin_terms': 'NPSWF',
            'plugin_search_mode': 'contains',
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 1)

        hits = res['hits'][0]
        self.assertEqual(hits['count'], 1)
        self.assertEqual(hits['pluginfilename'], 'NPSWF32_11_5_502_146.dll')

        # Test 7: plugins
        params = {
            'report_process': 'plugin',
            'plugin_in': 'name',
            'plugin_terms': 'Flash',
            'plugin_search_mode': 'starts_with',
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 1)

        hits = res['hits'][0]
        self.assertEqual(hits['count'], 1)
        self.assertEqual(hits['pluginname'], 'Flash')

        # Test 8: parameters renaming
        params = {
            'to_date': self.twodaysago
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 2)

        res_expected = {
            'hits': [{
                'signature': 'js::functions::call::hello_world',
                'count': 1,
                'is_windows': 0,
                'is_linux': 1,
                'is_mac': 0,
                'numhang': 0,
                'numplugin': 0,
                'numcontent': 0
            },{
                'signature': 'sig1',
                'count': 1,
                'is_windows': 1,
                'is_linux': 0,
                'is_mac': 0,
                'numhang': 1,
                'numplugin': 0,
                'numcontent': 0
            }],
            'total': 2
        }
        self.assertEqual(res, res_expected)

        # with parameter renaming
        params = {
            'to': self.twodaysago
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 2)
        self.assertEqual(res, res_expected)

        # Test 9: release channels
        params = {
            'release_channels': ['Nightly']
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 2)

        hits = res['hits'][0]
        self.assertEqual(hits['signature'], 'js::functions::call::hello_world')
        hits = res['hits'][1]
        self.assertEqual(hits['signature'], 'sig2')

        # verify that several values work, verify that it's case insensitive
        params = {
            'release_channels': ['NiGhTlY', 'release']
        }
        res = search.get(**params)
        self.assertEqual(res['total'], 5)

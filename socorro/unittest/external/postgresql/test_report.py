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
                '60597bdc-5dbe-4409-6b38-4309c0130828',
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
                '60597bdc-5dbe-4409-6b38-4309c0130829',
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
                '60597bdc-5dbe-4409-6b38-4309c0130830',
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
                '60597bdc-5dbe-4409-6b38-4309c0130831',
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
                '60597bdc-5dbe-4409-6b38-4309c0130832',
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
                '60597bdc-5dbe-4409-6b38-4309c0130833',
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
                '60597bdc-5dbe-4409-6b38-4309c0130834',
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
                '60597bdc-5dbe-4409-6b38-4309c0130835',
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
                '60597bdc-5dbe-4409-6b38-4309c0130836',
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
                '60597bdc-5dbe-4409-6b38-4309c0130837',
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
            INSERT INTO raw_crashes
            (
                uuid,
                date_processed,
                raw_crash
            )
            VALUES
            (
                UUID('60597bdc-5dbe-4409-6b38-4309c0130828'),
                '%(yesterday)s',
                '{"foo": "bar"}'
            ),
            (
                UUID('60597bdc-5dbe-4409-6b38-4309c0130829'),
                '%(yesterday)s',
                '{"Name": "Peter"}'
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

        cursor.execute("""
            INSERT INTO reports_duplicates
            (
                date_processed,
                uuid,
                duplicate_of
            )
            VALUES
            (
                '%(yesterday)s',
                '60597bdc-5dbe-4409-6b38-4309c0130828',
                '60597bdc-5dbe-4409-6b38-4309c0130833'
            );
        """ % {
            'yesterday': yesterday
        })
        self.connection.commit()

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE
              reports_duplicates,
              reports,
              plugins_reports,
              plugins,
              raw_crashes
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestReport, self).tearDown()

    def test_get_list(self):
        now = self.now
        yesterday = now - datetime.timedelta(days=1)
        yesterday = datetimeutil.date_to_string(yesterday)
        report = Report(config=self.config)

        base_params = {
            'signature': 'sig1',
            'from_date': yesterday,
            'to_date': now,
        }

        # Basic test
        res = report.get_list(**base_params)
        self.assertEqual(res['total'], 5)
        self.assertEqual(len(res['hits']), 5)

        duplicates_map = dict(
            (x['uuid'], x['duplicate_of']) for x in res['hits']
            if x['duplicate_of']
        )
        self.assertEqual(
            duplicates_map['60597bdc-5dbe-4409-6b38-4309c0130828'],
            '60597bdc-5dbe-4409-6b38-4309c0130833'
        )

        # Test with products and versions
        params = dict(
            base_params,
            products='WaterWolf',
            versions='WaterWolf:2.0',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

        # Test with os, build_ids and reasons
        params = dict(
            base_params,
            products='WaterWolf',
            versions=['WaterWolf:1.0', 'WaterWolf:3.0'],
            os='win',
            build_ids='20001212010203',
            reasons='STACK_OVERFLOW',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 2)

        res_expected = {
            'hits': [
                {
                    'hangid': None,
                    'product': 'WaterWolf',
                    'os_name': 'Windows NT',
                    'uuid': '60597bdc-5dbe-4409-6b38-4309c0130831',
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
                    'uuid': '60597bdc-5dbe-4409-6b38-4309c0130834',
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

        # Test with a signature with strange characters
        params = dict(
            base_params,
            signature='this/is+a=C|signature',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

        res_expected = {
            'hits': [{
                'hangid': None,
                'product': 'WindBear',
                'os_name': 'Linux',
                'uuid': '60597bdc-5dbe-4409-6b38-4309c0130837',
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

        # Test plugins
        params = dict(
            base_params,
            report_process='plugin',
            plugin_in='filename',
            plugin_terms='NPSWF',
            plugin_search_mode='contains',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

        # Test plugins with 'starts_with' search mode
        params = dict(
            base_params,
            report_process='plugin',
            plugin_in='name',
            plugin_terms='Flash',
            plugin_search_mode='starts_with',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)

    def test_get_list_with_raw_crash(self):
        now = self.now
        yesterday = now - datetime.timedelta(days=1)
        #yesterday = datetimeutil.date_to_string(yesterday)
        report = Report(config=self.config)
        base_params = {
            'signature': 'sig1',
            'from_date': yesterday,
            'to_date': now,
            'include_raw_crash': True
        }

        # Basic test
        res = report.get_list(**base_params)
        self.assertEqual(res['total'], 5)
        self.assertEqual(len(res['hits']), 5)

        duplicates_map = dict(
            (x['uuid'], x['duplicate_of']) for x in res['hits']
            if x['duplicate_of']
        )
        self.assertEqual(
            duplicates_map['60597bdc-5dbe-4409-6b38-4309c0130828'],
            '60597bdc-5dbe-4409-6b38-4309c0130833'
        )

        # two of them should have a raw crash
        self.assertEqual(
            len([x for x in res['hits'] if x['raw_crash'] is not None]),
            2
        )
        # the other 3 it's None
        self.assertEqual(
            len([x for x in res['hits'] if x['raw_crash'] is None]),
            3
        )

        # the two reports with raw crashes are known by the fixtures
        hits = [x for x in res['hits'] if x['raw_crash'] is not None]

        hit1, = [x for x in hits if x['reason'] == 'STACK_OVERFLOW']
        self.assertEqual(hit1['raw_crash'], {'foo': 'bar'})

        hit2, = [x for x in hits if x['reason'] == 'SIGFAULT']
        self.assertEqual(hit2['raw_crash'], {'Name': 'Peter'})

        # Test with products and versions
        params = dict(
            base_params,
            products='WaterWolf',
            versions='WaterWolf:2.0',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)
        self.assertEqual(len(res['hits']), 1)
        hit, = res['hits']
        self.assertEqual(hit['raw_crash'], {u'Name': u'Peter'})

        params = dict(
            base_params,
            products='WaterWolf',
            versions=['WaterWolf:1.0', 'WaterWolf:3.0'],
            os='win',
            build_ids='20001212010203',
            reasons='STACK_OVERFLOW',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 2)
        self.assertEqual(len(res['hits']), 2)
        hit1, hit2 = res['hits']
        self.assertEqual(hit1['raw_crash'], None)
        self.assertEqual(hit2['raw_crash'], None)

        # Test with os, build_ids and reasons
        params = dict(
            base_params,
            products='WaterWolf',
            versions=['WaterWolf:1.0', 'WaterWolf:3.0'],
            os='win',
            build_ids='20001212010203',
            reasons='STACK_OVERFLOW',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 2)
        self.assertEqual(len(res['hits']), 2)

        # Test plugins
        params = dict(
            base_params,
            report_process='plugin',
            plugin_in='filename',
            plugin_terms='NPSWF',
            plugin_search_mode='contains',
        )
        res = report.get_list(**params)
        self.assertEqual(res['total'], 1)
        self.assertEqual(len(res['hits']), 1)

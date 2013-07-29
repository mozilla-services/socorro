# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external.postgresql.signature_summary import SignatureSummary
from socorro.lib import datetimeutil

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestProducts(PostgreSQLTestCase):
    """Test socorro.external.postgresql.signature_summary.SignatureSummary class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate product_info table with fake data """
        super(IntegrationTestProducts, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        self.now = datetimeutil.utc_now()
        now = self.now.date()
        yesterday = now - datetime.timedelta(days=1)
        lastweek = now - datetime.timedelta(days=7)

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

        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            (
                'Release', 1
            ),
            (
                'Beta', 2
            );
        """)

        cursor.execute("""
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            (
                'Firefox', 'Release', '0.1'
            ),
            (
                'Fennec', 'Release', '0.1'
            ),
            (
                'Fennec', 'Beta', '1.0'
            ),
            (
                'Thunderbird', 'Release', '0.1'
            );
        """)

        # Insert versions, contains an expired version
        cursor.execute("""
            INSERT INTO product_versions
            (product_name, major_version, release_version, version_string,
             build_date, sunset_date, featured_version, build_type,
             version_sort)
            VALUES
            (
                'Firefox',
                '8.0',
                '8.0',
                '8.0',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '0008000'
            ),
            (
                'Firefox',
                '9.0',
                '9.0',
                '9.0',
                '%(lastweek)s',
                '%(lastweek)s',
                False,
                'Nightly',
                '0009000'
            ),
            (
                'Fennec',
                '11.0',
                '11.0',
                '11.0.1',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '0011001'
            ),
            (
                'Fennec',
                '12.0',
                '12.0',
                '12.0b1',
                '%(now)s',
                '%(now)s',
                False,
                'Beta',
                '00120b1'
            ),
            (
                'Thunderbird',
                '10.0',
                '10.0',
                '10.0.2b',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '001002b'
            );
        """ % {'now': now, 'lastweek': lastweek})

        cursor.execute("""
            INSERT INTO signatures
            (first_build, first_report, signature)
            VALUES
            ('20130701120000', '%(now)s', 'Fake Signature #1')
        """ % {'now': now})

        cursor.execute("SELECT signature_id FROM signatures WHERE signature = 'Fake Signature #1'")

        signature_id = cursor.fetchone()[0]

        cursor.execute("SELECT product_version_id FROM product_versions WHERE product_name = 'Firefox' and version_string = '8.0'")
        product_version_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO signature_summary_products
            (signature_id, product_version_id, product_name, version_string, report_date, report_count)
            VALUES
            (%(signature_id)s, %(product_version_id)s, 'Firefox', '8.0', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_architecture
            (signature_id, architecture, product_version_id, product_name, report_date, report_count)
            VALUES
            (%(signature_id)s, 'amd64', %(product_version_id)s, 'Firefox', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_flash_version
            (signature_id, flash_version, product_version_id, product_name, report_date, report_count)
            VALUES
            (%(signature_id)s, '1.0', %(product_version_id)s, 'Firefox', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_installations
            (signature_id, product_name, version_string, report_date, crash_count, install_count)
            VALUES
            (%(signature_id)s, 'Firefox', '8.0', '%(yesterday)s', 10, 8)
        """ % {'yesterday': yesterday,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_os
            (signature_id, os_version_string, product_version_id, product_name, report_date, report_count)
            VALUES
            (%(signature_id)s, 'Windows NT 6.4', %(product_version_id)s, 'Firefox', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_process_type
            (signature_id, process_type, product_version_id, product_name, report_date, report_count)
            VALUES
            (%(signature_id)s, 'plugin', %(product_version_id)s, 'Firefox', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_uptime
            (signature_id, uptime_string, product_version_id, product_name, report_date, report_count)
            VALUES
            (%(signature_id)s, '15-30 minutes', %(product_version_id)s, 'Firefox', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE products, product_version_builds, product_versions,
                     product_release_channels, release_channels,
                     product_versions,
                     signatures, signature_summary_products
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestProducts, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        signature_summary = SignatureSummary(config=self.config)
        now = self.now.date()
        lastweek = now - datetime.timedelta(days=7)
        now_str = datetimeutil.date_to_string(now)
        lastweek_str = datetimeutil.date_to_string(lastweek)

        #......................................................................
        # Test 1: find one exact match for one product version and signature
        params = {
            "versions": "Firefox:8.0",
            "report_type": "products",
            "signature": "Fake Signature #1",
            "start_date": lastweek_str,
            "end_date": now_str,
        }
        res = signature_summary.get(**params)
        res_expected = [
            {
                "product_name": 'Firefox',
                "version_string": "8.0",
                "report_count": 1.0,
                "percentage": 100.0,
             }
        ]

        self.assertEqual(
            sorted(res[0]),
            sorted(res_expected[0])
        )

        # Test 2: find architectures reported for a signature
        params = {
            "versions": "Firefox:8.0",
            "report_type": "architecture",
            "signature": "Fake Signature #1",
            "start_date": lastweek_str,
            "end_date": now_str,
        }
        res = signature_summary.get(**params)
        res_expected = [
            {
                "category": 'amd64',
                "report_count": 1.0,
                "percentage": 100.0,
             }
        ]

        self.assertEqual(
            sorted(res[0]),
            sorted(res_expected[0])
        )

        # Test 3: find flash_versions reported for a signature
        params = {
            "versions": "Firefox:8.0",
            "report_type": "flash_version",
            "signature": "Fake Signature #1",
            "start_date": lastweek_str,
            "end_date": now_str,
        }
        res = signature_summary.get(**params)
        res_expected = [
            {
                "category": '1.0',
                "report_count": 1.0,
                "percentage": 100.0,
             }
        ]

        self.assertEqual(
            sorted(res[0]),
            sorted(res_expected[0])
        )

        # Test 4: find installations reported for a signature
        params = {
            "versions": "Firefox:8.0",
            "report_type": "distinct_install",
            "signature": "Fake Signature #1",
            "start_date": lastweek_str,
            "end_date": now_str,
        }
        res = signature_summary.get(**params)
        res_expected = [
            {
                "product_name": 'Firefox',
                "version_string": '8.0',
                "crashes": 10,
                "installations": 8
             }
        ]

        self.assertEqual(
            sorted(res[0]),
            sorted(res_expected[0])
        )

        # Test 5: find os_version_strings reported for a signature
        params = {
            "versions": "Firefox:8.0",
            "report_type": "os",
            "signature": "Fake Signature #1",
            "start_date": lastweek_str,
            "end_date": now_str,
        }
        res = signature_summary.get(**params)
        res_expected = [
            {
                "category": 'Windows NT 6.4',
                "report_count": 1,
                "percentage": 100.0,
             }
        ]

        self.assertEqual(
            sorted(res[0]),
            sorted(res_expected[0])
        )

        # Test 6: find process_type reported for a signature
        params = {
            "versions": "Firefox:8.0",
            "report_type": "process_type",
            "signature": "Fake Signature #1",
            "start_date": lastweek_str,
            "end_date": now_str,
        }
        res = signature_summary.get(**params)
        res_expected = [
            {
                "category": 'plugin',
                "report_count": 1,
                "percentage": 100.0,
             }
        ]

        self.assertEqual(
            sorted(res[0]),
            sorted(res_expected[0])
        )

        # Test 7: find uptime reported for signature
        params = {
            "versions": "Firefox:8.0",
            "report_type": "uptime",
            "signature": "Fake Signature #1",
            "start_date": lastweek_str,
            "end_date": now_str,
        }
        res = signature_summary.get(**params)
        res_expected = [
            {
                "category": '15-30 minutes',
                "report_count": 1,
                "percentage": 100.0,
             }
        ]

        self.assertEqual(
            sorted(res[0]),
            sorted(res_expected[0])
        )

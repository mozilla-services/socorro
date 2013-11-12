# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external.postgresql.signature_summary import SignatureSummary
from socorro.lib import datetimeutil
from socorro.external import BadArgumentError

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestSignatureSummary(PostgreSQLTestCase):
    """Simple test of SignatureSummary class get() function"""

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate product_info table with fake data """
        super(IntegrationTestSignatureSummary, self).setUp()

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
            (product_version_id,
             product_name, major_version, release_version, version_string,
             build_date, sunset_date, featured_version, build_type,
             version_sort, has_builds, is_rapid_beta)
            VALUES
            (
                1,
                'Firefox',
                '8.0',
                '8.0',
                '8.0',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '0008000',
                True,
                False
            ),
            (
                2,
                'Firefox',
                '9.0',
                '9.0',
                '9.0',
                '%(lastweek)s',
                '%(lastweek)s',
                False,
                'Nightly',
                '0009000',
                True,
                False
            ),
            (
                3,
                'Fennec',
                '11.0',
                '11.0',
                '11.0.1',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '0011001',
                True,
                False
            ),
            (
                4,
                'Fennec',
                '12.0',
                '12.0',
                '12.0b1',
                '%(now)s',
                '%(now)s',
                False,
                'Beta',
                '00120b1',
                True,
                False
            ),
            (
                5,
                'Thunderbird',
                '10.0',
                '10.0',
                '10.0.2b',
                '%(now)s',
                '%(now)s',
                False,
                'Release',
                '001002b',
                True,
                False
            );
        """ % {'now': now, 'lastweek': lastweek})

        cursor.execute("""
            INSERT INTO signatures
            (first_build, first_report, signature)
            VALUES
            ('20130701120000', '%(now)s', 'Fake Signature #1')
        """ % {'now': now})

        cursor.execute("""
            SELECT signature_id FROM signatures
            WHERE signature = 'Fake Signature #1'
        """)

        signature_id = cursor.fetchone()[0]

        cursor.execute("""
            SELECT product_version_id
            FROM product_versions
            WHERE product_name = 'Firefox' and version_string = '8.0'
        """)
        product_version_id = cursor.fetchone()[0]

        cursor.execute("""
        SELECT product_version_id
        FROM product_versions
        WHERE product_name = 'Firefox' and version_string = '9.0'
        """)
        other_product_version_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO signature_summary_products
            (signature_id, product_version_id, product_name,
             version_string, report_date, report_count)
            VALUES
            (%(signature_id)s, %(product_version_id)s, 'Firefox',
             '8.0', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
           INSERT INTO signature_summary_products
           (signature_id, product_version_id, product_name,
            version_string, report_date, report_count)
           VALUES
           (%(signature_id)s, %(product_version_id)s, 'Firefox',
            '9.0', '%(yesterday)s', 1)
        """ % {'yesterday': yesterday,
               'product_version_id': other_product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_architecture
            (signature_id, architecture, product_version_id,
             product_name, report_date, report_count, version_string)
            VALUES
            (%(signature_id)s, 'amd64', %(product_version_id)s,
             'Firefox', '%(yesterday)s', 1, '8.0')
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
           INSERT INTO signature_summary_architecture
           (signature_id, architecture, product_version_id,
            product_name, report_date, report_count, version_string)
           VALUES
           (%(signature_id)s, 'amd64', %(product_version_id)s,
            'Firefox', '%(yesterday)s', 1, '9.0')
        """ % {'yesterday': yesterday,
               'product_version_id': other_product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_flash_version
            (signature_id, flash_version, product_version_id,
             product_name, report_date, report_count, version_string)
            VALUES
            (%(signature_id)s, '1.0', %(product_version_id)s,
             'Firefox', '%(yesterday)s', 1, '8.0')
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
           INSERT INTO signature_summary_flash_version
           (signature_id, flash_version, product_version_id,
            product_name, report_date, report_count, version_string)
           VALUES
           (%(signature_id)s, '1.0', %(product_version_id)s,
            'Firefox', '%(yesterday)s', 1, '9.0')
        """ % {'yesterday': yesterday,
               'product_version_id': other_product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_installations
            (signature_id, product_name, version_string,
             report_date, crash_count, install_count)
            VALUES
            (%(signature_id)s, 'Firefox', '8.0', '%(yesterday)s', 10, 8)
        """ % {'yesterday': yesterday,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_os
            (signature_id, os_version_string, product_version_id,
             product_name, report_date, report_count, version_string)
            VALUES
            (%(signature_id)s, 'Windows NT 6.4',
             %(product_version_id)s, 'Firefox', '%(yesterday)s', 1, '8.0')
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_process_type
            (signature_id, process_type, product_version_id,
             product_name, report_date, report_count, version_string)
            VALUES
            (%(signature_id)s, 'plugin', %(product_version_id)s,
             'Firefox', '%(yesterday)s', 1, '8.0')
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO signature_summary_uptime
            (signature_id, uptime_string, product_version_id,
             product_name, report_date, report_count, version_string)
            VALUES
            (%(signature_id)s, '15-30 minutes',
             %(product_version_id)s, 'Firefox', '%(yesterday)s', 1, '8.0')
        """ % {'yesterday': yesterday,
               'product_version_id': product_version_id,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO exploitability_reports
            (signature_id, signature, report_date, null_count,
             none_count, low_count, medium_count, high_count)
            VALUES
            (%(signature_id)s, 'Fake Signature #1', '%(yesterday)s',
             1, 2, 3, 4, 5)
        """ % {'yesterday': yesterday,
               'signature_id': signature_id})

        cursor.execute("""
            INSERT INTO android_devices
            (android_cpu_abi, android_manufacturer,
             android_model, android_version)
            VALUES
            ('armeabi-v7a', 'samsung', 'GT-P5100', '16 (REL)')
        """)

        cursor.execute("""
            SELECT android_device_id FROM android_devices
            WHERE android_cpu_abi = 'armeabi-v7a' AND
            android_manufacturer = 'samsung' AND
            android_model = 'GT-P5100' AND
            android_version = '16 (REL)'
        """)

        device_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO signature_summary_device
            (report_date, signature_id, product_version_id, product_name,
             version_string, android_device_id, report_count)
            VALUES
            ('%(yesterday)s', %(signature_id)s, %(product_version_id)s,
             'Firefox', '8.0', %(device_id)s, 123)
        """ % {'yesterday': yesterday,
               'signature_id': signature_id,
               'device_id': device_id,
               'product_version_id': product_version_id})

        cursor.execute("""
           INSERT INTO signature_summary_device
           (report_date, signature_id, product_version_id, product_name,
            version_string, android_device_id, report_count)
           VALUES
           ('%(yesterday)s', %(signature_id)s, %(product_version_id)s,
            'Firefox', '9.0', %(device_id)s, 123)
        """ % {'yesterday': yesterday,
               'signature_id': signature_id,
               'device_id': device_id,
               'product_version_id': other_product_version_id})

        cursor.execute("""
            INSERT INTO graphics_device
            (vendor_hex, adapter_hex, vendor_name, adapter_name)
            VALUES
            ('0x1234', '0x5678', 'Test Vendor', 'Test Adapter')
        """)

        cursor.execute("""
            SELECT graphics_device_id FROM graphics_device
            WHERE vendor_hex = '0x1234' AND adapter_hex = '0x5678'
        """)

        graphics_device_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO signature_summary_graphics
            (report_date, signature_id, graphics_device_id, product_version_id,
             product_name, version_string, report_count)
            VALUES
            ('%(yesterday)s', %(signature_id)s, %(device_id)s,
             %(product_version_id)s, 'Firefox', '8.0', 123)
        """ % {'yesterday': yesterday,
               'signature_id': signature_id,
               'device_id': graphics_device_id,
               'product_version_id': product_version_id})

        self.connection.commit()

        def add_product_version_builds(self):
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT product_version_id
                FROM product_versions
                WHERE product_name = 'Firefox' and version_string = '8.0'
            """)
            product_version_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO product_version_builds
                (build_id, platform, product_version_id)
                VALUES
                (1, 'Windows NT', %(product_version_id)s)
            """ % {'product_version_id': product_version_id})

            self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE products,
                     product_version_builds,
                     product_versions,
                     product_release_channels,
                     release_channels,
                     signatures, signature_summary_products,
                     signature_summary_architecture,
                     signature_summary_flash_version,
                     signature_summary_installations,
                     signature_summary_os,
                     signature_summary_process_type,
                     signature_summary_uptime,
                     exploitability_reports,
                     android_devices,
                     signature_summary_device,
                     signature_summary_graphics,
                     graphics_device
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestSignatureSummary, self).tearDown()

    def setup_data(self):
        now = self.now.date()
        yesterday = now - datetime.timedelta(days=1)
        lastweek = now - datetime.timedelta(days=7)
        now_str = datetimeutil.date_to_string(now)
        yesterday_str = datetimeutil.date_to_string(yesterday)
        lastweek_str = datetimeutil.date_to_string(lastweek)

        self.test_source_data = {
            # Test 1: find exact match for one product version and signature
            'products': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "products",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "product_name": 'Firefox',
                    "version_string": "8.0",
                    "report_count": 1,
                    "percentage": '100.000',
                }],
            },
            # Test 2: find ALL matches for all product versions and signature
            'products': {
                'params': {
                    "report_type": "products",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "product_name": 'Firefox',
                    "version_string": "8.0",
                    "report_count": 1,
                    "percentage": '50.000',
                },
                {
                    "product_name": 'Firefox',
                    "version_string": "9.0",
                    "report_count": 1,
                    "percentage": '50.000',
                }],
            },
            # Test 3: find architectures reported for a given version and a
            # signature
            'architecture': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "architecture",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "category": 'amd64',
                    "report_count": 1.0,
                    "percentage": "100.000",
                }],
            },
            # Test 4: find architectures reported for a signature with no
            # specific version.
            'architecture_no_version': {
                'params': {
                    "report_type": "architecture",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "category": 'amd64',
                    "report_count": 2,
                    "percentage": '100.000',
                }],
            },
            # Test 5: find flash_versions reported for specific version and
            # a signature
            'flash_versions': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "flash_version",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "category": '1.0',
                    "report_count": 1.0,
                    "percentage": "100.000",
                }],
            },
            # Test 6: find flash_versions reported with a signature and without
            # a specific version
            'flash_versions_no_version': {
                'params': {
                    "report_type": "flash_version",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "category": '1.0',
                    "report_count": 2.0,
                    "percentage": "100.000",
                }],
            },
            # Test 7: find installations reported for a signature
            'distinct_install': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "distinct_install",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "product_name": 'Firefox',
                    "version_string": '8.0',
                    "crashes": 10,
                    "installations": 8,
                }],
            },
            # Test 8: find os_version_strings reported for a signature
            'os': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "os",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "category": 'Windows NT 6.4',
                    "report_count": 1,
                    "percentage": "100.000",
                }],
            },
            # Test 9: find process_type reported for a signature
            'process_type': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "process_type",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "category": 'plugin',
                    "report_count": 1,
                    "percentage": "100.000",
                }],
            },
            # Test 10: find uptime reported for signature
            'uptime': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "uptime",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    "category": '15-30 minutes',
                    "report_count": 1,
                    "percentage": '100.000',
                }],
            },
            # Test 11: find exploitability reported for signature
            'exploitability': {
                'params': {
                    "versions": "Firefox:8.0",
                    "report_type": "exploitability",
                    "signature": "Fake Signature #1",
                    "start_date": lastweek_str,
                    "end_date": now_str,
                },
                'res_expected': [{
                    'low_count': 3,
                    'high_count': 5,
                    'null_count': 1,
                    'none_count': 2,
                    'report_date': yesterday_str,
                    'medium_count': 4,
                }],
            },
            # Test 12: find mobile devices reported for signature with a
            # specific version
            'devices': {
                'params': {
                    "versions": "Firefox:8.0",
                    'report_type': 'devices',
                    'signature': 'Fake Signature #1',
                    'start_date': lastweek_str,
                    'end_date': now_str,
                },
                'res_expected': [{
                    'cpu_abi': 'armeabi-v7a',
                    'manufacturer': 'samsung',
                    'model': 'GT-P5100',
                    'version': '16 (REL)',
                    'report_count': 123,
                    'percentage': '100.000',
                }],
            },
            # Test 13: find mobile devices reported for signature
            'devices_no_version': {
                'params': {
                    'report_type': 'devices',
                    'signature': 'Fake Signature #1',
                    'start_date': lastweek_str,
                    'end_date': now_str,
                },
                'res_expected': [{
                    'cpu_abi': 'armeabi-v7a',
                    'manufacturer': 'samsung',
                    'model': 'GT-P5100',
                    'version': '16 (REL)',
                    'report_count': 246,
                    'percentage': '100.000',
                }],
            },
            # Test 14: find mobile devices reported for signature
            'graphics': {
                'params': {
                    "versions": "Firefox:8.0",
                    'report_type': 'graphics',
                    'signature': 'Fake Signature #1',
                    'start_date': lastweek_str,
                    'end_date': now_str,
                },
                'res_expected': [{
                    'vendor_hex': '0x1234',
                    'adapter_hex': '0x5678',
                    'vendor_name': 'Test Vendor',
                    'adapter_name': 'Test Adapter',
                    'report_count': 123,
                    'percentage': '100.000',
                }],
            },
        }

    def test_get(self):
        signature_summary = SignatureSummary(config=self.config)

        self.setup_data()
        for test, data in self.test_source_data.items():
            res = signature_summary.get(**data['params'])
            if res == []:
                raise Exception(data['params'])
            self.assertNotEqual(res, [])
            self.assertEqual(res, data['res_expected'])

    def test_get_with_product(self):
        """same test as above but this time, add row to product_version_builds
        for Firefox 8.0 so that that becomes part of the queries"""
        signature_summary = SignatureSummary(config=self.config)

        self.setup_data()
        for test, data in self.test_source_data.items():
            res = signature_summary.get(**data['params'])
            self.assertEqual(res, data['res_expected'])

    def test_get_with_(self):
        signature_summary = SignatureSummary(config=self.config)

        self.setup_data()
        data = self.test_source_data['architecture']
        self.assertRaises(
            BadArgumentError,
            signature_summary.get,
            **data
        )

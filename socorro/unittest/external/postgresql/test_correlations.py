# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .unittestbase import PostgreSQLTestCase
from socorro.external.postgresql.correlations import Correlations
from nose.plugins.attrib import attr
from nose.tools import eq_
from socorro.lib import datetimeutil


@attr(integration='postgres')
class TestCorrelations(PostgreSQLTestCase):

    def setUp(self):
        """ Populate tables with fake data """
        super(TestCorrelations, self).setUp()

        cursor = self.connection.cursor()

        cursor.execute("""
            INSERT INTO signatures
            (signature_id, signature, first_report, first_build)
            VALUES
            (1, 'FakeSignature1', '2014-01-01', '20100115132715');
        """)

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name,
             rapid_beta_version)
            VALUES
            ('WaterWolf', 0, '1.0', 'waterwolf', '1.0');
        """)

        cursor.execute("""
            INSERT INTO reasons
            (reason_id, reason, first_seen)
            VALUES
            (1, 'goodreason', '2014-01-01');
        """)

        cursor.execute("""
            INSERT INTO product_versions
            (product_version_id, product_name, major_version, release_version,
             version_string, beta_number, version_sort , build_date,
             sunset_date, featured_version, build_type, has_builds,
             is_rapid_beta, rapid_beta_id, build_type_enum, version_build)
            VALUES
            (1, 'WaterWolf', '1.0', '1.0', '1.0', 0, 0, '2014-01-01',
             '2020-01-01', 't', 'release', 't', 'f', NULL, 'release', '');
        """)

        cursor.execute("""
            INSERT INTO correlations_addon
            (product_version_id, addon_id, addon_version, report_date,
             os_name, signature_id, total, reason_id)
            VALUES
            (1, 'fake-addon', '1.0', '2014-01-01', 'Linux', 1, 256, 1);
        """)

        cursor.execute("""
            INSERT INTO correlations_module
            (product_version_id, module_id, report_date,
             os_name, signature_id, total, reason_id)
            VALUES
            (1, 1, '2014-01-01', 'Linux', 1, 256, 1);
        """)

        cursor.execute("""
            INSERT INTO modules
            (module_id, name, version)
            VALUES
            (1, 'fake-module', '1.0');
        """)

        cursor.execute("""
            INSERT INTO correlations_core
            (product_version_id, cpu_arch, cpu_count, report_date,
             os_name, signature_id, total, reason_id)
            VALUES
            (1, 'x86', 1, '2014-01-01', 'Linux', 1, 256, 1);
        """)

        self.connection.commit()

    def tearDown(self):
        """ Cleanup the database, delete tables and functions """

        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE signatures, products, product_versions,
                     correlations_addon, reasons, correlations_module,
                     modules, correlations_core
            CASCADE;
        """)
        self.connection.commit()

        super(TestCorrelations, self).tearDown()

    def test_interesting_addons(self):
        correlations = Correlations(config=self.config)

        param = {
            'report_date': '2014-01-01',
            'report_type': 'interesting-addons',
            'product': 'WaterWolf',
            'version': '1.0',
            'signature': 'FakeSignature1',
            'platform': 'Linux',
            'min_baseline_diff': 0,
        }

        expected = {
            'hits': [
                {
                    "addon_id": "fake-addon",
                    "crashes_for_os": 256,
                    "crashes_for_sig": 256,
                    "in_os_ratio": 100.0,
                    "in_sig_ratio": 100.0,
                    "reason": "goodreason",
                    "total_for_os": 256,
                    "total_for_sig": 256 
                }

            ],
            'total': 1,
        }

        interesting_addons = correlations.get(**param)
        eq_(interesting_addons, expected)

    def test_interesting_addons_with_version(self):
        correlations = Correlations(config=self.config)

        param = {
            'report_date': '2014-01-01',
            'report_type': 'interesting-addons-with-version',
            'product': 'WaterWolf',
            'version': '1.0',
            'signature': 'FakeSignature1',
            'platform': 'Linux',
            'min_baseline_diff': 0,
        }

        expected = {
            'hits': [
                {
                    "addon_id": "fake-addon",
                    "addon_version": "1.0",
                    "crashes_for_os": 256,
                    "crashes_for_sig": 256,
                    "in_os_ratio": 100.0,
                    "in_sig_ratio": 100.0,
                    "reason": "goodreason",
                    "total_for_os": 256,
                    "total_for_sig": 256 
                }

            ],
            'total': 1,
        }

        interesting_addons = correlations.get(**param)
        eq_(interesting_addons, expected)

    def test_interesting_modules(self):
        correlations = Correlations(config=self.config)

        param = {
            'report_date': '2014-01-01',
            'report_type': 'interesting-modules',
            'product': 'WaterWolf',
            'version': '1.0',
            'signature': 'FakeSignature1',
            'platform': 'Linux',
            'min_baseline_diff': 0,
        }

        expected = {
            'hits': [
                {
                    "module_name": "fake-module",
                    "crashes_for_os": 256,
                    "crashes_for_sig": 256,
                    "in_os_ratio": 100.0,
                    "in_sig_ratio": 100.0,
                    "reason": "goodreason",
                    "total_for_os": 256,
                    "total_for_sig": 256 
                }

            ],
            'total': 1,
        }

        interesting_modules = correlations.get(**param)
        eq_(interesting_modules, expected)

    def test_interesting_modules_with_version(self):
        correlations = Correlations(config=self.config)

        param = {
            'report_date': '2014-01-01',
            'report_type': 'interesting-modules-with-version',
            'product': 'WaterWolf',
            'version': '1.0',
            'signature': 'FakeSignature1',
            'platform': 'Linux',
            'min_baseline_diff': 0,
        }

        expected = {
            'hits': [
                {
                    "module_name": "fake-module",
                    "module_version": "1.0",
                    "crashes_for_os": 256,
                    "crashes_for_sig": 256,
                    "in_os_ratio": 100.0,
                    "in_sig_ratio": 100.0,
                    "reason": "goodreason",
                    "total_for_os": 256,
                    "total_for_sig": 256 
                }

            ],
            'total': 1,
        }

        interesting_modules = correlations.get(**param)
        eq_(interesting_modules, expected)

    def test_core_counts(self):
        correlations = Correlations(config=self.config)

        param = {
            'report_date': '2014-01-01',
            'report_type': 'core-counts',
            'product': 'WaterWolf',
            'version': '1.0',
            'signature': 'FakeSignature1',
            'platform': 'Linux',
            'min_baseline_diff': 0,
        }

        expected = {
            'hits': [
                {
                    "cpu_arch": "x86",
                    "cpu_count": "1",
                    "crashes_for_os": 256,
                    "crashes_for_sig": 256,
                    "in_os_ratio": 100.0,
                    "in_sig_ratio": 100.0,
                    "reason": "goodreason",
                    "total_for_os": 256,
                    "total_for_sig": 256 
                }

            ],
            'total': 1,
        }

        interesting_modules = correlations.get(**param)
        eq_(interesting_modules, expected)


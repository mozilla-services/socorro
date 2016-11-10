# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.tools import eq_, ok_

from socorro.lib import datetimeutil

from .unittestbase import PostgreSQLTestCase


#==============================================================================
class IntegrationTestCrashAduByBuildSignature(PostgreSQLTestCase):
    """Test of Crash ADU By Build Signature stored procedures"""

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate product_info table with fake data """
        super(IntegrationTestCrashAduByBuildSignature, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        self.now = datetimeutil.utc_now()
        self.tomorrow = self.now + datetime.timedelta(days=1)

        tomorrow = self.tomorrow.date()
        now = self.now.date()

        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name)
            VALUES
            (
                'Firefox',
                1,
                '8.0',
                'firefox'
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
            INSERT INTO product_versions
            (product_version_id,
             product_name, major_version, release_version, version_string,
             build_date, sunset_date, featured_version, build_type,
             version_sort, has_builds, is_rapid_beta, build_type_enum)
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
                'release',
                '0008000',
                True,
                False,
                'release'
            );
        """ % {'now': now})

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
            INSERT INTO reports_clean
            (address_id,
             build,
             date_processed,
             domain_id,
             flash_version_id,
             os_name,
             os_version_id,
             process_type,
             reason_id,
             release_channel,
             signature_id,
             uuid,
             build_type,
             product_version_id)
            VALUES
            (1,
             '%(build)s',
             '%(now)s',
             1,
             1,
             'windows',
             '9',
             'browser',
             1,
             'release',
             '%(signature_id)s',
             'a1',
             'release',
             '%(product_version_id)s')""" %
                       {'now': now,
                        'build': now.strftime('%Y%m%d'),
                        'signature_id': signature_id,
                        'product_version_id': product_version_id})

        cursor.execute("""
             INSERT INTO build_adu
                (product_version_id,
                build_date,
                adu_date,
                os_name,
                adu_count)
             VALUES
                (%(product_version_id)s,
                '%(now)s',
                '%(now)s',
                'windows',
                123),
                (%(product_version_id)s,
                '%(tomorrow)s',
                '%(tomorrow)s',
                'windows',
                321) """ % {
                    'product_version_id': product_version_id,
                    'now': now,
                    'tomorrow': tomorrow
                    })

    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE products,
                product_versions,
                release_channels,
                signatures,
                reports_clean,
                build_adu,
                crash_adu_by_build_signature
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestCrashAduByBuildSignature, self).tearDown()

    def test_stored_procedure(self):
        cursor = self.connection.cursor()
        now = self.now.date()
        tomorrow = self.tomorrow.date()

        cursor.execute("""
            SELECT update_crash_adu_by_build_signature('%(now)s')
        """ % {'now': now})

        ok_(cursor.fetchone()[0])

        cursor.execute("""
            SELECT
                signature,
                adu_date,
                build_date,
                buildid::text,
                crash_count,
                adu_count,
                os_name,
                channel
            FROM
            crash_adu_by_build_signature
            WHERE build_date = '%(now)s'""" % {'now': now})
        expected = ('Fake Signature #1',
                    now,
                    now,
                    now.strftime('%Y%m%d'),
                    1,
                    123,
                    'windows',
                    'release')
        eq_(cursor.fetchall()[0], expected)

        # ensure that we show builds with no crashes

        expected = ('',
                    tomorrow,
                    tomorrow,
                    '0',
                    0,
                    321,
                    'windows',
                    'release')

        cursor.execute("""
            SELECT update_crash_adu_by_build_signature('%(tomorrow)s')
        """ % {'tomorrow': tomorrow})

        ok_(cursor.fetchone()[0])

        cursor.execute("""
            SELECT
                signature,
                adu_date,
                build_date,
                buildid::text,
                crash_count,
                adu_count,
                os_name,
                channel
            FROM
            crash_adu_by_build_signature
            WHERE build_date = '%(tomorrow)s'""" % {'tomorrow': tomorrow})

        eq_(cursor.fetchall()[1], expected)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.external.postgresql.signature_urls import SignatureURLs
from socorro.external.postgresql.signature_urls import MissingOrBadArgumentException
from socorro.lib import datetimeutil

from .unittestbase import PostgreSQLTestCase


#==============================================================================
class TestSignatureURLs(PostgreSQLTestCase):
    """Test socorro.external.postgresql.signature_urls.SignatureURLs class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate product_info table with fake data """
        super(TestSignatureURLs, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        now = datetimeutil.utc_now().date()
        cursor.execute("""
            INSERT INTO products
            (product_name, sort, rapid_release_version, release_name)
            VALUES
            ('Firefox', 1, '8.0', 'firefox'),
            ('Fennec', 2, '12.0', 'fennec');

            INSERT INTO reports_clean VALUES
            (
                '32bcc6e8-c23b-48ce-abf0-70d0e2120323',
                '%s',
                '%s',
                815,
                20111228055358,
                2895542,
                '384:52:52'::interval,
                '00:19:45'::interval,
                245,
                11427500,
                'Windows',
                71,
                '55',
                215,
                'Browser',
                'Beta',
                '',
                631719,
                'x86',
                2
            ),
            (
                '32bcc6e8-c23b-48ce-abf0-70d0e2120333',
                '%s',
                '%s',
                816,
                20111228055358,
                2895542,
                '384:52:52'::interval,
                '00:19:45'::interval,
                245,
                11427500,
                'Windows',
                71,
                '55',
                215,
                'Browser',
                'Beta',
                '',
                631719,
                'x86',
                2
            ),
            (
                '32bcc6e8-c23b-48ce-abf0-70d0e2120343',
                '%s',
                '%s',
                817,
                20111228055358,
                2895542,
                '384:52:52'::interval,
                '00:19:45'::interval,
                245,
                11427500,
                'Windows',
                71,
                '55',
                215,
                'Browser',
                'Beta',
                '',
                631719,
                'x86',
                2
            );
            INSERT INTO reports_user_info VALUES
            (
                '32bcc6e8-c23b-48ce-abf0-70d0e2120323',
                '%s',
                '',
                'AdapterVendorID: 0x1002, AdapterDeviceID: 0x9442,
                AdapterSubsysID: 05021002, AdapterDriverVersion: 8.920.0.0',
                '',
                'http://deusex.wikia.com/wiki/Praxis_kit'
            ),
            (
                '32bcc6e8-c23b-48ce-abf0-70d0e2120333',
                '%s',
                '',
                'AdapterVendorID: 0x1002, AdapterDeviceID: 0x9442,
                AdapterSubsysID: 05021002, AdapterDriverVersion: 8.920.0.0',
                '',
                'http://wikipedia.org/Code_Rush'
            ),
            (
                '32bcc6e8-c23b-48ce-abf0-70d0e2120343',
                '%s',
                '',
                'AdapterVendorID: 0x1002, AdapterDeviceID: 0x9442,
                AdapterSubsysID: 05021002, AdapterDriverVersion: 8.920.0.0',
                '',
                'http://arewemobileyet.org/'
            );
            INSERT INTO signatures VALUES
            (
                2895542,
                'EMPTY: no crashing thread identified; corrupt dump',
                '%s',
                2008120122
            );
            INSERT INTO product_versions VALUES
            (
                815,
                'Firefox',
                '11.0',
                '11.0',
                '11.0',
                0,
                '011000000r000',
                '%s',
                '%s',
                True,
                'Release'
            ),
            (
                816,
                'Firefox',
                '12.0a2',
                '12.0a2',
                '12.0a2',
                0,
                '011000000r000',
                '%s',
                '%s',
                True,
                'Beta'
            ),
            (
                817,
                'Fennec',
                '12.0a2',
                '12.0a2',
                '12.0a2',
                0,
                '011000000r000',
                '%s',
                '%s',
                True,
                'Beta'
            );
        """ % (now, now, now, now, now, now,
               now, now, now, now, now, now,
               now, now, now, now))

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE reports_clean, reports_user_info, signatures,
                     product_versions, products
            CASCADE
        """)
        self.connection.commit()
        super(TestSignatureURLs, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        signature_urls = SignatureURLs(config=self.config)
        now = datetimeutil.utc_now()
        now = datetime.datetime(now.year, now.month, now.day)
        now_str = datetimeutil.date_to_string(now)

        #......................................................................
        # Test 1: find one exact match for products and versions passed
        params = {
            "signature": "EMPTY: no crashing thread identified; corrupt dump",
            "start_date": now_str,
            "end_date": now_str,
            "products": ['Firefox'],
            "versions": ["Firefox:10.0", "Firefox:11.0"]
        }
        res = signature_urls.get(**params)
        res_expected = {
            "hits": [
                {
                    "url": "http://deusex.wikia.com/wiki/Praxis_kit",
                    "crash_count": 1
                 }
            ],
            "total": 1
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: Raise error if parameter is not passed
        params = {
            "signature": "",
            "start_date": "",
            "end_date": now_str,
            "products": ['Firefox'],
            "versions": ["Firefox:10.0", "Firefox:11.0"]
        }
        self.assertRaises(MissingOrBadArgumentException,
                          signature_urls.get,
                          **params)

        #......................................................................
        # Test 3: Query returning no results
        params = {
            "signature": "EMPTY: no crashing thread identified; corrupt dump",
            "start_date": now_str,
            "end_date": now_str,
            "products": ['Fennec'],
            "versions": ["Fennec:10.0", "Fennec:11.0"]
        }
        res = signature_urls.get(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        self.assertEqual(res, res_expected)

        # Test 4: Return results for all version of Firefox
        params = {
            "signature": "EMPTY: no crashing thread identified; corrupt dump",
            "start_date": now_str,
            "end_date": now_str,
            "products": ['Firefox'],
            "versions": ["ALL"]
        }

        res = signature_urls.get(**params)
        res_expected = {
            "hits": [
                {
                    "url": "http://deusex.wikia.com/wiki/Praxis_kit",
                    "crash_count": 1
                 },
                     {
                    "url": "http://wikipedia.org/Code_Rush",
                    "crash_count": 1
                 }
            ],
            "total": 2
        }

        self.assertEqual(res, res_expected)

        # Test 5: Return results for all products and versions
        params = {
            "signature": "EMPTY: no crashing thread identified; corrupt dump",
            "start_date": now_str,
            "end_date": now_str,
            "products": ['ALL'],
            "versions": ["ALL"]
        }

        res = signature_urls.get(**params)
        res_expected = {
            "hits": [
                {
                    "url": "http://deusex.wikia.com/wiki/Praxis_kit",
                    "crash_count": 1
                 },
                     {
                    "url": "http://wikipedia.org/Code_Rush",
                    "crash_count": 1
                 },
                     {
                    "url": "http://arewemobileyet.org/",
                    "crash_count": 1
                 }
            ],
            "total": 3
        }

        self.assertEqual(res, res_expected)

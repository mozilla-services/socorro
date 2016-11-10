# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.tools import eq_, assert_raises

from socorro.lib import MissingArgumentError
from socorro.lib.datetimeutil import UTC
from socorro.external.postgresql.signature_first_date import (
    SignatureFirstDate,
)

from .unittestbase import PostgreSQLTestCase


# =============================================================================
class IntegrationTestSignatureFirstDate(PostgreSQLTestCase):
    """Test socorro.external.postgresql.signature_first_date
    .SignatureFirstDate class. """

    # -------------------------------------------------------------------------
    def _insert_test_data(self):
        cursor = self.connection.cursor()

        # Insert data
        cursor.execute("""
            INSERT INTO signatures
            (first_build, first_report, signature)
            VALUES (
                12,
                '2000-01-01',
                'hey'
            ), (
                12,
                '2000-01-02',
                'i_just_met_you()'
            ), (
                2,
                '2000-01-01',
                'andThisIs<craaazy>'
            );
        """)

        self.connection.commit()

    # -------------------------------------------------------------------------
    def _delete_test_data(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE signatures
            CASCADE
        """)
        self.connection.commit()

    # -------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the signatures table with fake
        data. """
        super(IntegrationTestSignatureFirstDate, self).setUp()
        self._insert_test_data()

    # -------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        self._delete_test_data()
        super(IntegrationTestSignatureFirstDate, self).tearDown()

    # -------------------------------------------------------------------------
    def test_get(self):
        api = SignatureFirstDate(config=self.config)

        # .....................................................................
        # Test 1: a valid signature
        params = {
            "signatures": "hey"
        }
        res = api.get(**params)
        res_expected = {
            "hits": [
                {
                    "signature": "hey",
                    "first_date": datetime.datetime(
                        2000, 1, 1, 0, 0, 0, 0,
                        tzinfo=UTC
                    ),
                    "first_build": "12",
                }
            ],
            "total": 1
        }
        eq_(res['total'], res_expected['total'])
        eq_(res, res_expected)

        # .....................................................................
        # Test 2: several signatures
        params = {
            "signatures": ["hey", "i_just_met_you()"]
        }
        res = api.get(**params)
        res_expected = {
            "hits": [
                {
                    "signature": "hey",
                    "first_date": datetime.datetime(
                        2000, 1, 1, 0, 0, 0, 0,
                        tzinfo=UTC
                    ),
                    "first_build": "12",
                },
                {
                    "signature": "i_just_met_you()",
                    "first_date": datetime.datetime(
                        2000, 1, 2, 0, 0, 0, 0,
                        tzinfo=UTC
                    ),
                    "first_build": "12",
                }
            ],
            "total": 2
        }

        eq_(res['total'], res_expected['total'])
        eq_(res, res_expected)

        # .....................................................................
        # Test 3: a non-existent signature
        params = {
            "signatures": "unknown"
        }
        res = api.get(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        eq_(res, res_expected)

        # .....................................................................
        # Test 4: missing argument
        params = {}
        assert_raises(MissingArgumentError, api.get, **params)

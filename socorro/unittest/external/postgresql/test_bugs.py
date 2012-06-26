# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.postgresql.bugs import Bugs, MissingOrBadArgumentError
import socorro.unittest.testlib.util as testutil

from .unittestbase import PostgreSQLTestCase


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class IntegrationTestBugs(PostgreSQLTestCase):
    """Test socorro.external.postgresql.bugs.Bugs class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestBugs, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        cursor.execute("""
            INSERT INTO bug_associations
            (signature, bug_id)
            VALUES
            (
                'sig1',
                1
            ),
            (
                'sig2',
                1
            ),
            (
                'sig2',
                2
            ),
            (
                'sig3',
                3
            );
            INSERT INTO signatures
            (signature_id, signature, first_report, first_build)
            VALUES
            (1, 'sig1', '2011-03-06 20:20:52.422027+00', 20100115132715),
            (2, 'sig2', '2011-03-06 20:20:52.422027+00', 20100115132715),
            (3, 'sig3', '2011-03-06 20:20:52.422027+00', 20100115132715),
            (1337, 'sig1337', '2011-03-06 20:20:52.422027+00', 20100115132715);
        """)

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE bug_associations, signatures
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestBugs, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        bugs = Bugs(config=self.config)

        #......................................................................
        # Test 1: a valid signature with 2 bugs
        params = {
            "signature_ids": "2"
        }
        res = bugs.get(**params)
        res_expected = {
            "hits": [
                {
                    "id": 1,
                    "signature": "sig2"
                },
                {
                    "id": 2,
                    "signature": "sig2"
                }
            ],
            "total": 2
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: several signatures with bugs
        params = {
            "signature_ids": ["1", "2", "3"]
        }
        res = bugs.get(**params)
        res_expected = {
            "hits": [
                {
                    "id": 1,
                    "signature": "sig1"
                },
                {
                    "id": 1,
                    "signature": "sig2"
                },
                {
                    "id": 2,
                    "signature": "sig2"
                },
                {
                    "id": 3,
                    "signature": "sig3"
                }
            ],
            "total": 4
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 3: a signature without bugs
        params = {
            "signature_ids": "1337"
        }
        res = bugs.get(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 4: missing argument
        params = {}
        self.assertRaises(MissingOrBadArgumentError, bugs.get, **params)

        #......................................................................
        # Test 5: bad signature
        params = {
            "signature_id": "lolwut?"
        }
        self.assertRaises(MissingOrBadArgumentError, bugs.get, **params)

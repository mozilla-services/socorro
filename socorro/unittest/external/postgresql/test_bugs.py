# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from socorro.external.postgresql.bugs import Bugs
from socorro.lib import MissingArgumentError
from socorro.unittest.external.postgresql.unittestbase import PostgreSQLTestCase


class IntegrationTestBugs(PostgreSQLTestCase):
    """Test socorro.external.postgresql.bugs.Bugs class. """

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
                'sign1',
                1
            ),
            (
                'js',
                1
            ),
            (
                'mysignature',
                2
            ),
            (
                'mysignature',
                3
            );
        """)

        self.connection.commit()

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE bug_associations
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestBugs, self).tearDown()

    def test_get(self):
        bugs = Bugs(config=self.config)

        # Test 1: a valid signature with 2 bugs
        params = {
            "signatures": "mysignature"
        }
        res = bugs.get(**params)
        res_expected = {
            "hits": [
                {
                    "id": 2,
                    "signature": "mysignature"
                },
                {
                    "id": 3,
                    "signature": "mysignature"
                }
            ],
            "total": 2
        }
        assert res['total'] == res_expected['total']
        # by convert the hits to sets we can be certain order doesn't matter
        expected = set([(x['id'], x['signature']) for x in res_expected['hits']])
        assert set([(x['id'], x['signature']) for x in res['hits']]) == expected

        # Test 2: several signatures with bugs
        params = {
            "signatures": ["mysignature", "js"]
        }
        res = bugs.get(**params)
        res_expected = {
            "hits": [
                {
                    "id": 1,
                    "signature": "sign1"
                },
                {
                    "id": 1,
                    "signature": "js"
                },
                {
                    "id": 2,
                    "signature": "mysignature"
                },
                {
                    "id": 3,
                    "signature": "mysignature"
                }
            ],
            "total": 4
        }

        assert res['total'] == res_expected['total']
        expected = set([(x['id'], x['signature']) for x in res_expected['hits']])
        assert set([(x['id'], x['signature']) for x in res['hits']]) == expected

        # Test 3: a signature without bugs
        params = {
            "signatures": "unknown"
        }
        res = bugs.get(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        assert res == res_expected

        # Test 4: missing argument
        with pytest.raises(MissingArgumentError):
            bugs.get()

        # Test 5: search by bug_ids argument
        params = {
            "bug_ids": ["1", "2"]
        }
        res = bugs.get(**params)

        # This is what we expect but because the results aren't sorted,
        # we can't expect them to come in in this order.
        res_expected = {
            'hits': [
                {'id': 1, 'signature': 'js'},
                {'id': 1, 'signature': 'sign1'},
                {'id': 2, 'signature': 'mysignature'}
            ],
            'total': 3
        }
        assert res['total'] == res_expected['total']
        assert len(res['hits']) == len(res_expected['hits'])
        for row in res_expected['hits']:
            assert row in res['hits']

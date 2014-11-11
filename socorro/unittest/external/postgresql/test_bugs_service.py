# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_, assert_raises

from socorro.external.postgresql.bugs_service import (
    Bugs,
    MissingArgumentError
)
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)

from socorro.external.postgresql.service_base import (
    PostgreSQLWebServiceBase
)


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestBugs(PostgreSQLWebServiceBase):
    """Test socorro.external.postgresql.bugs_service.Bugs class. """

    #--------------------------------------------------------------------------
    def _insert_test_data(self, connection):
        # clear old data, just in case
        execute_no_results(
            connection,
            "TRUNCATE bug_associations, bugs CASCADE"
        )
        # Insert data
        execute_no_results(
            connection,
            "INSERT INTO bugs VALUES (1),(2),(3),(4)"
        )
        execute_no_results(
            connection,
            """
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
            """
        )

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestBugs, self).setUp()
        self.transaction(self._insert_test_data)

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        def truncate_transaction(connection):
            execute_no_results(
                connection,
                "TRUNCATE bug_associations, bugs CASCADE"
            )
        self.transaction(truncate_transaction)
        super(IntegrationTestBugs, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        bugs = Bugs(config=self.config)

        #......................................................................
        # Test 1: a valid signature with 2 bugs
        params = {
            "signatures": "mysignature"
        }
        res = bugs.post(**params)
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
        eq_(res['total'], res_expected['total'])
        # by convert the hits to sets we can be certain order doesn't matter
        eq_(
            set([(x['id'], x['signature']) for x in res['hits']]),
            set([(x['id'], x['signature']) for x in res_expected['hits']])
        )

        #......................................................................
        # Test 2: several signatures with bugs
        params = {
            "signatures": ["mysignature", "js"]
        }
        res = bugs.post(**params)
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

        eq_(res['total'], res_expected['total'])
        eq_(
            set([(x['id'], x['signature']) for x in res['hits']]),
            set([(x['id'], x['signature']) for x in res_expected['hits']])
        )

        #......................................................................
        # Test 3: a signature without bugs
        params = {
            "signatures": "unknown"
        }
        res = bugs.post(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        eq_(res, res_expected)

        #......................................................................
        # Test 4: missing argument
        params = {}
        assert_raises(MissingArgumentError, bugs.post, **params)

        #......................................................................
        # Test 5: search by bug_ids argument
        params = {
            "bug_ids": ["1", "2"]
        }
        res = bugs.post(**params)
        res_expected = {
            'hits': [
                {'id': 1, 'signature': 'sign1'},
                {'id': 1, 'signature': 'js'},
                {'id': 2, 'signature': 'mysignature'}
            ],
            "total": 3
        }
        eq_(res, res_expected)

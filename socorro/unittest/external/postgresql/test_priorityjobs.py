# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr

from socorro.external.postgresql import priorityjobs

from unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestPriorityjobs(PostgreSQLTestCase):
    """Test socorro.external.postgresql.priorityjobs.Priorityjobs class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestPriorityjobs, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        cursor.execute("""
            INSERT INTO priorityjobs (uuid) VALUES
            (
                'a1'
            ),
            (
                'a2'
            );
        """)

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE priorityjobs
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestPriorityjobs, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        jobs = priorityjobs.Priorityjobs(config=self.config)

        #......................................................................
        # Test 1: a valid job
        params = {
            "uuid": "a1"
        }
        res = jobs.get(**params)
        res_expected = {
            "hits": [
                {
                    "uuid": "a1"
                }
            ],
            "total": 1
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: an invalid job
        params = {
            "uuid": "b2"
        }
        res = jobs.get(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 3: missing argument
        params = {}
        self.assertRaises(priorityjobs.MissingArgumentError,
                          jobs.get,
                          **params)

    #--------------------------------------------------------------------------
    def test_create(self):
        jobs = priorityjobs.Priorityjobs(config=self.config)

        #......................................................................
        # Test 1: a new job
        params = {
            "uuid": "b1"
        }
        res = jobs.create(**params)
        res_expected = True

        self.assertEqual(res, res_expected)

        # Verify that job has been created in the DB
        res = jobs.get(**params)
        res_expected = {
            "hits": [
                {
                    "uuid": "b1"
                }
            ],
            "total": 1
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: an already existing job
        params = {
            "uuid": "a2"
        }
        res = jobs.create(**params)
        res_expected = False

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 3: missing argument
        params = {}
        self.assertRaises(priorityjobs.MissingArgumentError,
                          jobs.create,
                          **params)

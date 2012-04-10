from socorro.external.postgresql import priorityjobs
import socorro.unittest.testlib.util as testutil

from unittestbase import PostgreSQLTestCase


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class IntegrationTestPriorityjobs(PostgreSQLTestCase):
    """Test socorro.external.postgresql.priorityjobs.Priorityjobs class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestPriorityjobs, self).setUp()

        cursor = self.connection.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE priorityjobs
            (
                uuid text not null primary key
            );
        """)

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
            DROP TABLE priorityjobs;
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
        self.assertRaises(priorityjobs.MissingOrBadArgumentError,
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
        self.assertRaises(priorityjobs.MissingOrBadArgumentError,
                          jobs.create,
                          **params)

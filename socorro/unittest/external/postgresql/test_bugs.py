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

        # Create tables
        cursor.execute("""
            CREATE TABLE bugs
            (
                id serial NOT NULL
            );
            CREATE TABLE bug_associations
            (
                bug_id integer not null,
                signature text
            );
        """)

        # Insert data
        cursor.execute("""
            INSERT INTO bugs VALUES
            (1),
            (2),
            (3),
            (4);
        """)

        cursor.execute("""
            INSERT INTO bug_associations VALUES
            (
                1,
                'sign1'
            ),
            (
                1,
                'js'
            ),
            (
                2,
                'mysignature'
            ),
            (
                3,
                'mysignature'
            );
        """)

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            DROP TABLE bug_associations;
            DROP TABLE bugs;
        """)
        self.connection.commit()
        super(IntegrationTestBugs, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        bugs = Bugs(config=self.config)

        #......................................................................
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

        self.assertEqual(res, res_expected)

        #......................................................................
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

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 3: a signature without bugs
        params = {
            "signatures": "unknown"
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

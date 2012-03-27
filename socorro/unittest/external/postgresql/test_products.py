import datetime

from socorro.external.postgresql.products import Products
from socorro.external.postgresql.products import MissingOrBadArgumentException
from socorro.lib import datetimeutil
import socorro.unittest.testlib.util as testutil

from .unittestbase import PostgreSQLTestCase

#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)

#==============================================================================
class TestProducts(PostgreSQLTestCase):
    """Test socorro.external.postgresql.products.Products class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """ Populate product_info table with fake data """
        super(TestProducts, self).setUp()
        
        cursor = self.connection.cursor()
        
        #Create table
        cursor.execute("""
            CREATE TABLE product_info
            (
                product_name citext,
                version_string citext,
                start_date timestamp without time zone,
                end_date timestamp without time zone,
                is_featured boolean,
                build_type citext,
                throttle numeric(5,2)
            );
        """)
        
        # Insert data
        now = datetimeutil.utc_now().date()
        cursor.execute("""
            INSERT INTO product_info VALUES
            (
                'Firefox',
                '8.0',
                '%s',
                '%s',
                False,
                'Release',
                10.00
            ),
            (
                'Firefox',
                '11.0.1',
                '%s',
                '%s',
                False,
                'Release',
                20.00
            ),
            (
                'Thunderbird',
                '10.0.2b',
                '%s',
                '%s',
                False,
                'Release',
                30.00
            );
        """ % (now, now,
               now, now,
               now, now))
        
        self.connection.commit()
        
    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            DROP TABLE product_info;
        """)
        self.connection.commit()
        super(TestProducts, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        products = Products(config=self.config)
        now = datetimeutil.utc_now()
        now = datetime.datetime(now.year, now.month, now.day)
        now_str = datetimeutil.date_to_string(now)

        #......................................................................
        # Test 1: find one exact match for one product and one version
        params = {
            "versions": "Firefox:8.0"
        }
        res = products.get_versions(**params)
        res_expected = {
            "hits": [
                {
                    "product": "Firefox",
                    "version": "8.0",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 10.0
                 }
            ],
            "total": 1
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: Find two different products with their correct verions
        params = {
            "versions": ["Firefox:11.0.1", "Thunderbird:10.0.2b"]
        }
        res = products.get_versions(**params)
        res_expected = {
            "hits": [
                {
                    "product": "Firefox",
                    "version": "11.0.1",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 20.0
                 },
                 {
                    "product": "Thunderbird",
                    "version": "10.0.2b",
                    "start_date": now_str,
                    "end_date": now_str,
                    "is_featured": False,
                    "build_type": "Release",
                    "throttle": 30.0
                 }
            ],
            "total": 2
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 3: empty result, no products:version found
        params = {
            "versions": "Firefox:14.0"
        }
        res = products.get_versions(**params)
        res_expected = {
            "hits": [],
            "total": 0
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 4: exception when no parameter is passed
        params = {
            "versions": ['']
        }
        self.assertRaises(MissingOrBadArgumentException,
                          products.get_versions,
                          **params)
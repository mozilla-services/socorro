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

        #Create table
        cursor.execute("""
            CREATE TABLE reports_clean
            (
                uuid text NOT NULL,
                date_processed timestamp with time zone NOT NULL,
                client_crash_date timestamp with time zone,
                product_version_id integer,
                build numeric,
                signature_id integer NOT NULL,
                install_age interval,
                uptime interval,
                reason_id integer NOT NULL,
                address_id integer NOT NULL,
                os_name citext NOT NULL,
                os_version_id integer NOT NULL,
                hang_id text,
                flash_version_id integer NOT NULL,
                process_type citext NOT NULL,
                release_channel citext NOT NULL,
                duplicate_of text,
                domain_id integer NOT NULL,
                architecture citext,
                cores integer
            );
            CREATE TABLE reports_user_info
            (
                uuid text NOT NULL,
                date_processed timestamp with time zone NOT NULL,
                user_comments citext,
                app_notes citext,
                email citext,
                url text
            );
            CREATE TABLE signatures
            (
                signature_id integer NOT NULL,
                signature text,
                first_report timestamp with time zone,
                first_build numeric
            );
            CREATE TABLE product_versions
            (
                product_version_id integer NOT NULL,
                product_name text NOT NULL,
                major_version text NOT NULL,
                release_version text NOT NULL,
                version_string text NOT NULL,
                beta_number integer,
                version_sort text DEFAULT 0 NOT NULL,
                build_date date NOT NULL,
                sunset_date date NOT NULL,
                featured_version boolean DEFAULT false NOT NULL,
                build_type text DEFAULT 'release' NOT NULL
            );
        """)

        # Insert data
        now = datetimeutil.utc_now().date()
        cursor.execute("""
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
            );
        """ % (now, now, now, now, now, now))

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """ Cleanup the database, delete tables and functions """
        cursor = self.connection.cursor()
        cursor.execute("""
            DROP TABLE reports_clean;
            DROP TABLE reports_user_info;
            DROP TABLE signatures;
            DROP TABLE product_versions;
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

import unittest
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from socorro.app.generic_app import main
from socorro.cron.weeklyReportsPartitions import WeeklyReportsPartitions
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)


# Notes:
#  psycopg2.extensions
#
#  0, TRANSACTION_STATUS_IDLE
#  1, TRANSACTION_STATUS_ACTIVE
#  2, TRANSACTION_STATUS_INTRANS
#  3, TRANSACTION_STATUS_INERROR
#  4, TRANSACTION_STATUS_UNKNOWN

DSN = {
  "database_host": databaseHost.default,
  "database_name": databaseName.default,
  "database_user": databaseUserName.default,
  "database_password": databasePassword.default
}


class TestClass(unittest.TestCase):

    def setUp(self):
        assert 'test' in databaseName.default, databaseName.default
        dsn = ('host=%(database_host)s dbname=%(database_name)s '
               'user=%(database_user)s password=%(database_password)s' % DSN)
        self.conn = psycopg2.connect(dsn)
        # Create a mock function named 'weekly_report_partitions'
        cursor = self.conn.cursor()
        cursor.execute("""
        DROP TABLE IF EXISTS mock_bucket;
        CREATE TABLE mock_bucket (when_used timestamp);
        DROP FUNCTION IF EXISTS weekly_report_partitions();
        CREATE FUNCTION weekly_report_partitions() RETURNS VOID AS $$
          BEGIN
            insert into mock_bucket values (now());
            return;
          END; $$ LANGUAGE plpgsql;
        """)
        self.conn.commit()
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE

    def tearDown(self):
        self.conn.cursor().execute("""
        DROP TABLE IF EXISTS mock_bucket;
        """)
        self.conn.commit()

    def test_run_weeklyReportsPartitions(self):
        """Create a mock function named exactly like the stored procedure in
        the cron script we want to functionally test.
        That way we can assert that it was run.
        """

        # provide values for the config to pick up

        # be explicit about the values_source_list to
        # avoid configman picking up nosetests arguments
        main(WeeklyReportsPartitions, values_source_list=[DSN])

        # check that something was written to the mock_bucket
        cursor = self.conn.cursor()
        cursor.execute('select count(*) from mock_bucket;')
        self.assertTrue(cursor.fetchone())

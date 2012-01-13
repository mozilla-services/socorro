import sys
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from socorro.app.generic_app import main
from socorro.cron.weeklyReportsPartitions import WeeklyReportsPartitions
from socorro.external.postgresql.transactional import Postgres
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)
import configman


# Notes:
#  psycopg2.extensions
#
#  0, TRANSACTION_STATUS_IDLE
#  1, TRANSACTION_STATUS_ACTIVE
#  2, TRANSACTION_STATUS_INTRANS
#  3, TRANSACTION_STATUS_INERROR
#  4, TRANSACTION_STATUS_UNKNOWN


def test_run_weeklyReportsPartitions():
    """Create a mock function named exactly like the stored procedure in the
    cron script we want to functionally test. 
    That way we can assert that it was run. 
    """
    
    # Create a mock function named 'weekly_report_partitions'
    dsn = ('host=%s dbname=%s user=%s password=%s' % (
            databaseHost.default, databaseName.default,
            databaseUserName.default, databasePassword.default))
    assert 'dbname=test' in dsn, "make sure you use test database!"
    conn = psycopg2.connect(dsn)
    cursor = conn.cursor()
    cursor.execute("""
    DROP TABLE IF EXISTS mock_bucket;
    CREATE TABLE mock_bucket (when_used timestamp);
    DROP FUNCTION IF EXISTS weekly_report_partitions();
    CREATE FUNCTION weekly_report_partitions() RETURNS VOID AS $$
      BEGIN
        insert into mock_bucket values (now());
        return;
      END; $$ LANGUAGE plpgsql;
    COMMIT;
    """)
    conn.get_transaction_status() == TRANSACTION_STATUS_IDLE
 
    try:
        # monkey-patch the convenient built in required config 
        Postgres.required_config.database_host.value = databaseHost.default
        Postgres.required_config.database_name.value = databaseName.default
        Postgres.required_config.database_user.value = databaseUserName.default
        Postgres.required_config.database_password.value = databasePassword.default
        
        # use the `values_source_list=[configman.environment]` to 
        # avoid configman picking up nosetests arguments
        app = main(WeeklyReportsPartitions, values_source_list=[configman.environment])

        # check that something was written to the mock_bucket
        cursor = conn.cursor()
        cursor.execute('select count(*) from mock_bucket;')
        assert cursor.fetchone()
        
    finally:
        # cleaning up like a good citizen
        cursor.execute("""
        DROP TABLE IF EXISTS mock_bucket;
        """)

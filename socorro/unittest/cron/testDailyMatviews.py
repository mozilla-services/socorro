import datetime
import unittest
import psycopg2
import socorro.cron.dailyMatviews  # needed for Mock
import socorro.cron.dailyMatviews as dailyMatviews

from socorro.lib.datetimeutil import utc_now

from socorro.unittest.config.commonconfig import databaseHost
from socorro.unittest.config.commonconfig import databaseName
from socorro.unittest.config.commonconfig import databaseUserName
from socorro.unittest.config.commonconfig import databasePassword

from mock import patch


class mock_connection:
    def __init__(self, c):
        self.c = c

    def _void(self):
        pass

    commit = rollback = _void

    def cursor(self):
        return self.c


class mock_psycopg2:
    InternalError = Exception

    def __init__(self, cursor):
        self.cursor = cursor

    def connect(self, *args, **kwargs):
        return mock_connection(self.cursor)


class mock_cursor:
    def __init__(self, returns):
        self.returns = returns
        self.called = []

    def callproc(self, name, params):
        self.name = name
        self.called.append(name)

    def fetchone(self):
        if self.name in self.returns:
            return self.returns[self.name]
        return (True,)

    def execute(self, sql, params):
        pass


class TestCase(unittest.TestCase):
    def setUp(self):
        self.config = {
          'databaseHost': '',
          'databasePassword': '',
          'databaseName': '',
          'databaseUserName': '',
        }

    def test_failing__update_product_versions(self):
        cursor = mock_cursor({
          'update_product_versions': (False,),
        })
        dailyMatviews.psycopg2 = mock_psycopg2(cursor)
        with patch('socorro.cron.dailyMatviews.logger') as mock_logger:
            dailyMatviews.update(self.config, 'some date')
            self.assertEqual(cursor.called, ['update_product_versions',
              'update_signatures', 'update_os_versions', 'update_adu',
              'update_daily_crashes', 'update_hang_report', 'rank_compare'])
            self.assertEqual(mock_logger.info.call_count, 7)
            self.assertEqual(mock_logger.warn.call_count, 2)
            self.assertEqual(mock_logger.error.call_count, 0)

    def test_all_works(self):
        cursor = mock_cursor({})
        dailyMatviews.psycopg2 = mock_psycopg2(cursor)
        with patch('socorro.cron.dailyMatviews.logger') as mock_logger:
            dailyMatviews.update(self.config, 'some date')
            self.assertEqual(mock_logger.info.call_count, 8)
            self.assertEqual(mock_logger.warn.call_count, 0)
            self.assertEqual(mock_logger.error.call_count, 0)

    def test_mock_internal_error(self):
        cursor = mock_cursor({
          'update_signatures': psycopg2.InternalError,
        })
        dailyMatviews.psycopg2 = mock_psycopg2(cursor)
        with patch('socorro.cron.dailyMatviews.logger') as mock_logger:
            dailyMatviews.update(self.config, 'some date')
            self.assertEqual(mock_logger.info.call_count, 7)
            self.assertEqual(mock_logger.warn.call_count, 1)
            self.assertEqual(mock_logger.error.call_count, 1)


class FunctionalTestCase(unittest.TestCase):

    connection = None

    def setUp(self):
        # create the tables
        self.config = {
          'databaseHost': databaseHost.default,
          'databaseName': databaseName.default,
          'databaseUserName': databaseUserName.default,
          'databasePassword': databasePassword.default,
        }

        if not self.connection:
            dsn = 'host=%(databaseHost)s '\
                  'dbname=%(databaseName)s '\
                  'user=%(databaseUserName)s '\
                  'password=%(databasePassword)s' % self.config
            self.connection = psycopg2.connect(dsn)
        cursor = self.connection.cursor()
        cursor.execute("""
DROP TABLE IF EXISTS cronjobs;
CREATE TABLE cronjobs (
  cronjob VARCHAR,
  last_target_time VARCHAR,
  last_success TIMESTAMP NULL,
  last_failure TIMESTAMP NULL,
  failure_message VARCHAR NULL
);
INSERT INTO cronjobs (cronjob) VALUES ('dailyMatviews:update_product_versions');
INSERT INTO cronjobs (cronjob) VALUES ('dailyMatviews:update_os_versions');
INSERT INTO cronjobs (cronjob) VALUES ('dailyMatviews:update_tcbs');
INSERT INTO cronjobs (cronjob) VALUES ('dailyMatviews:update_signatures');
INSERT INTO cronjobs (cronjob) VALUES ('dailyMatviews:update_adu');
INSERT INTO cronjobs (cronjob) VALUES ('dailyMatviews:update_daily_crashes');
 CREATE OR REPLACE FUNCTION update_product_versions()
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;
 CREATE OR REPLACE FUNCTION update_signatures(timestamp with time zone)
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;
 CREATE OR REPLACE FUNCTION update_os_versions(timestamp with time zone)
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;
 CREATE OR REPLACE FUNCTION update_tcbs(timestamp with time zone)
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;
 CREATE OR REPLACE FUNCTION update_adu(timestamp with time zone)
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;
 CREATE OR REPLACE FUNCTION update_daily_crashes(timestamp with time zone)
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;
 CREATE OR REPLACE FUNCTION update_hang_report(timestamp with time zone)
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;
 CREATE OR REPLACE FUNCTION rank_compare(timestamp with time zone)
RETURNS boolean AS $$
BEGIN
        RETURN true;
END;
$$ LANGUAGE plpgsql;

        """)
        self.connection.commit()

    def tearDown(self):
        # drop the table
        cursor = self.connection.cursor()
        cursor.execute("""DROP TABLE cronjobs;
        DROP FUNCTION update_product_versions () ;
        DROP FUNCTION update_os_versions (timestamp with time zone) ;
        DROP FUNCTION update_signatures (timestamp with time zone) ;
        DROP FUNCTION update_tcbs (timestamp with time zone) ;
        DROP FUNCTION update_adu (timestamp with time zone) ;
        DROP FUNCTION update_daily_crashes (timestamp with time zone) ;
        DROP FUNCTION update_hang_report(timestamp with time zone) ;
        DROP FUNCTION rank_compare(timestamp with time zone) ;
        """)
        self.connection.commit()

    def test_all_works_without_errors(self):
        with patch('socorro.cron.dailyMatviews.logger'):
            dailyMatviews.update(self.config, utc_now().date())
            cursor = self.connection.cursor()
            for each in ('dailyMatviews:update_product_versions',
                         'dailyMatviews:update_os_versions',
                         'dailyMatviews:update_adu',
                         'dailyMatviews:update_tcbs',
                         'dailyMatviews:update_signatures',
                         ):
                cursor.execute(
                  'select last_success from cronjobs where cronjob=%s',
                  [each]
                )
                last_success = cursor.fetchone()[0]
                self.assertTrue(last_success)

    def test_fail__update_product_versions(self):
        with patch('socorro.cron.dailyMatviews.logger'):
            cursor = self.connection.cursor()
            cursor.execute("""
            CREATE OR REPLACE FUNCTION update_product_versions()
            RETURNS boolean AS $$
            BEGIN
                    RETURN false;
            END;
            $$ LANGUAGE plpgsql;
            """)
            self.connection.commit()

            dailyMatviews.update(self.config, utc_now().date())
            cursor = self.connection.cursor()
            for each in ('dailyMatviews:update_os_versions',
                         'dailyMatviews:update_adu',
                         'dailyMatviews:update_signatures',
                         ):
                cursor.execute(
                  'select last_success from cronjobs where cronjob=%s',
                  [each]
                )
                last_success = cursor.fetchone()[0]
                self.assertTrue(last_success)

            for each in ('dailyMatviews:update_product_versions',
                         'dailyMatviews:update_tcbs',
                         ):
                cursor.execute(
                  'select last_success from cronjobs where cronjob=%s',
                  [each]
                )
                last_success = cursor.fetchone()[0]
                self.assertTrue(not last_success)

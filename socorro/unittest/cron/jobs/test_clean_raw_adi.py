import datetime

from socorro.cron.crontabber_app import CronTabberApp
from socorro.lib.datetimeutil import utc_now
from socorro.unittest.cron.jobs.base import IntegrationTestBase


class TestCleanRawADICronApp(IntegrationTestBase):

    def _setup_config_manager(self, days_to_keep=None):
        return super(TestCleanRawADICronApp, self)._setup_config_manager(
            jobs_string='socorro.cron.jobs.clean_raw_adi.CleanRawADICronApp|1d',
            extra_value_source={
                'crontabber.class-CleanRawADICronApp.days_to_keep': days_to_keep
            },
        )

    def tearDown(self):
        cur = self.conn.cursor()

        # Ensure that the test partition entry and table no longer exist.
        cur.execute('TRUNCATE raw_adi CASCADE')
        cur.execute('TRUNCATE raw_adi_logs CASCADE')
        self.conn.commit()

        super(TestCleanRawADICronApp, self).tearDown()

    def test_basic_run(self):
        cur = self.conn.cursor()
        # Ensure test table is present.
        statement = """
            INSERT INTO raw_adi
            (date, product_name, adi_count) VALUES
            (%(first)s, 'WinterFox', 11),
            (%(second)s, 'WinterFox', 23)
        """
        second = utc_now().date()
        first = second - datetime.timedelta(days=1)
        cur.execute(statement, {'first': first, 'second': second})

        # Ensure test table is present.
        statement = """
            INSERT INTO raw_adi_logs
            (report_date, product_name, count) VALUES
            (%(first)s, 'WinterFox', 11),
            (%(second)s, 'WinterFox', 23)
        """
        second = utc_now().date()
        first = second - datetime.timedelta(days=1)
        cur.execute(statement, {'first': first, 'second': second})
        self.conn.commit()

        # Run the crontabber job to remove the test table.
        config_manager = self._setup_config_manager(days_to_keep=1)
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

        # Basic assertion test of stored procedure.
        information = self._load_structure()
        assert information['clean-raw-adi']
        assert not information['clean-raw-adi']['last_error']
        assert information['clean-raw-adi']['last_success']

        # Ensure test row was removed
        cur.execute('SELECT date FROM raw_adi')
        result, = cur.fetchall()
        report_date = result[0]
        assert report_date == second

        cur.execute('SELECT report_date FROM raw_adi_logs')
        result, = cur.fetchall()
        report_date = result[0]
        assert report_date == second

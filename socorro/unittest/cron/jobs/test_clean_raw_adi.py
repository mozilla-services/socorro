import datetime

from nose.tools import eq_
from crontabber.app import CronTabber

from socorro.lib.datetimeutil import utc_now
from socorro.unittest.cron.jobs.base import IntegrationTestBase
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


class TestCleanRawADICronApp(IntegrationTestBase):

    def _setup_config_manager(self, days_to_keep=None):
        super(TestCleanRawADICronApp, self)._setup_config_manager
        return get_config_manager_for_crontabber(
            jobs=(
                'socorro.cron.jobs.clean_raw_adi.'
                'CleanRawADICronApp|1d'
            ),
            overrides={
                'crontabber.class-CleanRawADICronApp'
                '.days_to_keep': days_to_keep
            },
        )

    def tearDown(self):
        cur = self.conn.cursor()

        # Ensure that the test partition entry and table no longer exist.
        statement = """
        TRUNCATE raw_adi CASCADE
        """
        cur.execute(statement)
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
        self.conn.commit()

        # Run the crontabber job to remove the test table.
        config_manager = self._setup_config_manager(days_to_keep=1)
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

        # Basic assertion test of stored procedure.
        information = self._load_structure()
        assert information['clean-raw-adi']
        assert not information['clean-raw-adi']['last_error']
        assert information['clean-raw-adi']['last_success']

        # Ensure test row was removed
        cur.execute("""
            SELECT date FROM raw_adi
        """)
        result, = cur.fetchall()
        report_date = result[0]
        eq_(report_date, second)

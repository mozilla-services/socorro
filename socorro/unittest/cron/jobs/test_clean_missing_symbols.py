import datetime

from socorro.cron.crontabber_app import CronTabberApp
from socorro.lib.datetimeutil import utc_now
from socorro.unittest.cron.jobs.base import IntegrationTestBase


class TestCleanMissingSymbolsCronApp(IntegrationTestBase):

    def _setup_config_manager(self, days_to_keep=None):
        return super(TestCleanMissingSymbolsCronApp, self)._setup_config_manager(
            jobs_string='socorro.cron.jobs.clean_missing_symbols.CleanMissingSymbolsCronApp|1d',
            extra_value_source={
                'crontabber.class-CleanMissingSymbolsCronApp.days_to_keep': days_to_keep
            },
        )

    def tearDown(self):
        cur = self.conn.cursor()

        # Ensure that the test partition entry and table no longer exist.
        statement = """
        TRUNCATE missing_symbols CASCADE
        """
        cur.execute(statement)
        self.conn.commit()

        super(TestCleanMissingSymbolsCronApp, self).tearDown()

    def test_basic_run(self):
        cur = self.conn.cursor()
        # Ensure test table is present.
        statement = """
            INSERT INTO missing_symbols
            (date_processed, debug_file, debug_id, code_file, code_id)
            VALUES
            (%(first)s, 'foo.pdb', '0420', 'foo.py', '123'),
            (%(second)s, 'bar.pdb', '65EA9', 'bar.py', null)
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
        assert information['clean-missing-symbols']
        assert not information['clean-missing-symbols']['last_error']
        assert information['clean-missing-symbols']['last_success']

        # Ensure expected test row was removed
        cur.execute("""
            SELECT date_processed FROM missing_symbols
        """)
        first, = cur.fetchall()
        date_processed = first[0]
        assert date_processed == second

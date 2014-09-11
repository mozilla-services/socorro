# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock
from nose.plugins.attrib import attr
from nose.tools import eq_

from socorro.lib.util import DotDict

from crontabber.app import CronTabber

from socorro.unittest.cron.jobs.base import IntegrationTestBase

from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


#==============================================================================
@attr(integration='postgres')
class IntegrationTestReprocessingJobs(IntegrationTestBase):

    def _clear_tables(self):
        self.conn.cursor().execute("""
            TRUNCATE
                reprocessing_jobs
            CASCADE
        """)

    def setUp(self):
        super(IntegrationTestReprocessingJobs, self).setUp()
        self._clear_tables()

    def tearDown(self):
        """
        The reason why this is all necessary, including the commit, is that
        we're testing a multi-process tool, crontabber.
        The changes made to the database happen in a transaction
        that crontabber doesn't have visibility into.

        """
        self._clear_tables()
        self.conn.commit()
        super(IntegrationTestReprocessingJobs, self).tearDown()

    def _setup_config_manager(self):
        self.rabbit_queue_mocked = Mock()

        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.reprocessingjobs.ReprocessingJobsApp|5m',
            overrides={
                'crontabber.class-ReprocessingJobsApp.queuing.queuing_class':
                    self.rabbit_queue_mocked
            }
        )

    def test_reprocessing(self):
        """ Simple test of reprocessing"""
        config_manager = self._setup_config_manager()
        c = config_manager.get_config()

        cursor = self.conn.cursor()

        # Create partitions to support the status query
        # Load report_partition_info data
        cursor.execute("""
            INSERT into reprocessing_jobs
              (crash_id)
            VALUES
             ('13c4a348-5d04-11e3-8118-d231feb1dc81')
        """)

        # We have to do this here to accommodate separate crontabber processes
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = tab.job_state_database['reprocessing-jobs']
            assert not information['last_error']
            assert information['last_success']

        cursor = self.conn.cursor()
        cursor.execute('select count(*) from reprocessing_jobs')

        res_expected = 0
        res, = cursor.fetchone()
        eq_(res, res_expected)

        self.rabbit_queue_mocked.return_value.save_raw_crash \
            .assert_called_once_with(
                DotDict({'legacy_processing': 0}),
                [],
                '13c4a348-5d04-11e3-8118-d231feb1dc81'
            )

    def test_reprocessing_exception(self):
        config_manager = self._setup_config_manager()

        cursor = self.conn.cursor()

        # Test exception handling
        cursor.execute("""
            alter table reprocessing_jobs RENAME TO test_reprocessing_jobs
        """)
        # Need to commit this in order to test the exception handling
        # because the crontabber invocation happens in a different Pg
        # transaction.
        self.conn.commit()

        try:
            with config_manager.context() as config:
                tab = CronTabber(config)
                tab.run_all()

            state = tab.job_state_database['reprocessing-jobs']
            res_expected = "<class 'psycopg2.ProgrammingError'>"
            res = state['last_error']['type']
            eq_(res, res_expected)

        finally:
            # Change table name back
            cursor.execute("""
                alter table test_reprocessing_jobs RENAME TO reprocessing_jobs
            """)
            self.conn.commit()

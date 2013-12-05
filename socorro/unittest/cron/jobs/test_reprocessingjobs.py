# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock
from nose.plugins.attrib import attr

from socorro.cron import crontabber

from ..base import IntegrationTestCaseBase


#==============================================================================
@attr(integration='postgres')
class IntegrationTestReprocessingJobs(IntegrationTestCaseBase):

    def _clear_tables(self):
        self.conn.cursor().execute("""
            TRUNCATE
                crontabber
                , crontabber_log
                --, reprocessing_jobs
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
        _super = super(IntegrationTestReprocessingJobs,
                       self)._setup_config_manager

        self.rabbit_queue_mocked = Mock()

        return _super(
            'socorro.cron.jobs.reprocessingjobs.ReprocessingJobsApp|5m',
            extra_value_source={'queue_class': self.rabbit_queue_mocked}
        )

    def test_reprocessing(self):
        """ Simple test of reprocessing"""
        config_manager = self._setup_config_manager()

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
            tab = crontabber.CronTabber(config)
            tab.run_all()

        cursor.execute('select count(*) from reprocessing_jobs')

        res_expected = 0
        res, = cursor.fetchone()
        self.assertEqual(res, res_expected)

    def test_reprocessing_exception(self):
        config_manager = self._setup_config_manager()

        cursor = self.conn.cursor()

        # Test exception handling
        cursor.execute('drop table reprocessing_jobs')
        self.conn.commit()

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

        cursor.execute("""
            select json_extract_path_text(last_error, 'type')
            from crontabber
        """)
        res_expected = "<class 'psycopg2.ProgrammingError'>"
        res, = cursor.fetchone()
        self.assertEqual(res, res_expected)

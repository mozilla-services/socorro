# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import datetime
import json
import mock
from socorro.cron import crontabber
from socorro.cron import base
from socorro.lib.datetimeutil import utc_now
from ..base import TestCaseBase


class TestMatviews(TestCaseBase):

    def setUp(self):
        super(TestMatviews, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.mocked_connection = mock.Mock()
        self.psycopg2 = self.psycopg2_patcher.start()

    def tearDown(self):
        super(TestMatviews, self).tearDown()
        self.psycopg2_patcher.stop()

    def test_one_matview_alone(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.jobs.test_matviews.ReportsCleanJob|1d\n'
          'socorro.unittest.cron.jobs.test_matviews.FTPScraperJob|1d\n'
          ''
          'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            # not a huge fan of this test because it's so specific
            from socorro.cron.jobs.matviews import ProductVersionsCronApp
            proc_name = ProductVersionsCronApp.proc_name
            (self.psycopg2().cursor().callproc
             .assert_called_once_with(proc_name))

    @mock.patch('socorro.cron.crontabber.utc_now')
    def test_all_matviews(self, mocked_utc_now):

        # Pretend it's 03AM UTC
        def mock_utc_now():
            n = utc_now()
            n = n.replace(hour=3)
            return n

        mocked_utc_now.side_effect = mock_utc_now

        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.jobs.test_matviews.ReportsCleanJob|1d\n'
          'socorro.unittest.cron.jobs.test_matviews.FTPScraperJob|1d\n'
          ''
          'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d\n'
          'socorro.cron.jobs.matviews.SignaturesCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.TCBSCronApp|1d\n'
          'socorro.cron.jobs.matviews.ADUCronApp|1d\n'
          'socorro.cron.jobs.matviews.NightlyBuildsCronApp|1d\n'
          'socorro.cron.jobs.matviews.BuildADUCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.CrashesByUserCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.CrashesByUserBuildCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.CorrelationsCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.HomePageGraphCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.HomePageGraphBuildCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.TCBSBuildCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.ExplosivenessCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.GraphicsDeviceCronApp|1d|02:00\n'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))

            for app_name in ('product-versions-matview',
                             'signatures-matview',
                             'tcbs-matview',
                             'adu-matview',
                             'nightly-builds-matview',
                             'build-adu-matview',
                             'crashes-by-user-matview',
                             'crashes-by-user-build-matview',
                             'correlations-matview',
                             'home-page-graph-matview',
                             'home-page-graph-matview-build',
                             'tcbs-build-matview',
                             'explosiveness-matview',
                             'graphics-device-matview',):

                self.assertTrue(app_name in information, app_name)
                self.assertTrue(not information[app_name]['last_error'],
                                app_name)
                self.assertTrue(information[app_name]['last_success'],
                                app_name)

            self.assertEqual(self.psycopg2().cursor().callproc.call_count, 14)
            for call in self.psycopg2().cursor().callproc.mock_calls:
                __, call_args, __ = call
                if len(call_args) > 1:
                    # e.g. ('update_signatures', [datetime.date(2012, 6, 25)])
                    # then check that it's a datetime.date instance
                    self.assertTrue(isinstance(call_args[1][0], datetime.date))
            # the reason we expect 14 * 2 + 2 commit() calls is because,
            # for each job it commits when it writes to the JSON database but
            # postgresql jobs also commit the actual run. We have 16 jobs,
            # 14 of them are postgresql jobs writing twice, 2 of them are
            # regular jobs writing only once.
            self.assertEqual(self.psycopg2().commit.call_count, 14 * 2 + 2)

    def test_reports_clean_with_dependency(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.cron.jobs.matviews.DuplicatesCronApp|1h\n'
          'socorro.cron.jobs.matviews.ReportsCleanCronApp|1h'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['reports-clean']
            assert not information['reports-clean']['last_error']
            assert information['reports-clean']['last_success']

            # not a huge fan of this test because it's so specific
            calls = self.psycopg2().cursor().callproc.mock_calls
            call = calls[-1]
            __, called, __ = list(call)
            self.assertEqual(called[0], 'update_reports_clean')

    def test_duplicates(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.cron.jobs.matviews.DuplicatesCronApp|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['duplicates']
            assert not information['duplicates']['last_error']
            assert information['duplicates']['last_success']

            # not a huge fan of this test because it's so specific
            proc_name = 'update_reports_duplicates'
            calls = self.psycopg2().cursor().callproc.mock_calls
            call1, call2 = calls
            __, called, __ = call1
            assert called[0] == proc_name, called[0]
            start, end = called[1]
            self.assertEqual(end - start, datetime.timedelta(hours=1))

            __, called, __ = call2
            assert called[0] == proc_name, called[0]
            start, end = called[1]
            self.assertEqual(end - start, datetime.timedelta(hours=1))


class _Job(base.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


class ReportsCleanJob(_Job):
    app_name = 'reports-clean'


class FTPScraperJob(_Job):
    app_name = 'ftpscraper'

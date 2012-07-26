# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import mock
from socorro.cron import crontabber
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

    def test_all_matviews(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d\n'
          'socorro.cron.jobs.matviews.SignaturesCronApp|1d\n'
          'socorro.cron.jobs.matviews.OSVersionsCronApp|1d\n'
          'socorro.cron.jobs.matviews.TCBSCronApp|1d\n'
          'socorro.cron.jobs.matviews.ADUCronApp|1d\n'
          'socorro.cron.jobs.matviews.DailyCrashesCronApp|1d\n'
          'socorro.cron.jobs.matviews.HangReportCronApp|1d\n'
          'socorro.cron.jobs.matviews.RankCompareCronApp|1d\n'
          'socorro.cron.jobs.matviews.NightlyBuildsCronApp|1d\n'
          'socorro.cron.jobs.matviews.BuildADUCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.ProductADUCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.CrashesByUserCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.CrashesByUserBuildCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.CorrelationsCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.HomePageGraphCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.HomePageGraphBuildCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.SignatureProductsCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.SignatureProductsRollupCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.TCBSBuildCronApp|1d|02:00\n'
          'socorro.cron.jobs.matviews.ExplosivenessBuildCronApp|1d|02:00\n'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))

            for app_name in ('product-versions-matview',
                             'signatures-matview',
                             'os-versions-matview',
                             'tcbs-matview',
                             'adu-matview',
                             'daily-crashes-matview',
                             'hang-report-matview',
                             'rank-compare-matview',
                             'nightly-builds-matview',
                             'build-adu-matview',
                             'product-adu-matview',
                             'crashes-by-user-matview',
                             'crashes-by-user-build-matview',
                             'correlations-matview',
                             'home-page-graph-matview',
                             'home-page-graph-matview-build',
                             'signatures-products-matview',
                             'signatures-products-rollup-matview',
                             'tcbs-build-matview',
                             'explosiveness-matview'):

                self.assertTrue(app_name in information, app_name)
                self.assertTrue(not information[app_name]['last_error'],
                                app_name)
                self.assertTrue(information[app_name]['last_success'],
                                app_name)

            self.assertEqual(self.psycopg2().cursor().callproc.call_count, 9)
            for call in self.psycopg2().cursor().callproc.mock_calls:
                __, call_args, __ = call
                if len(call_args) > 1:
                    # e.g. ('update_signatures', [datetime.date(2012, 6, 25)])
                    # then check that it's a datetime.date instance
                    self.assertTrue(isinstance(call_args[1][0], datetime.date))

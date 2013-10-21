# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
from nose.plugins.attrib import attr

from socorro.cron import crontabber
from socorro.cron import base
from socorro.lib.datetimeutil import utc_now
from ..base import IntegrationTestCaseBase

from socorro.cron.jobs import matviews


@attr(integration='postgres')
class TestMatviews(IntegrationTestCaseBase):

    def setUp(self):
        super(TestMatviews, self).setUp()

        # remember what the `proc_name` was of all apps in matviews
        self.old_proc_names = {}
        for thing_name in dir(matviews):
            thing = getattr(matviews, thing_name)
            if hasattr(thing, 'proc_name'):
                self.old_proc_names[thing] = thing.proc_name
                thing.proc_name = 'harmless'

        # these have very different signatures
        matviews.DuplicatesCronApp.proc_name = 'harmless_twotimestamps'
        matviews.ReportsCleanCronApp.proc_name = 'harmless_timestamp'

        # add the benign stored procedure
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE OR REPLACE FUNCTION
              public.harmless(harmless_date date DEFAULT 'now()')
            RETURNS boolean
            LANGUAGE plpgsql
            AS $function$
            BEGIN
                RETURN True;
            END
            $function$
        """)
        cursor.execute("""
            CREATE OR REPLACE FUNCTION
              public.harmless_timestamp(harmless_date timestamp with time zone DEFAULT 'now()')
            RETURNS boolean
            LANGUAGE plpgsql
            AS $function$
            BEGIN
                RETURN True;
            END
            $function$

        """)
        cursor.execute("""

            CREATE OR REPLACE FUNCTION
              public.harmless_twotimestamps(
                  harmless_date timestamp with time zone DEFAULT 'now()',
                  other_date timestamp with time zone DEFAULT 'now()'
              )
            RETURNS boolean
            LANGUAGE plpgsql
            AS $function$
            BEGIN
                RETURN True;
            END
            $function$
        """)
        cursor.close()
        self.conn.commit()

    def tearDown(self):
        super(TestMatviews, self).tearDown()
        cursor = self.conn.cursor()
        cursor.execute("DROP FUNCTION harmless(date)")
        cursor.execute("DROP FUNCTION harmless_twotimestamps(timestamp with time zone, timestamp with time zone)")
        self.conn.commit()
        self.conn.close()

        # restore the old proc_name attributes
        for class_, old_proc_name in self.old_proc_names.items():
            class_.proc_name = old_proc_name


    def test_one_matview_alone(self):
        config_manager = self._setup_config_manager(
          'socorro.unittest.cron.jobs.test_matviews.ReportsCleanJob|1d\n'
          'socorro.unittest.cron.jobs.test_matviews.FTPScraperJob|1d\n'
          ''
          'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['reports-clean']
            assert not information['reports-clean']['last_error']
            assert information['reports-clean']['last_success']

            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

            assert information['product-versions-matview']
            assert not information['product-versions-matview']['last_error']
            assert information['product-versions-matview']['last_success']

    @mock.patch('socorro.cron.crontabber.utc_now')
    def test_all_matviews(self, mocked_utc_now):

        # Pretend it's 03AM UTC
        def mock_utc_now():
            n = utc_now()
            n = n.replace(hour=3)
            return n

        mocked_utc_now.side_effect = mock_utc_now

        config_manager = self._setup_config_manager(
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

            information = self._load_structure()

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
                self.assertTrue(
                    not information[app_name]['last_error'],
                    app_name
                )
                self.assertTrue(
                    information[app_name]['last_success'],
                    app_name
                )

    def test_reports_clean_with_dependency(self):
        config_manager = self._setup_config_manager(
          'socorro.cron.jobs.matviews.DuplicatesCronApp|1h\n'
          'socorro.cron.jobs.matviews.ReportsCleanCronApp|1h'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['reports-clean']
            assert not information['reports-clean']['last_error']
            assert information['reports-clean']['last_success']

    def test_duplicates(self):
        config_manager = self._setup_config_manager(
          'socorro.cron.jobs.matviews.DuplicatesCronApp|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['duplicates']
            assert not information['duplicates']['last_error']
            assert information['duplicates']['last_success']


class _Job(base.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


class ReportsCleanJob(_Job):
    app_name = 'reports-clean'


class FTPScraperJob(_Job):
    app_name = 'ftpscraper'

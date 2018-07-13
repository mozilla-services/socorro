# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crontabber import base
import mock

from socorro.cron.crontabber_app import CronTabberApp
from socorro.cron.jobs import matviews
from socorro.lib.datetimeutil import utc_now
from socorro.unittest.cron.jobs.base import IntegrationTestBase


class TestMatviews(IntegrationTestBase):

    def _setup_config_manager(self, jobs):
        return super(TestMatviews, self)._setup_config_manager(
            jobs_string=jobs
        )

    def setUp(self):
        super(TestMatviews, self).setUp()

        # remember what the `proc_name` was of all apps in matviews
        self.old_proc_names = {}
        for thing_name in dir(matviews):
            thing = getattr(matviews, thing_name)
            if hasattr(thing, 'proc_name'):
                self.old_proc_names[thing] = thing.proc_name
                thing.proc_name = 'harmless'

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
        cursor = self.conn.cursor()
        cursor.execute("DROP FUNCTION harmless(date)")
        cursor.execute(
            "DROP FUNCTION harmless_twotimestamps"
            "(timestamp with time zone, timestamp with time zone)")
        self.conn.commit()

        # restore the old proc_name attributes
        for class_, old_proc_name in self.old_proc_names.items():
            class_.proc_name = old_proc_name

        super(TestMatviews, self).tearDown()

    def test_one_matview_alone(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.jobs.test_matviews.FTPScraperJob|1d\n'
            ''
            'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d'
        )

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

            assert information['product-versions-matview']
            assert not information['product-versions-matview']['last_error']
            assert information['product-versions-matview']['last_success']

    @mock.patch('crontabber.app.utc_now')
    def test_all_matviews(self, mocked_utc_now):

        # Pretend it's 03AM UTC
        def mock_utc_now():
            n = utc_now()
            n = n.replace(hour=3)
            return n

        mocked_utc_now.side_effect = mock_utc_now

        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.jobs.test_matviews.FTPScraperJob|1d\n'
            'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d\n'
        )

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

        information = self._load_structure()

        for app_name in ('product-versions-matview',):
            assert app_name in information
            assert not information[app_name]['last_error']
            assert information[app_name]['last_success']


class _Job(base.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


class FTPScraperJob(_Job):
    app_name = 'ftpscraper'

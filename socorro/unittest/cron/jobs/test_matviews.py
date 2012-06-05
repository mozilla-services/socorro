import re
import sys
import datetime
import json
from cStringIO import StringIO
import mock
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from nose.plugins.attrib import attr
from socorro.lib.datetimeutil import utc_now
from socorro.cron import crontabber
from configman import ConfigurationManager, Namespace

from .base import TestCaseBase


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
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert any(not v['last_error'] for v in information.values())
            self.assertEqual(self.psycopg2().cursor().callproc.call_count, 9)

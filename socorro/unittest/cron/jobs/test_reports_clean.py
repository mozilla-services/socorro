# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
import unittest
import json
import tempfile
import mock

from configman import ConfigurationManager
from socorro.cron import crontabber
from ..base import TestCaseBase, DSN


class TestReportsClean(TestCaseBase):

    def setUp(self):
        super(TestReportsClean, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.mocked_connection = mock.Mock()
        self.psycopg2 = self.psycopg2_patcher.start()

    def tearDown(self):
        super(TestReportsClean, self).tearDown()
        self.psycopg2_patcher.stop()

    def test_dependency_prerequisite(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.cron.jobs.reports_clean.ReportsCleanCronApp|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            # no file is created because it's unable to run anything
            self.assertTrue(not os.path.isfile(json_file))

    def test_one_run_with_dependency(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.cron.jobs.duplicates.DuplicatesCronApp|1h\n'
          'socorro.cron.jobs.reports_clean.ReportsCleanCronApp|1h'
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

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os
import shutil
import unittest
import json
import tempfile
import mock

from configman import ConfigurationManager
from socorro.cron import crontabber
from ..base import TestCaseBase


class TestDuplicates(TestCaseBase):

    def setUp(self):
        super(TestDuplicates, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.mocked_connection = mock.Mock()
        self.psycopg2 = self.psycopg2_patcher.start()

    def tearDown(self):
        super(TestDuplicates, self).tearDown()
        self.psycopg2_patcher.stop()

    def test_one_matview_alone(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.cron.jobs.duplicates.DuplicatesCronApp|1d'
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

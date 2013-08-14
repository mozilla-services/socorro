# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import mock
import shutil
import os
from configman import ConfigurationManager
from socorro.cron import crontabber
from ..base import TestCaseBase
import datetime

from socorro.lib.datetimeutil import utc_now


from socorro.external.fs.crashstorage import FSDatedRadixTreeStorage

#==============================================================================
class TestCleanupRadix(TestCaseBase):
    CRASH_ID = "0bba929f-8721-460c-dead-a43c20071025"

    def setUp(self):
        super(TestCleanupRadix, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.mocked_connection = mock.Mock()
        self.psycopg2 = self.psycopg2_patcher.start()

        with self._setup_radix_storage().context() as config:
            self.fsrts = FSDatedRadixTreeStorage(config)

    def tearDown(self):
        super(TestCleanupRadix, self).tearDown()
        self.psycopg2_patcher.stop()
        shutil.rmtree(self.fsrts.config.fs_root)

    def _setup_radix_storage(self):
        mock_logging = mock.Mock()
        required_config = FSDatedRadixTreeStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'minute_slice_interval': 1
          }]
        )
        return config_manager

    def _setup_config_manager(self):
        _super = super(TestCleanupRadix, self)._setup_config_manager
        config_manager, json_file = _super(
            'socorro.cron.jobs.cleanup_radix.RadixCleanupCronApp|1d',
            {
                'crontabber.class-RadixCleanupCronApp.storage0': {
                    'crashstorage_class': FSDatedRadixTreeStorage
                }
            }
        )
        return config_manager, json_file

    def test_cleanup_radix(self):
        self.fsrts._current_slot = lambda: ['00', '00_00']
        self.fsrts.save_raw_crash({
            "test": "TEST"
        }, {
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }, self.CRASH_ID)
        self.fsrts._current_slot = lambda: ['10', '00_01']

        self.assertEqual(list(self.fsrts.new_crashes()), [self.CRASH_ID])
        self.assertEqual(list(self.fsrts.new_crashes()), [])

        config_manager, json_file = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)

        tab.run_all()

        self.assertEqual(os.listdir(self.fsrts.config.fs_root), [])

        future = (utc_now() + datetime.timedelta(days=10)).strftime("%Y%m%d")
        future_id = "0bba929f-8721-460c-dead-a43c%s" % future

        self.fsrts._current_slot = lambda: ['00', '00_00']
        self.fsrts.save_raw_crash({
            "test": "TEST"
        }, {
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }, future_id)
        self.fsrts._current_slot = lambda: ['10', '00_01']

        self.assertEqual(list(self.fsrts.new_crashes()), [future_id])
        self.assertEqual(list(self.fsrts.new_crashes()), [])

        tab.run_all()

        self.assertEqual(os.listdir(self.fsrts.config.fs_root), [future])

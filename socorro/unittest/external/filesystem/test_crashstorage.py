# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import os.path
import shutil
import tempfile
import inspect
import unittest
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.external.filesystem.crashstorage import (
  FileSystemRawCrashStorage,
  FileSystemThrottledCrashStorage,
  FileSystemCrashStorage)
from socorro.lib.util import DotDict
from configman import ConfigurationManager
from mock import Mock


class TestFileSystemCrashStorage(unittest.TestCase):

    def setUp(self):
        self.std_tmp_dir = tempfile.mkdtemp()
        self.def_tmp_dir = tempfile.mkdtemp()
        self.pro_tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.std_tmp_dir)

    @staticmethod
    def _get_class_methods(klass):
        return dict((n, ref) for (n, ref)
                    in inspect.getmembers(klass, inspect.ismethod)
                    if not n.startswith('_') and n in klass.__dict__)

    def _find_file(self, in_, filename):
        found = []
        for f in os.listdir(in_):
            path = os.path.join(in_, f)
            if os.path.isdir(path):
                found.extend(self._find_file(path, filename))
            elif os.path.isfile(path) and filename in path:
                found.append(path)
        return found

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = FileSystemCrashStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'std_fs_root': self.std_tmp_dir,
            'def_fs_root': self.def_tmp_dir,
            'pro_fs_root': self.pro_tmp_dir,
          }]
        )
        return config_manager

    def _common_basic_test(self, config, crashstorage):
        fake_dump = 'this is a fake dump'
        self.assertEqual(list(crashstorage.new_crashes()), [])
        raw = {"name": "Peter",
               "legacy_processing": 0,
               "submitted_timestamp": '2012-03-14 15:10:33'}
        crashstorage.save_raw_crash(
          raw,
          fake_dump,
          "114559a5-d8e6-428c-8b88-1c1f22120314"
        )

        fake_dumps = {None: 'this is a fake dump', 'aux01': 'aux01 fake dump'}
        raw = {"name": "Lars",
               "legacy_processing": 0,
               "submitted_timestamp": '2012-05-04 15:10:33'}
        crashstorage.save_raw_crash(
          raw,
          fake_dumps,
          "114559a5-d8e6-428c-8b88-1c1f22120504"
        )
        self.assertEqual(sorted(list(crashstorage.new_crashes())),
                         sorted(["114559a5-d8e6-428c-8b88-1c1f22120314",
                          "114559a5-d8e6-428c-8b88-1c1f22120504",
                         ]))

        self.assertTrue(
          os.path.exists(
            crashstorage.std_crash_store.getJson(
                '114559a5-d8e6-428c-8b88-1c1f22120314')))
        self.assertTrue(
          os.path.exists(
            crashstorage.std_crash_store.getDump(
                '114559a5-d8e6-428c-8b88-1c1f22120314')))
        self.assertTrue(
          os.path.exists(
            crashstorage.std_crash_store.getJson(
                '114559a5-d8e6-428c-8b88-1c1f22120504')))
        self.assertTrue(
          os.path.exists(
            crashstorage.std_crash_store.getDump(
                '114559a5-d8e6-428c-8b88-1c1f22120504')))

        meta = crashstorage.get_raw_crash(
          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertTrue(isinstance(meta, DotDict))
        self.assertEqual(meta['name'], 'Peter')

        dump = crashstorage.get_raw_dump(
          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertTrue(isinstance(dump, basestring))
        self.assertTrue("fake dump" in dump)

        dumps = crashstorage.get_raw_dumps(
          '114559a5-d8e6-428c-8b88-1c1f22120504'
        )
        self.assertEqual(['upload_file_minidump', 'aux01'], dumps.keys())
        self.assertEqual(['this is a fake dump', 'aux01 fake dump'],
                         dumps.values())

        crashstorage.remove('114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getJson,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getDump,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(CrashIDNotFound,
                          crashstorage.remove,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(CrashIDNotFound,
                          crashstorage.get_raw_crash,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(CrashIDNotFound,
                          crashstorage.get_raw_dump,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')

    def _common_throttle_test(self, config, crashstorage):
        fake_dump = 'this is a fake dump'
        crashstorage = FileSystemThrottledCrashStorage(config)
        self.assertEqual(list(crashstorage.new_crashes()), [])
        raw = {"name": "Peter",
               "legacy_processing": 1,
               "submitted_timestamp": '2012-05-04 15:10:33'}
        crashstorage.save_raw_crash(
          raw,
          fake_dump,
          "114559a5-d8e6-428c-8b88-1c1f22120314"
        )

        fake_dumps = {None: 'this is a fake dump', 'aux01': 'aux01 fake dump'}
        raw = {"name": "Lars",
               "legacy_processing": 0,
               "submitted_timestamp": '2012-05-04 15:10:33'}
        crashstorage.save_raw_crash(
          raw,
          fake_dumps,
          "114559a5-d8e6-428c-8b88-1c1f22120504"
        )
        self.assertEqual(list(crashstorage.new_crashes()),
                         ["114559a5-d8e6-428c-8b88-1c1f22120504",])

        self.assertTrue(
          os.path.exists(
            crashstorage.def_crash_store.getJson(
                '114559a5-d8e6-428c-8b88-1c1f22120314')))
        self.assertTrue(
          os.path.exists(
            crashstorage.def_crash_store.getDump(
                '114559a5-d8e6-428c-8b88-1c1f22120314')))
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getJson,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getDump,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')

        meta = crashstorage.get_raw_crash(
          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertTrue(isinstance(meta, DotDict))
        self.assertEqual(meta['name'], 'Peter')

        dump = crashstorage.get_raw_dump(
          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertTrue(isinstance(dump, basestring))
        self.assertTrue("fake dump" in dump)

        crashstorage.remove('114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.def_crash_store.getJson,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.def_crash_store.getDump,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getJson,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getDump,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')

    def test_filesystem_raw_crashstorage(self):
        config_manager = self._common_config_setup()
        with config_manager.context() as config:
            crashstorage = FileSystemRawCrashStorage(config)
            self._common_basic_test(config, crashstorage)

    def test_filesystem_throttled_crashstorage(self):
        config_manager = self._common_config_setup()
        with config_manager.context() as config:
            crashstorage = FileSystemThrottledCrashStorage(config)
            self._common_basic_test(config, crashstorage)
            self._common_throttle_test(config, crashstorage)

    def test_filesystem_crashstorage(self):
        config_manager = self._common_config_setup()
        with config_manager.context() as config:
            crashstorage = FileSystemCrashStorage(config)
            self._common_throttle_test(config, crashstorage)

            crashstorage = FileSystemCrashStorage(config)
            self.assertEqual(list(crashstorage.new_crashes()), [])

            processed_crash = {"name": "Peter", "legacy_processing": 1}
            self.assertRaises(
              CrashIDNotFound,
              crashstorage.save_processed,
              processed_crash
            )
            processed_crash = {"name": "Peter",
                               "uuid": "114559a5-d8e6-428c-8b88-1c1f22120314",
                               }
            crash_id = processed_crash['uuid']
            crashstorage.save_processed(processed_crash)
            returned_processed_crash = crashstorage.get_processed(crash_id)
            self.assertEqual(processed_crash, returned_processed_crash)
            self.assertTrue(isinstance(returned_processed_crash,
                                       DotDict))

            crashstorage.remove(crash_id)
            self.assertRaises(CrashIDNotFound,
                              crashstorage.get_processed,
                              crash_id)
            crashstorage.remove(crash_id)

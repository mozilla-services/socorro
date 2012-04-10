import os
import os.path
import json
import shutil
import tempfile
import inspect
import unittest
from socorro.external.crashstorage_base import (
  CrashStorageBase, OOIDNotFoundException)
from socorro.external.filesystem.crashstorage import (
  FileSystemRawCrashStorage,
  FileSystemThrottledCrashStorage,
  FileSystemCrashStorage)
from configman import ConfigurationManager
from mock import Mock


class TestFileSystemRawCrashStorage(unittest.TestCase):

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

    #def test_abstract_classism(self):
        ## XXX work in progress, might change prints ot asserts
        #interface = self._get_class_methods(CrashStorageBase)
        #implementor = self._get_class_methods(FileSystemRawCrashStorage)
        #for name in interface:
            #if name not in implementor:
                #print FileSystemRawCrashStorage.__name__,
                #print "doesn't implement", name

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
        self.assertEqual(list(crashstorage.new_ooids()), [])
        raw = {"name": "Peter", "legacy_processing": 0}
        self.assertRaises(
          OOIDNotFoundException,
          crashstorage.save_raw_crash,
          raw,
          fake_dump  # as a stand in for the binary dump file
        )
        raw = {"name":"Peter",
               "ooid":"114559a5-d8e6-428c-8b88-1c1f22120314",
               "legacy_processing": 0}
        crashstorage.save_raw_crash(raw, fake_dump)

        self.assertTrue(
          os.path.exists(
            crashstorage.std_crash_store.getJson(
                '114559a5-d8e6-428c-8b88-1c1f22120314')))
        self.assertTrue(
          os.path.exists(
            crashstorage.std_crash_store.getDump(
                '114559a5-d8e6-428c-8b88-1c1f22120314')))

        meta = crashstorage.get_raw_crash(
          '114559a5-d8e6-428c-8b88-1c1f22120314')
        assert isinstance(meta, dict)
        self.assertEqual(meta['name'], 'Peter')

        dump = crashstorage.get_raw_dump(
          '114559a5-d8e6-428c-8b88-1c1f22120314')
        assert isinstance(dump, basestring)
        self.assertTrue("fake dump" in dump)

        crashstorage.remove('114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getJson,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OSError,
                          crashstorage.std_crash_store.getDump,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OOIDNotFoundException,
                          crashstorage.remove,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OOIDNotFoundException,
                          crashstorage.get_raw_crash,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertRaises(OOIDNotFoundException,
                          crashstorage.get_raw_dump,
                          '114559a5-d8e6-428c-8b88-1c1f22120314')

    def _common_throttle_test(self, config, crashstorage):
        fake_dump = 'this is a fake dump'
        crashstorage = FileSystemThrottledCrashStorage(config)
        self.assertEqual(list(crashstorage.new_ooids()), [])
        raw = {"name": "Peter", "legacy_processing": 1}
        self.assertRaises(
          OOIDNotFoundException,
          crashstorage.save_raw_crash,
          raw,
          fake_dump  # as a stand in for the binary dump file
        )
        raw = {"name":"Peter",
               "ooid":"114559a5-d8e6-428c-8b88-1c1f22120314",
               "legacy_processing": 1}
        result = crashstorage.save_raw_crash(raw, fake_dump)
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
        assert isinstance(meta, dict)
        self.assertEqual(meta['name'], 'Peter')

        dump = crashstorage.get_raw_dump(
          '114559a5-d8e6-428c-8b88-1c1f22120314')
        assert isinstance(dump, basestring)
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
            self.assertEqual(list(crashstorage.new_ooids()), [])

            processed_crash = {"name": "Peter", "legacy_processing": 1}
            self.assertRaises(
              OOIDNotFoundException,
              crashstorage.save_processed,
              processed_crash
            )
            processed_crash = {"name":"Peter",
                               "ooid":"114559a5-d8e6-428c-8b88-1c1f22120314",
                               }
            ooid = processed_crash['ooid']
            crashstorage.save_processed(processed_crash)
            returned_procesessed_crash = crashstorage.get_processed(ooid)
            self.assertEqual(processed_crash, returned_procesessed_crash)

            crashstorage.remove(ooid)
            self.assertRaises(OOIDNotFoundException,
                              crashstorage.get_processed,
                              ooid)
            self.assertRaises(OOIDNotFoundException,
                              crashstorage.remove,
                              ooid)




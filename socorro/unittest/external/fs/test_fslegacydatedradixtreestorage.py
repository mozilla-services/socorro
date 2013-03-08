import unittest
import os
import shutil
from mock import Mock
from configman import ConfigurationManager

from socorro.external.fs.crashstorage import FSLegacyDatedRadixTreeStorage
from socorro.external.crashstorage_base import CrashIDNotFound


class TestFSLegacyDatedRadixTreeStorage(unittest.TestCase):
    CRASH_ID_1 = "0bba929f-8721-460c-dead-a43c20071025"
    CRASH_ID_2 = "0bba929f-8721-460c-dead-a43c20071026"

    def setUp(self):
        with self._common_config_setup().context() as config:
            self.fsrts = FSLegacyDatedRadixTreeStorage(config)

    def tearDown(self):
        shutil.rmtree(self.fsrts.config.fs_root)

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = FSLegacyDatedRadixTreeStorage.get_required_config()
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

    def _make_test_crash(self):
        self.fsrts.save_raw_crash({
            "test": "TEST"
        }, {
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }, self.CRASH_ID_1)

    def test_save_raw_crash(self):
        self._make_test_crash()
        self.assertTrue(os.path.islink(
            os.path.join(
              self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
              self.fsrts._get_date_root_name(self.CRASH_ID_1))))
        self.assertTrue(os.path.exists(
            os.path.join(
              self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
              self.fsrts._get_date_root_name(self.CRASH_ID_1),
              self.CRASH_ID_1)))

    def test_get_raw_crash(self):
        self._make_test_crash()
        self.assertEqual(self.fsrts.get_raw_crash(self.CRASH_ID_1)['test'],
                         "TEST")
        self.assertRaises(CrashIDNotFound, self.fsrts.get_raw_crash,
                          self.CRASH_ID_2)

    def test_get_raw_dump(self):
        self._make_test_crash()
        self.assertEqual(self.fsrts.get_raw_dump(self.CRASH_ID_1, 'foo'),
                         "bar")
        self.assertEqual(self.fsrts.get_raw_dump(self.CRASH_ID_1,
                                                 self.fsrts.config.dump_field),
                         "baz")
        self.assertRaises(CrashIDNotFound, self.fsrts.get_raw_dump,
                          self.CRASH_ID_2, "foo")
        self.assertRaises(IOError, self.fsrts.get_raw_dump, self.CRASH_ID_1,
                          "foor")

    def test_get_raw_dumps(self):
        self._make_test_crash()
        self.assertEqual(self.fsrts.get_raw_dumps(self.CRASH_ID_1), {
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        })
        self.assertRaises(CrashIDNotFound, self.fsrts.get_raw_dumps,
                          self.CRASH_ID_2)

    def test_remove(self):
        self._make_test_crash()
        self.fsrts.remove(self.CRASH_ID_1)

        parent = os.path.realpath(
            os.path.join(
              self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
              self.fsrts._get_date_root_name(self.CRASH_ID_1)))

        p = os.path.join(parent, self.CRASH_ID_1)
        self.assertTrue(not os.path.exists(p))

        p = os.path.dirname(p)
        self.assertTrue(not os.path.exists(p))

        p = os.path.dirname(p)
        self.assertTrue(not os.path.exists(p))

        self.assertRaises(CrashIDNotFound, self.fsrts.remove,
                          self.CRASH_ID_2)

    def test_new_crashes(self):
        self.fsrts._current_slot = lambda: ['00', '00_00']
        self._make_test_crash()
        self.fsrts._current_slot = lambda: ['00', '00_01']
        self.assertEqual(list(self.fsrts.new_crashes()), [self.CRASH_ID_1])
        self.assertEqual(list(self.fsrts.new_crashes()), [])
        self.fsrts.remove(self.CRASH_ID_1)
        del self.fsrts._current_slot

        self.fsrts._current_slot = lambda: ['00', '00_00']
        self._make_test_crash()

        date_path = self.fsrts._get_dated_parent_directory(self.CRASH_ID_1,
                                                           ['00', '00_00'])

        new_date_path = self.fsrts._get_dated_parent_directory(self.CRASH_ID_1,
                                                               ['00', '00_01'])

        webhead_path = os.sep.join([new_date_path, 'webhead_0'])

        os.mkdir(new_date_path)
        os.rename(date_path, webhead_path)

        os.unlink(os.sep.join([webhead_path, self.CRASH_ID_1]))
        os.symlink('../../../../name/' + os.sep.join(self.fsrts._get_radix(
                       self.CRASH_ID_1)),
                   os.sep.join([webhead_path, self.CRASH_ID_1]))

        self.fsrts._current_slot = lambda: ['00', '00_02']
        self.assertEqual(list(self.fsrts.new_crashes()),
                         [self.CRASH_ID_1])

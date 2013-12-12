import unittest
import os
import shutil
from mock import Mock
from configman import ConfigurationManager

from socorro.external.fs.crashstorage import FSRadixTreeStorage
from socorro.external.crashstorage_base import CrashIDNotFound


class TestFSRadixTreeStorage(unittest.TestCase):
    CRASH_ID_1 = "0bba929f-8721-460c-dead-a43c20071025"
    CRASH_ID_2 = "0bba929f-8721-460c-dead-a43c20071026"
    CRASH_ID_3 = "0bba929f-8721-460c-dead-a43c20071027"

    def setUp(self):
        with self._common_config_setup().context() as config:
            self.fsrts = FSRadixTreeStorage(config)

    def tearDown(self):
        shutil.rmtree(self.fsrts.config.fs_root)

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = FSRadixTreeStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging
          }],
          argv_source=[]
        )
        return config_manager

    def _make_test_crash(self, crash_id=CRASH_ID_1):
        self.fsrts.save_raw_crash({
            "test": "TEST"
        }, {
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }, crash_id)

    def _make_processed_test_crash(self):
        self.fsrts.save_processed({
            "uuid": self.CRASH_ID_2,
            "test": "TEST",
            "email": "should not exist"
        })

    def test_save_raw_crash(self):
        self._make_test_crash()
        self.assertTrue(os.path.exists(
            self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1)))

    def test_save_processed(self):
        self._make_processed_test_crash()
        self.assertTrue(os.path.exists(
            os.path.join(
                self.fsrts._get_radixed_parent_directory(self.CRASH_ID_2),
                self.CRASH_ID_2 + self.fsrts.config.jsonz_file_suffix)))

    def test_get_raw_crash(self):
        self._make_test_crash()
        self.assertEqual(self.fsrts.get_raw_crash(self.CRASH_ID_1)['test'],
                         "TEST")
        self.assertRaises(CrashIDNotFound, self.fsrts.get_raw_crash,
                          self.CRASH_ID_2)

    def test_get_unredacted_processed_crash(self):
        self._make_processed_test_crash()
        self.assertEqual(self.fsrts.get_unredacted_processed(self.CRASH_ID_2)['test'],
                         "TEST")
        self.assertTrue('email' in
                        self.fsrts.get_unredacted_processed(self.CRASH_ID_2))
        self.assertRaises(CrashIDNotFound, self.fsrts.get_unredacted_processed,
                          self.CRASH_ID_1)

    def test_get_processed_crash(self):
        self._make_processed_test_crash()
        self.assertEqual(self.fsrts.get_processed(self.CRASH_ID_2)['test'],
                         "TEST")
        self.assertTrue('email' not in
                        self.fsrts.get_processed(self.CRASH_ID_2))
        self.assertRaises(CrashIDNotFound, self.fsrts.get_unredacted_processed,
                          self.CRASH_ID_1)

    def test_get_raw_dump(self):
        self._make_test_crash()
        self.assertEqual(self.fsrts.get_raw_dump(self.CRASH_ID_1, 'foo'),
                        "bar")
        self.assertEqual(self.fsrts.get_raw_dump(self.CRASH_ID_1,
                                                 self.fsrts.config.dump_field),
                         "baz")
        self.assertRaises(CrashIDNotFound, self.fsrts.get_raw_dump,
                          self.CRASH_ID_2, "foo")
        self.assertRaises(IOError, self.fsrts.get_raw_dump,
                          self.CRASH_ID_1, "foor")

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
        self._make_test_crash(self.CRASH_ID_3)
        self.fsrts.remove(self.CRASH_ID_1)
        self.fsrts.remove(self.CRASH_ID_3)
        self.assertTrue(not os.path.exists(
            self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1)))
        self.assertRaises(CrashIDNotFound, self.fsrts.remove,
                          self.CRASH_ID_2)

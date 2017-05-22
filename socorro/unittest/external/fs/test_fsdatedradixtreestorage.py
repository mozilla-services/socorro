import os
import shutil
from mock import Mock
from configman import ConfigurationManager
from nose.tools import eq_, ok_, assert_raises

from socorro.external.fs.crashstorage import FSDatedRadixTreeStorage
from socorro.external.crashstorage_base import (
    CrashIDNotFound,
    MemoryDumpsMapping,
)
from socorro.unittest.testbase import TestCase


class TestFSDatedRadixTreeStorage(TestCase):
    CRASH_ID_1 = "0bba929f-8721-460c-dead-a43c20071025"
    CRASH_ID_2 = "0bba929f-8721-460c-dead-a43c20071026"

    def setUp(self):
        super(TestFSDatedRadixTreeStorage, self).setUp()
        with self._common_config_setup().context() as config:
            self.fsrts = FSDatedRadixTreeStorage(config)

    def tearDown(self):
        super(TestFSDatedRadixTreeStorage, self).tearDown()
        shutil.rmtree(self.fsrts.config.fs_root)

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = FSDatedRadixTreeStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'minute_slice_interval': 1,
            'fs_root': os.environ.get('resource.fs.fs_root', './crashes'),
          }],
          argv_source=[]
        )
        return config_manager

    def _make_test_crash(self):
        self.fsrts.save_raw_crash(
            {  # raw crash
                "test": "TEST"
            },
            MemoryDumpsMapping({  # dumps
                'foo': 'bar',
                self.fsrts.config.dump_field: 'baz'
            }),
            self.CRASH_ID_1
        )

    def test_save_raw_crash(self):
        try:
            self._make_test_crash()
            ok_(os.path.islink(
                os.path.join(
                  self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                  self.fsrts._get_date_root_name(self.CRASH_ID_1))))
            ok_(os.path.exists(
                os.path.join(
                  self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                  self.fsrts._get_date_root_name(self.CRASH_ID_1),
                  self.CRASH_ID_1)))
            ok_(
                os.path.exists(
                    "%s/%s.json" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
            ok_(
                os.path.exists(
                    "%s/%s.dump" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
            ok_(
                os.path.exists(
                    "%s/%s.foo.dump" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
        finally:
            self.fsrts.remove(self.CRASH_ID_1)

    def test_save_raw_crash_no_dumps(self):
        try:
            self.fsrts.save_raw_crash(
                {  # raw crash
                    "test": "TEST"
                },
                None,  # dumps
                self.CRASH_ID_1
            )
            ok_(os.path.islink(
                os.path.join(
                  self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                  self.fsrts._get_date_root_name(self.CRASH_ID_1))))
            ok_(os.path.exists(
                os.path.join(
                  self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                  self.fsrts._get_date_root_name(self.CRASH_ID_1),
                  self.CRASH_ID_1)))
            ok_(
                os.path.exists(
                    "%s/%s.json" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
            ok_(not
                os.path.exists(
                    "%s/%s.dump" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
            ok_(not
                os.path.exists(
                    "%s/%s.foo.dump" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
        finally:
            self.fsrts.remove(self.CRASH_ID_1)

    def test_save_raw_and_processed_crash_no_dumps(self):
        try:
            self.fsrts.save_raw_and_processed(
                {  # raw crash
                    "test": "TEST"
                },
                None,  # dumps
                {  # processed_crash
                    'processed': 'crash',
                    'uuid': self.CRASH_ID_1,
                },
                self.CRASH_ID_1
            )
            ok_(os.path.islink(
                os.path.join(
                  self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                  self.fsrts._get_date_root_name(self.CRASH_ID_1))))
            ok_(os.path.exists(
                os.path.join(
                  self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                  self.fsrts._get_date_root_name(self.CRASH_ID_1),
                  self.CRASH_ID_1)))
            ok_(
                os.path.exists(
                    "%s/%s.json" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
            ok_(not
                os.path.exists(
                    "%s/%s.dump" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
            ok_(not
                os.path.exists(
                    "%s/%s.foo.dump" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
            ok_(
                os.path.exists(
                    "%s/%s.jsonz" % (
                        self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
                        self.CRASH_ID_1
                    )
                )
            )
        finally:
            self.fsrts.remove(self.CRASH_ID_1)

    def test_get_raw_crash(self):
        self._make_test_crash()
        eq_(self.fsrts.get_raw_crash(self.CRASH_ID_1)['test'],
                         "TEST")
        assert_raises(CrashIDNotFound, self.fsrts.get_raw_crash,
                          self.CRASH_ID_2)

    def test_get_raw_dump(self):
        self._make_test_crash()
        eq_(self.fsrts.get_raw_dump(self.CRASH_ID_1, 'foo'),
                         "bar")
        eq_(self.fsrts.get_raw_dump(self.CRASH_ID_1,
                                                 self.fsrts.config.dump_field),
                         "baz")
        assert_raises(CrashIDNotFound, self.fsrts.get_raw_dump,
                          self.CRASH_ID_2, "foo")
        assert_raises(IOError, self.fsrts.get_raw_dump, self.CRASH_ID_1,
                          "foor")

    def test_get_raw_dumps(self):
        self._make_test_crash()
        eq_(self.fsrts.get_raw_dumps(self.CRASH_ID_1), {
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        })
        assert_raises(CrashIDNotFound, self.fsrts.get_raw_dumps,
                          self.CRASH_ID_2)

    def test_remove(self):
        self._make_test_crash()
        self.fsrts.remove(self.CRASH_ID_1)

        parent = os.path.realpath(
            os.path.join(
              self.fsrts._get_radixed_parent_directory(self.CRASH_ID_1),
              self.fsrts._get_date_root_name(self.CRASH_ID_1)))

        p = os.path.join(parent, self.CRASH_ID_1)
        ok_(not os.path.exists(p))

        p = os.path.dirname(p)
        ok_(not os.path.exists(p))

        p = os.path.dirname(p)
        ok_(not os.path.exists(p))

        assert_raises(CrashIDNotFound, self.fsrts.remove,
                          self.CRASH_ID_2)

    def test_new_crashes(self):
        self.fsrts._current_slot = lambda: ['00', '00_00']
        self._make_test_crash()
        self.fsrts._current_slot = lambda: ['00', '00_01']
        eq_(list(self.fsrts.new_crashes()), [self.CRASH_ID_1])
        eq_(list(self.fsrts.new_crashes()), [])
        self.fsrts.remove(self.CRASH_ID_1)
        del self.fsrts._current_slot

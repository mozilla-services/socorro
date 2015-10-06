import os
import shutil
from mock import Mock
from configman import ConfigurationManager
from nose.tools import eq_, ok_, assert_raises

from socorro.external.fs.crashstorage import (
    FSLegacyDatedRadixTreeStorage,
    FSTemporaryStorage
)
from socorro.external.crashstorage_base import (
    CrashIDNotFound,
    MemoryDumpsMapping,
)
from socorro.unittest.testbase import TestCase


class TestFSLegacyDatedRadixTreeStorage(TestCase):
    CRASH_ID_1 = "0bba929f-8721-460c-dead-a43c20071025"
    CRASH_ID_2 = "0bba929f-8721-460c-dead-a43c20071026"
    CRASH_ID_3 = "0bba929f-8721-460c-dddd-a43c20071025"

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
          }],
          argv_source=[]
        )
        return config_manager

    def _make_test_crash(self):
        self.fsrts.save_raw_crash({
            "test": "TEST"
        }, MemoryDumpsMapping({
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }), self.CRASH_ID_1)

    def _make_test_crash_3(self):
        self.fsrts.save_raw_crash({
            "test": "TEST"
        }, MemoryDumpsMapping({
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }), self.CRASH_ID_3)


    def test_save_raw_crash(self):
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
        eq_(self.fsrts.get_raw_dumps(self.CRASH_ID_1), MemoryDumpsMapping({
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }))
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
        eq_(list(self.fsrts.new_crashes()),
                         [self.CRASH_ID_1])

    def test_orphaned_symlink_clean_up(self):
        # Bug 971496 identified a problem where a second crash coming in with
        # the same crash id would derail saving the second crash and leave
        # an extra undeleted symbolic link in the file system.  This link
        # would be sited as undeleted on every run of 'new_crashes'.
        # this test shows that we can clean these extra symlinks if we
        # encounter them.
        self.fsrts._current_slot = lambda: ['00', '00_00']
        self._make_test_crash()
        self.fsrts._current_slot = lambda: ['00', '00_01']
        # make sure we can't create the duplicate in a different slot
        assert_raises(OSError, self._make_test_crash)
        # make sure the second slot exists so we can make the bogus symlink
        self._make_test_crash_3()
        # create bogus orphan link
        self.fsrts._create_name_to_date_symlink(
            self.CRASH_ID_1,
            self.fsrts._current_slot()
        )
        ok_(os.path.islink(
            './crashes/20071025/date/00/00_01/0bba929f-8721-460c-dead-'
            'a43c20071025'
        ))
        # run through the new_crashes iterator which will yield each of the
        # crashes that has been submitted since the last run of new_crashes.
        # this should cause all the symlinks to be removed.
        # we don't bother saving the crashes, as we don't need them.
        for x in self.fsrts.new_crashes():
            pass
        ok_(not os.path.exists(
            './crashes/20071025/date/00/00_01/0bba929f-8721-460c-dead-'
            'a43c20071025'
        ))

class MyFSTemporaryStorage(FSTemporaryStorage):
    def _get_current_date(self):
        return "25"

class TestFSTemporaryStorage(TestCase):
    CRASH_ID_1 = "0bba929f-8721-460c-dead-a43c20071025"
    CRASH_ID_2 = "0bba929f-8721-460c-dead-a43c20071026"
    CRASH_ID_3 = "0bba929f-8721-460c-dddd-a43c20071025"
    CRASH_ID_4 = "0bba929f-8721-460c-dddd-a43c20071125"

    def setUp(self):
        with self._common_config_setup().context() as config:
            self.fsrts = MyFSTemporaryStorage(config)

    def tearDown(self):
        shutil.rmtree(self.fsrts.config.fs_root)

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = MyFSTemporaryStorage.get_required_config()
        required_config.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{
            'logger': mock_logging,
            'minute_slice_interval': 1
          }],
          argv_source=[]
        )
        return config_manager

    def _make_test_crash(self):
        self.fsrts.save_raw_crash(
            {"test": "TEST"},
            MemoryDumpsMapping({
                'foo': 'bar',
                self.fsrts.config.dump_field: 'baz'
            }),
            self.CRASH_ID_1
        )

    def _make_test_crash_3(self):
        self.fsrts.save_raw_crash(
            {"test": "TEST"},
            MemoryDumpsMapping({
                'foo': 'bar',
                self.fsrts.config.dump_field: 'baz'
            }),
            self.CRASH_ID_3
        )

    def _make_test_crash_4(self):
        self.fsrts.save_raw_crash(
            {"test": "TEST"},
            MemoryDumpsMapping({
                'foo': 'bar',
                self.fsrts.config.dump_field: 'baz'
            }),
            self.CRASH_ID_4
        )

    def test_save_raw_crash(self):
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
        eq_(self.fsrts.get_raw_dumps(self.CRASH_ID_1), MemoryDumpsMapping({
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }))
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
        eq_(list(self.fsrts.new_crashes()),
                         [self.CRASH_ID_1])

    def test_orphaned_symlink_clean_up(self):
        # Bug 971496 identified a problem where a second crash coming in with
        # the same crash id would derail saving the second crash and leave
        # an extra undeleted symbolic link in the file system.  This link
        # would be sited as undeleted on every run of 'new_crashes'.
        # this test shows that we can clean these extra symlinks if we
        # encounter them.
        self.fsrts._current_slot = lambda: ['00', '00_00']
        self._make_test_crash()
        self.fsrts._current_slot = lambda: ['00', '00_01']
        # make sure we can't create the duplicate in a different slot
        assert_raises(OSError, self._make_test_crash)
        # make sure the second slot exists so we can make the bogus symlink
        self._make_test_crash_3()
        # create bogus orphan link
        self.fsrts._create_name_to_date_symlink(
            self.CRASH_ID_1,
            self.fsrts._current_slot()
        )
        ok_(os.path.islink(
            './crashes/25/date/00/00_01/0bba929f-8721-460c-dead-'
            'a43c20071025'
        ))
        ok_(os.path.islink(
            './crashes/25/date/00/00_01/0bba929f-8721-460c-dddd-'
            'a43c20071025'
        ))
        # make sure all slots in use are traversable
        self.fsrts._current_slot = lambda: ['00', '00_02']
        # run through the new_crashes iterator which will yield each of the
        # crashes that has been submitted since the last run of new_crashes.
        # this should cause all the symlinks to be removed.
        # we don't bother saving the crashes, as we don't need them.
        for x in self.fsrts.new_crashes():
            pass
        ok_(not os.path.exists(
            './crashes/25/date/00/00_01/0bba929f-8721-460c-dead-a43c20071025'
        ))

    def test_make_sure_days_recycle(self):
        self.fsrts._current_slot = lambda: ['00', '00_01']
        self._make_test_crash()
        self._make_test_crash_3()
        self._make_test_crash_4()
        ok_(os.path.exists(
            './crashes/25/date/00/00_01/0bba929f-8721-460c-dead-a43c20071025'
        ))
        ok_(os.path.exists(
            './crashes/25/date/00/00_01/0bba929f-8721-460c-dddd-a43c20071025'
        ))
        ok_(os.path.exists(
            './crashes/25/date/00/00_01/0bba929f-8721-460c-dddd-a43c20071125'
        ))
        for x in self.fsrts.new_crashes():
            pass

    def _secondary_config_setup(self):
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
          }],
          argv_source=[]
        )
        return config_manager

    def test_make_sure_old_style_date_directories_are_traversed(self):
        with self._secondary_config_setup().context() as config:
            self.fsrts_old = FSLegacyDatedRadixTreeStorage(config)
        self.fsrts_old._current_slot = lambda: ['00', '00_00']
        # save crash 1 in old system
        self.fsrts_old.save_raw_crash({
            "test": "TEST"
        }, MemoryDumpsMapping({
            'foo': 'bar',
            self.fsrts.config.dump_field: 'baz'
        }), self.CRASH_ID_1)
        ok_(os.path.exists(
            './crashes/20071025/date/00/00_00/0bba929f-8721-460c-dead-'
            'a43c20071025'
        ))

        self.fsrts._current_slot = lambda: ['00', '00_00']
        #save crash 3 in new system
        self._make_test_crash_3()

        ok_(os.path.exists(
            './crashes/25/date/00/00_00/0bba929f-8721-460c-dddd-a43c20071025'
        ))

        # consume crashes
        for x in self.fsrts.new_crashes():
            pass

        # should be consumed because it isn't in our working tree or slot
        ok_(not os.path.exists(
            './crashes/20071025/date/00/00_00/0bba929f-8721-460c-dead-'
            'a43c20071025'
        ))

        # should not be consumed, while in working tree, it is in active slot
        ok_(os.path.exists(
            './crashes/25/date/00/00_00/0bba929f-8721-460c-dddd-a43c20071025'
        ))

        # switch to next active slot
        self.fsrts._current_slot = lambda: ['00', '00_01']

        # consume crashes
        for x in self.fsrts.new_crashes():
            pass

        # should be consumed because it is in working tree and inactive slot
        ok_( not os.path.exists(
            './crashes/25/date/00/00_00/0bba929f-8721-460c-dddd-a43c20071025'
        ))

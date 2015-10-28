# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_, assert_raises
from mock import Mock

from configman.dotdict import DotDictWithAcquisition

from socorro.app.fts_worker_methods import (
    NullTransform,
    FTSWorkerMethodBase,
    RawCrashCopyWorkerMethod,
    RawCrashMoveWorkerMethod,
    ProcessedCrashCopyWorkerMethod,
    CopyAllWorkerMethod,
    ProcessorWorkerMethod,
    RejectJob
)
from socorro.lib.util import DotDict as SocorroDotDict
from socorro.external.crashstorage_base import NullCrashStorage
from socorro.unittest.testbase import TestCase

an_id = 'not a real id'
dump_name = 'dummy_dump_name'
a_raw_crash = {
    'crash_id': an_id,
}
a_raw_dump = 'a dump contents'
raw_dumps = {
    'dump': a_raw_dump,
    dump_name: 'more dump contents',
}
a_processed_crash = {
    'crash_id': an_id,
}

#==============================================================================
class TestFTSWorkerMethods(TestCase):

    #--------------------------------------------------------------------------
    def get_config(self):
        config = DotDictWithAcquisition()
        config.logger = Mock()
        config.redactor_class = Mock()
        return config

    #--------------------------------------------------------------------------
    def test_FTSWorkerMethodBase_all_None(self):
        config = self.get_config()
        fts_worker_method = FTSWorkerMethodBase(config)
        ok_(isinstance(fts_worker_method.fetch_store, NullCrashStorage))
        ok_(isinstance(fts_worker_method.save_store, NullCrashStorage))
        ok_(fts_worker_method.transformation_fn is NullTransform)
        ok_(fts_worker_method.quick_check is None)
        ok_(fts_worker_method.save_raw_crash({}, {}, an_id) is None)
        ok_(
            fts_worker_method.save_raw_crash_with_file_dumps({}, {}, an_id)
            is None
        )
        ok_(fts_worker_method.save_processed({}) is None)
        eq_(fts_worker_method.get_raw_crash(an_id), {})
        eq_(fts_worker_method.get_raw_dump(an_id, dump_name), '')
        eq_(fts_worker_method.get_raw_dumps(an_id), {})
        eq_(fts_worker_method.get_raw_dumps_as_files(an_id), {})
        eq_(fts_worker_method.get_unredacted_processed(an_id), {})
        eq_(fts_worker_method.get_processed(an_id), {})
        ok_(fts_worker_method.remove(an_id) is None)

        assert_raises(NotImplementedError, fts_worker_method, an_id)

    #--------------------------------------------------------------------------
    def test_FTSWorkerMethodBase_all_Mocked(self):
        config = self.get_config()
        fts_worker_method = FTSWorkerMethodBase(
            config,
            Mock(),
            Mock(),
            Mock(),
            Mock(),
        )

        ok_(fts_worker_method.save_raw_crash({}, {}, an_id) is None)
        fts_worker_method.save_store.save_raw_crash.called_once_with(
            {},
            {},
            an_id
        )

        ok_(
            fts_worker_method.save_raw_crash_with_file_dumps(
                {},
                {},
                an_id
            ) is None
        )
        fts_worker_method.save_store.save_raw_crash_with_file_dumps \
            .called_once_with({}, {}, an_id)

        ok_(fts_worker_method.save_processed({}) is None)
        fts_worker_method.save_store.save_processed.called_once_with({})

        fts_worker_method.get_raw_crash(an_id),
        fts_worker_method.fetch_store.save_processed.called_once_with(an_id)

        fts_worker_method.get_raw_dump(an_id, dump_name)
        fts_worker_method.fetch_store.get_raw_dump.called_once_with(
            an_id,
            dump_name
        )

        fts_worker_method.get_raw_dumps(an_id)
        fts_worker_method.fetch_store.get_raw_dumps.called_once_with(an_id)

        fts_worker_method.get_raw_dumps_as_files(an_id)
        fts_worker_method.fetch_store.get_raw_dumps_as_files.called_once_with(
            an_id,
        )

        fts_worker_method.get_unredacted_processed(an_id)
        fts_worker_method.fetch_store.get_unredacted_processed \
            .called_once_with(an_id)

        fts_worker_method.get_processed(an_id)
        fts_worker_method.fetch_store.get_processed.called_once_with(an_id)

        fts_worker_method.remove(an_id)
        fts_worker_method.fetch_store.remove.called_once_with(an_id)

    #--------------------------------------------------------------------------
    def test_RawCrashCopyWorkerMethod_all_Mocked(self):
        config = self.get_config()
        fts_worker_method = RawCrashCopyWorkerMethod(
            config,
            fetch_store=Mock(),
            save_store=Mock(),
            transform_fn=Mock(),
            quit_check=Mock(),
        )
        fts_worker_method.fetch_store.get_raw_crash.return_value = a_raw_crash
        fts_worker_method.fetch_store.get_raw_dumps.return_value = raw_dumps

        # the call to be tested
        fts_worker_method(an_id)

        # this is what should have happened:
        # first with the fetch_store
        fts_worker_method.fetch_store.get_raw_crash.called_once_with(an_id)
        fts_worker_method.fetch_store.get_raw_dumps.called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.save_raw_crash.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.save_raw_crash_with_file_dumps
                .call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.save_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.save_raw_and_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.fetch_store.get_raw_dumps_as_files.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.get_unredacted_processed.call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.get_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.remove.call_count, 0)

        # then with the transformation
        fts_worker_method.transformation_fn.called_once_with(
            raw_crash=a_raw_crash,
            raw_dumps=raw_dumps
        )

        # and then with the save_store
        fts_worker_method.save_store.save_raw_crash.called_once_with(
            a_raw_crash,
            raw_dumps
        )
        eq_(fts_worker_method.save_store.save_raw_crash_with_file_dumps.call_count, 0)
        eq_(fts_worker_method.save_store.save_processed.call_count, 0)
        eq_(fts_worker_method.save_store.save_raw_and_processed.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps_as_files.call_count, 0)
        eq_(fts_worker_method.save_store.get_unredacted_processed.call_count, 0)
        eq_(fts_worker_method.save_store.remove.call_count, 0)

    #--------------------------------------------------------------------------
    def test_RawCrashMoveWorkerMethod_all_Mocked(self):
        config = self.get_config()
        fts_worker_method = RawCrashCopyWorkerMethod(
            config,
            fetch_store=Mock(),
            save_store=Mock(),
            transform_fn=Mock(),
            quit_check=Mock(),
        )
        fts_worker_method.fetch_store.get_raw_crash.return_value = a_raw_crash
        fts_worker_method.fetch_store.get_raw_dumps.return_value = raw_dumps

        # the call to be tested
        fts_worker_method(an_id)

        # this is what should have happened:
        # first with the fetch_store
        fts_worker_method.fetch_store.get_raw_crash.called_once_with(an_id)
        fts_worker_method.fetch_store.get_raw_dumps.called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.save_raw_crash.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.save_raw_crash_with_file_dumps
                .call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.save_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.save_raw_and_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.fetch_store.get_raw_dumps_as_files.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.get_unredacted_processed.call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.get_processed.call_count, 0)
        fts_worker_method.fetch_store.remove.called_once_with(an_id)

        # then with the transformation
        fts_worker_method.transformation_fn.called_once_with(
            raw_crash=a_raw_crash,
            raw_dumps=raw_dumps
        )

        # and then with the save_store
        fts_worker_method.save_store.save_raw_crash.called_once_with(
            a_raw_crash,
            raw_dumps
        )
        fts_worker_method.save_store.remove.called_once_with(an_id)
        eq_(fts_worker_method.save_store.save_raw_crash_with_file_dumps.call_count, 0)
        eq_(fts_worker_method.save_store.save_processed.call_count, 0)
        eq_(fts_worker_method.save_store.save_raw_and_processed.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps_as_files.call_count, 0)
        eq_(fts_worker_method.save_store.get_unredacted_processed.call_count, 0)
        eq_(fts_worker_method.save_store.remove.call_count, 0)


    #--------------------------------------------------------------------------
    def test_ProcessedCrashCopyWorkerMethod_all_Mocked(self):
        config = self.get_config()
        fts_worker_method = ProcessedCrashCopyWorkerMethod(
            config,
            fetch_store=Mock(),
            save_store=Mock(),
            transform_fn=Mock(),
            quit_check=Mock(),
        )
        fts_worker_method.fetch_store.get_unredacted_processed.return_value = \
            a_processed_crash

        # the call to be tested
        fts_worker_method(an_id)

        # this is what should have happened:
        # first with the fetch_store
        eq_(fts_worker_method.fetch_store.save_raw_crash.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.save_raw_crash_with_file_dumps
                .call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.save_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.save_raw_and_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.get_raw_crash.call_count, 0)
        eq_(fts_worker_method.fetch_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.fetch_store.get_raw_dumps_as_files.call_count, 0)
        fts_worker_method.fetch_store.get_unredacted_processed \
            .called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.get_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.remove.call_count, 0)

        # then with the transformation
        fts_worker_method.transformation_fn.called_once_with(
            processed_crash=a_processed_crash,
        )

        # and then with the save_store
        eq_(fts_worker_method.save_store.save_raw_crash.call_count, 0)
        eq_(
            fts_worker_method.save_store.save_raw_crash_with_file_dumps
                .call_count,
            0
        )
        fts_worker_method.save_store.save_processed.called_once_with(
            a_processed_crash
        )
        eq_(fts_worker_method.save_store.save_raw_and_processed.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps_as_files.call_count, 0)
        eq_(fts_worker_method.save_store.get_unredacted_processed.call_count, 0)
        eq_(fts_worker_method.save_store.get_processed.call_count, 0)
        eq_(fts_worker_method.save_store.remove.call_count, 0)


    #--------------------------------------------------------------------------
    def test_CopyAllWorkerMethod_all_Mocked(self):
        config = self.get_config()
        fts_worker_method = ProcessedCrashCopyWorkerMethod(
            config,
            fetch_store=Mock(),
            save_store=Mock(),
            transform_fn=Mock(),
            quit_check=Mock(),
        )
        fts_worker_method.fetch_store.get_raw_crash.return_value = a_raw_crash
        fts_worker_method.fetch_store.get_raw_dumps.return_value = raw_dumps
        fts_worker_method.fetch_store.get_unredacted_processed.return_value = \
            a_processed_crash

        # the call to be tested
        fts_worker_method(an_id)

        # this is what should have happened:
        # first with the fetch_store
        eq_(fts_worker_method.fetch_store.save_raw_crash.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.save_raw_crash_with_file_dumps
                .call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.save_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.save_raw_and_processed.call_count, 0)
        fts_worker_method.fetch_store.get_raw_crash.called_once_with(an_id)
        fts_worker_method.fetch_store.get_raw_dumps.called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.get_raw_dumps_as_files.call_count, 0)
        fts_worker_method.fetch_store.get_unredacted_processed \
            .called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.get_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.remove.call_count, 0)

        # then with the transformation
        fts_worker_method.transformation_fn.called_once_with(
            raw_crash=a_raw_crash,
            raw_dumps=raw_dumps,
            processed_crash=a_processed_crash,
        )

        # and then with the save_store
        eq_(fts_worker_method.save_store.save_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.save_raw_crash_with_file_dumps.call_count, 0)
        fts_worker_method.save_store.save_processed.called_once_with(
            a_processed_crash
        )
        fts_worker_method.save_store.save_raw_and_processed.called_once_with(
            a_raw_crash,
            raw_dumps,
            a_processed_crash,
            an_id
        )
        eq_(fts_worker_method.save_store.get_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps_as_files.call_count, 0)
        eq_(fts_worker_method.save_store.get_unredacted_processed.call_count, 0)
        eq_(fts_worker_method.save_store.get_processed.call_count, 0)
        eq_(fts_worker_method.save_store.remove.call_count, 0)

    #--------------------------------------------------------------------------
    def test_ProcessorWorkerMethod_all_Mocked(self):
        config = self.get_config()
        fts_worker_method = ProcessedCrashCopyWorkerMethod(
            config,
            fetch_store=Mock(),
            save_store=Mock(),
            transform_fn=Mock(),
            quit_check=Mock(),
        )
        fts_worker_method.fetch_store.get_raw_crash.return_value = a_raw_crash
        fts_worker_method.fetch_store.get_raw_dumps.return_value = raw_dumps
        fts_worker_method.fetch_store.get_unredacted_processed.return_value = \
            a_processed_crash

        # the call to be tested
        fts_worker_method(an_id)

        # this is what should have happened:
        # first with the fetch_store
        eq_(fts_worker_method.fetch_store.save_raw_crash.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.save_raw_crash_with_file_dumps
                .call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.save_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.save_raw_and_processed.call_count, 0)
        fts_worker_method.fetch_store.get_raw_crash.called_once_with(an_id)
        fts_worker_method.fetch_store.get_raw_dumps.called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.get_raw_dumps_as_files.call_count, 0)
        fts_worker_method.fetch_store.get_unredacted_processed \
            .called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.get_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.remove.call_count, 0)

        # then with the transformation
        fts_worker_method.transformation_fn.called_once_with(
            raw_crash=a_raw_crash,
            raw_dumps=raw_dumps,
            processed_crash=a_processed_crash,
        )

        # and then with the save_store
        eq_(fts_worker_method.save_store.save_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.save_raw_crash_with_file_dumps.call_count, 0)
        fts_worker_method.save_store.save_processed.called_once_with(
            a_processed_crash
        )
        fts_worker_method.save_store.save_raw_and_processed.called_once_with(
            a_raw_crash,
            None,
            a_processed_crash,
            an_id
        )
        eq_(fts_worker_method.save_store.get_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps_as_files.call_count, 0)
        eq_(fts_worker_method.save_store.get_unredacted_processed.call_count, 0)
        eq_(fts_worker_method.save_store.get_processed.call_count, 0)
        eq_(fts_worker_method.save_store.remove.call_count, 0)


    #--------------------------------------------------------------------------
    def test_ProcessorWorkerMethod_no_preexisting_processed_all_Mocked(self):
        config = self.get_config()
        fts_worker_method = ProcessedCrashCopyWorkerMethod(
            config,
            fetch_store=Mock(),
            save_store=Mock(),
            transform_fn=Mock(),
            quit_check=Mock(),
        )
        fts_worker_method.fetch_store.get_raw_crash.return_value = a_raw_crash
        fts_worker_method.fetch_store.get_raw_dumps.return_value = raw_dumps
        fts_worker_method.fetch_store.get_unredacted_processed.side_effect = \
            RejectJob('nope')

        # the call to be tested
        fts_worker_method(an_id)

        # this is what should have happened:
        # first with the fetch_store
        eq_(fts_worker_method.fetch_store.save_raw_crash.call_count, 0)
        eq_(
            fts_worker_method.fetch_store.save_raw_crash_with_file_dumps
                .call_count,
            0
        )
        eq_(fts_worker_method.fetch_store.save_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.save_raw_and_processed.call_count, 0)
        fts_worker_method.fetch_store.get_raw_crash.called_once_with(an_id)
        fts_worker_method.fetch_store.get_raw_dumps.called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.get_raw_dumps_as_files.call_count, 0)
        fts_worker_method.fetch_store.get_unredacted_processed \
            .called_once_with(an_id)
        eq_(fts_worker_method.fetch_store.get_processed.call_count, 0)
        eq_(fts_worker_method.fetch_store.remove.call_count, 0)

        # then with the transformation
        fts_worker_method.transformation_fn.called_once_with(
            raw_crash=a_raw_crash,
            raw_dumps=raw_dumps,
            processed_crash=SocorroDotDict(),
        )

        # and then with the save_store
        eq_(fts_worker_method.save_store.save_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.save_raw_crash_with_file_dumps.call_count, 0)
        fts_worker_method.save_store.save_processed.called_once_with(
            a_processed_crash
        )
        fts_worker_method.save_store.save_raw_and_processed.called_once_with(
            a_raw_crash,
            None,
            a_processed_crash,
            an_id
        )
        eq_(fts_worker_method.save_store.get_raw_crash.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dump.call_count, 0)
        eq_(fts_worker_method.save_store.get_raw_dumps_as_files.call_count, 0)
        eq_(fts_worker_method.save_store.get_unredacted_processed.call_count, 0)
        eq_(fts_worker_method.save_store.get_processed.call_count, 0)
        eq_(fts_worker_method.save_store.remove.call_count, 0)



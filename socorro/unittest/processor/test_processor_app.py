# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
from nose.tools import eq_

from configman.dotdict import DotDict, DotDictWithAcquisition

from socorro.processor.processor_app import ProcessorApp
from socorro.app.fts_worker_methods import ProcessorWorkerMethod
from socorro.external.crashstorage_base import (
    CrashIDNotFound,
    FileDumpsMapping
)
from socorro.unittest.testbase import TestCase


def sequencer(*args):
    def foo(*fargs, **fkwargs):
        for x in args:
            yield x
    return foo


class TestProcessorApp(TestCase):

    def get_standard_config(self):
        config = DotDictWithAcquisition()

        config.source = DotDictWithAcquisition()
        mocked_source_crashstorage = mock.Mock()
        mocked_source_crashstorage.id = 'mocked_source_crashstorage'
        config.source.crashstorage_class = mock.Mock(
          return_value=mocked_source_crashstorage
        )

        config.destination = DotDictWithAcquisition()
        mocked_destination_crashstorage = mock.Mock()
        mocked_destination_crashstorage.id = 'mocked_destination_crashstorage'
        config.destination.crashstorage_class = mock.Mock(
          return_value=mocked_destination_crashstorage
        )

        config.processor = DotDictWithAcquisition()
        mocked_processor = mock.Mock()
        mocked_processor.id = 'mocked_processor'
        config.processor.processor_class = mock.Mock(
          return_value=mocked_processor
        )

        config.number_of_submissions = 'forever'
        config.dry_run = False
        config.new_crash_source = DotDictWithAcquisition()
        class FakedNewCrashSource(object):
            def __init__(self, *args, **kwargs):
                pass
            def new_crashes(self):
                return sequencer(((1,), {}),
                                 2,  # ensure both forms acceptable
                                 None,
                                 ((3,), {}))()
        config.new_crash_source.new_crash_source_class = FakedNewCrashSource

        config.worker_task =  DotDictWithAcquisition()
        config.worker_task.worker_task_impl = ProcessorWorkerMethod

        config.companion_process = DotDictWithAcquisition()
        mocked_companion_process = mock.Mock()
        config.companion_process.companion_class = mock.Mock(
          return_value=mocked_companion_process
        )

        config.logger = mock.MagicMock()
        config.redactor_class = mock.MagicMock()

        return config

    def test_setup(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()

    def test_source_iterator(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        g = pa.source_iterator()
        eq_(g.next(), ((1,), {}))
        eq_(g.next(), ((2,), {}))
        eq_(g.next(), None)
        eq_(g.next(), ((3,), {}))

    def test_transform_success(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()

        fake_raw_crash = DotDict()
        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)
        pa.source.get_raw_crash = mocked_get_raw_crash

        fake_dump = FileDumpsMapping({'upload_file_minidump': 'fake_dump_TEMPORARY.dump'})
        mocked_get_raw_dumps_as_files = mock.Mock(return_value=fake_dump)
        pa.source.get_raw_dumps_as_files = mocked_get_raw_dumps_as_files

        fake_processed_crash = DotDict()
        mocked_get_unredacted_processed = mock.Mock(return_value=fake_processed_crash)
        pa.source.get_unredacted_processed = mocked_get_unredacted_processed

        mocked_process_crash = mock.Mock(return_value=7)
        pa._worker_method.transformation_fn = mocked_process_crash
        pa.destination.save_processed = mock.Mock()
        finished_func = mock.Mock()
        with mock.patch('socorro.external.crashstorage_base.os.unlink') as mocked_unlink:
            # the call being tested
            pa.worker_method(17, finished_func)
        # test results
        mocked_unlink.assert_called_with('fake_dump_TEMPORARY.dump')
        pa.source.get_raw_crash.assert_called_with(17)
        mocked_process_crash.assert_called_with(
          raw_crash=fake_raw_crash,
          raw_dumps=fake_dump,
          processed_crash=fake_processed_crash
        )
        pa.destination.save_raw_and_processed.assert_called_with(fake_raw_crash, None, 7, 17)
        eq_(finished_func.call_count, 1)

    def test_transform_crash_id_missing(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=CrashIDNotFound(17))
        pa.source.get_raw_crash = mocked_get_raw_crash
        pa.source.get_raw_dumps = mock.Mock()

        finished_func = mock.Mock()
        pa.worker_method(17, finished_func)
        pa.source.get_raw_crash.assert_called_with(17)
        eq_(pa.source.get_raw_dumps.call_count, 0)
        eq_(finished_func.call_count, 1)

    def test_transform_unexpected_exception(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=Exception('bummer'))
        pa.source.get_raw_crash = mocked_get_raw_crash

        finished_func = mock.Mock()

        self.assertRaises(Exception, pa.worker_method, 17, finished_func)
        eq_(finished_func.call_count, 1)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import time
import json

from nose.tools import eq_, ok_, assert_raises

from socorro.collector.submitter_app import (
    SubmitterApp,
    SubmitterFileSystemWalkerSource,
    DBSamplingCrashSource
)
from socorro.app.fts_worker_methods import ProcessorWorkerMethod
from configman.dotdict import DotDict, DotDictWithAcquisition
from socorro.app.fts_worker_methods import RawCrashCopyWorkerMethod
from socorro.external.postgresql import dbapi2_util
from socorro.external.crashstorage_base import Redactor
from socorro.unittest.testbase import TestCase


#------------------------------------------------------------------------------
def sequencer(*args):
    list_of_args =  list(args)
    def foo(*fargs, **fkwargs):
        try:
            return list_of_args.pop()
        except IndexError:
            return None
    return foo


#------------------------------------------------------------------------------
def generator_for_sequence(*args):
    list_of_args =  list(args)
    def foo(*fargs, **fkwargs):
        try:
            yield list_of_args.pop()
        except IndexError:
            return
    return foo


#==============================================================================
class TestSubmitterFileSystemWalkerSource(TestCase):

    #--------------------------------------------------------------------------
    def get_standard_config(self):
        config = DotDictWithAcquisition()
        config.search_root = None
        config.dump_suffix = '.dump'
        config.dump_field = "upload_file_minidump"
        config.redactor_class = Redactor
        config.forbidden_keys = Redactor.required_config.forbidden_keys.default

        config.logger = mock.MagicMock()

        return config

    #--------------------------------------------------------------------------
    def test_setup(self):
        config = self.get_standard_config()
        sub_walker = SubmitterFileSystemWalkerSource(config)
        eq_(sub_walker.config, config)
        eq_(sub_walker.config.logger, config.logger)

    #--------------------------------------------------------------------------
    def test_get_raw_crash(self):
        config = self.get_standard_config()
        sub_walker = SubmitterFileSystemWalkerSource(config)

        raw = ('{"name":"Gabi", ''"submitted_timestamp":"%d"}' % time.time())
        fake_raw_crash = DotDict(json.loads(raw))
        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)
        sub_walker.get_raw_crash = mocked_get_raw_crash

        path_tuple = ['6611a662-e70f-4ba5-a397-69a3a2121129.dump',
                      '6611a662-e70f-4ba5-a397-69a3a2121129.flash1.dump',
                      '6611a662-e70f-4ba5-a397-69a3a2121129.flash2.dump',
                      ]

        raw_crash = sub_walker.get_raw_crash(path_tuple)
        ok_(isinstance(raw_crash, DotDict))
        eq_(raw_crash['name'], 'Gabi')

    #--------------------------------------------------------------------------
    def test_get_raw_dumps_as_files(self):
        config = self.get_standard_config()
        sub_walker = SubmitterFileSystemWalkerSource(config)

        dump_pathnames = (
            '6611a662-e70f-4ba5-a397-69a3a2121129',
            (
                'raw_crash_file',
                '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.dump',
                '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash1.dump',
                '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash2.dump',
            ),
        )
        raw_dumps_files = sub_walker.get_raw_dumps_as_files(dump_pathnames)

        dump_names = {'upload_file_minidump':
             '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.dump',
             'flash1':
             '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash1.dump',
             'flash2':
             '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash2.dump'
             }

        ok_(isinstance(raw_dumps_files, dict))
        eq_(raw_dumps_files, dump_names)

    #--------------------------------------------------------------------------
    def test_new_crashes(self):
        sequence =  [
            (
                './',
                '6611a662-e70f-4ba5-a397-69a3a2121129.json',
                './6611a662-e70f-4ba5-a397-69a3a2121129.json',
            ),
            (
                './',
                '6611a662-e70f-4ba5-a397-69a3a2121129.upload.dump',
                './6611a662-e70f-4ba5-a397-69a3a2121129.upload.dump',
            ),
            (
                './',
                '7611a662-e70f-4ba5-a397-69a3a2121129.json',
                './7611a662-e70f-4ba5-a397-69a3a2121129.json',
            ),
            (
                './',
                '7611a662-e70f-4ba5-a397-69a3a2121129.other.dump',
                './7611a662-e70f-4ba5-a397-69a3a2121129.other.dump',
            ),
            (
                './',
                '7611a662-e70f-4ba5-a397-69a3a2121129.other.txt',
                './7611a662-e70f-4ba5-a397-69a3a2121129.other.txt',
            ),
            (
                './',
                '8611a662-e70f-4ba5-a397-69a3a2121129.json',
                './8611a662-e70f-4ba5-a397-69a3a2121129.json',
            )
        ]

        def findFileGenerator_mock_method(root, method):
            for x in sequence:
                if method(x):
                    yield x

        def listdir_mock_method(a_path):
            for x in sequence:
                yield x[1]

        config = self.get_standard_config()

        expected = [
            (
                ((
                    '6611a662-e70f-4ba5-a397-69a3a2121129',
                    [
                        './6611a662-e70f-4ba5-a397-69a3a2121129.json',
                        './6611a662-e70f-4ba5-a397-69a3a2121129.upload.dump'
                    ],
                ), ),
                {}
            ),
            (
                ((
                    '7611a662-e70f-4ba5-a397-69a3a2121129',
                    [
                        './7611a662-e70f-4ba5-a397-69a3a2121129.json',
                        './7611a662-e70f-4ba5-a397-69a3a2121129.other.dump'
                    ],
                ), ),
                {}
            ),
            (
                ((
                    '8611a662-e70f-4ba5-a397-69a3a2121129',
                    [
                        './8611a662-e70f-4ba5-a397-69a3a2121129.json'
                    ]
                ), ),
                {}
            ),
        ]

        find_patch_path = 'socorro.collector.submitter_app.findFileGenerator'
        with mock.patch(
            find_patch_path,
            new_callable=lambda: findFileGenerator_mock_method
        ):
            listdir_patch_path = 'socorro.collector.submitter_app.listdir'
            with mock.patch(
                listdir_patch_path,
                new_callable=lambda: listdir_mock_method
            ):

                sub_walker = SubmitterFileSystemWalkerSource(config)
                result = [x for x in sub_walker.new_crashes()]
                eq_(result, expected)


#==============================================================================
class TestDBSamplingCrashSource(TestCase):

    #--------------------------------------------------------------------------
    def get_standard_config(self):
        config = DotDictWithAcquisition()

        mocked_source_implementation = mock.Mock()
        mocked_source_implementation.quit_check_callback = None
        config.source_implementation = mock.Mock(
            return_value=mocked_source_implementation
        )

        config.sql = 'select uuid from jobs order by \
                      queueddatetime DESC limit 1000'

        config.logger = mock.MagicMock()
        return config

    #--------------------------------------------------------------------------
    def test_setup(self):
        config = self.get_standard_config()
        db_sampling = DBSamplingCrashSource(config)
        eq_(db_sampling.config, config)
        eq_(db_sampling.config.logger, config.logger)

    #--------------------------------------------------------------------------
    def test_new_crashes(self):
        config = self.get_standard_config()
        db_sampling = DBSamplingCrashSource(config)

        m_execute = mock.MagicMock()
        sequence =  [
            '114559a5-d8e6-428c-8b88-1c1f22120314',
            'c44245f4-c93b-49b8-86a2-c15dc3a695cb'
        ]
        expected = sequencer(*tuple(sequence))

        conn = mock.MagicMock()
        conn.cursor.return_value.__enter__().fetchone =  expected

        for a_row in dbapi2_util.execute_query_iter(conn, config.sql):
            eq_(a_row, sequence.pop())

        conn.cursor.assert_called_once_with()
        conn.cursor.return_value.__enter__.return_value.execute \
            .assert_called_once_with(
                config.sql,
                None
            )

    #--------------------------------------------------------------------------
    def test_get_raw_crash(self):
        config = self.get_standard_config()
        db_sampling = DBSamplingCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        raw = ('{"name":"Gabi", ''"submitted_timestamp":"%d"}' % time.time())
        fake_raw_crash = DotDict(json.loads(raw))

        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)

        db_sampling._implementation = mock.Mock()
        db_sampling._implementation.get_raw_crash = mocked_get_raw_crash

        raw_crash = db_sampling._implementation.get_raw_crash(crash_id)
        ok_(isinstance(raw_crash, DotDict))
        eq_(raw_crash['name'], 'Gabi')
        db_sampling._implementation.get_raw_crash.assert_called_with(crash_id)

    #--------------------------------------------------------------------------
    def test_get_raw_dumps_as_files(self):
        config = self.get_standard_config()
        db_sampling = DBSamplingCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        fake_dumps_as_files = {'upload_file_minidump':
                               '86b58ff2-9708-487d-bfc4-9dac32121214.' \
                               'upload_file_minidump.TEMPORARY.dump'
                              }
        mocked_as_files = mock.Mock(return_value=fake_dumps_as_files)

        db_sampling._implementation = mock.Mock()
        db_sampling._implementation.get_raw_dumps_as_files = mocked_as_files

        raw_dumps_as_files = \
            db_sampling._implementation.get_raw_dumps_as_files(crash_id)
        ok_(isinstance(raw_dumps_as_files, dict))
        eq_(raw_dumps_as_files['upload_file_minidump'],
                         '86b58ff2-9708-487d-bfc4-9dac32121214.' \
                         'upload_file_minidump.TEMPORARY.dump'
                        )
        db_sampling._implementation.get_raw_dumps_as_files \
            .assert_called_with(crash_id)


#==============================================================================
class TestSubmitterApp(TestCase):

    #--------------------------------------------------------------------------
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

        config.producer_consumer = DotDictWithAcquisition()
        mocked_producer_consumer = mock.Mock()
        mocked_producer_consumer.id = 'mocked_producer_consumer'
        config.producer_consumer.producer_consumer_class = mock.Mock(
            return_value=mocked_producer_consumer
        )
        config.producer_consumer.number_of_threads = float(1)

        config.new_crash_source = DotDictWithAcquisition()
        config.new_crash_source.new_crash_source_class = None

        config.submitter = DotDictWithAcquisition()
        config.submitter.delay = 0
        config.dry_run = False
        config.number_of_submissions = "all"

        config.logger = mock.MagicMock()
        config.redactor_class = mock.MagicMock()

        config.worker_task = DotDictWithAcquisition(
            {"worker_task_impl": RawCrashCopyWorkerMethod,},
        )

        return config

    #--------------------------------------------------------------------------
    def get_new_crash_source_config(self):
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

        config.producer_consumer = DotDictWithAcquisition()
        mocked_producer_consumer = mock.Mock()
        mocked_producer_consumer.id = 'mocked_producer_consumer'
        config.producer_consumer.producer_consumer_class = mock.Mock(
            return_value=mocked_producer_consumer
        )
        config.producer_consumer.number_of_threads = float(1)

        config.new_crash_source = DotDictWithAcquisition()
        mocked_new_crash_source =  mock.Mock()
        mocked_new_crash_source.id = 'mocked_new_crash_source'
        config.new_crash_source.new_crash_source_class = mock.Mock(
            return_value=mocked_new_crash_source
        )

        config.submitter = DotDictWithAcquisition()
        config.submitter.delay = 0
        config.dry_run = False
        config.number_of_submissions = "all"

        config.worker_task = DotDictWithAcquisition()
        config.worker_task.worker_task_impl = ProcessorWorkerMethod

        config.logger = mock.MagicMock()
        config.redactor_class = mock.MagicMock()

        return config


    #--------------------------------------------------------------------------
    def test_setup(self):
        config = self.get_standard_config()
        sub = SubmitterApp(config)
        eq_(sub.config, config)
        eq_(sub.config.logger, config.logger)

    #--------------------------------------------------------------------------
    def test_transform(self):
        config = self.get_standard_config()
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'

        fake_raw_crash = DotDict()
        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)
        sub.source.get_raw_crash = mocked_get_raw_crash

        fake_dump = {'upload_file_minidump': 'fake dump'}
        mocked_get_raw_dumps = mock.Mock(return_value=fake_dump)
        sub.source.get_raw_dumps = mocked_get_raw_dumps

        sub.destination.save_raw_crash = mock.Mock()

        sub.worker_method(crash_id)
        sub.source.get_raw_crash.assert_called_with(crash_id)
        sub.source.get_raw_dumps.assert_called_with(crash_id)
        sub.destination.save_raw_crash.assert_called_with(
            fake_raw_crash,
            fake_dump,
            crash_id
        )

    #--------------------------------------------------------------------------
    def test_source_iterator(self):

        # Test with number of submissions equal to all
        # It raises StopIterations after all the elements were called
        config = self.get_standard_config()
        config.number_of_submissions = "all"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()

        sub.source.new_crashes = lambda: iter([1, 2, 3])
        itera = sub.source_iterator()

        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))
        assert_raises(StopIteration, itera.next)

        # Test with number of submissions equal to forever
        # It never raises StopIterations
        config = self.get_standard_config()
        config.number_of_submissions = "forever"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sub.source.new_crashes = lambda: iter([1, 2, 3])

        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))
        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))

        # Test with number of submissions equal to an integer > number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_standard_config()
        config.number_of_submissions = "5"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sub.source.new_crashes = lambda: iter([1, 2, 3])

        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))
        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        assert_raises(StopIteration, itera.next)

        # Test with number of submissions equal to an integer < number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_standard_config()
        config.number_of_submissions = "1"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sub.source.new_crashes = lambda: iter([1, 2, 3])

        eq_(itera.next(), ((1,), {}))
        assert_raises(StopIteration, itera.next)

    #--------------------------------------------------------------------------
    def test_new_crash_source_iterator(self):

        # Test with number of submissions equal to all
        # It raises StopIterations after all the elements were called
        config = self.get_new_crash_source_config()
        config.number_of_submissions = "all"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()

        config.new_crash_source.new_crash_source_class.return_value \
            .new_crashes = lambda: iter([1, 2, 3])
        itera = sub.source_iterator()

        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))
        assert_raises(StopIteration, itera.next)

        # Test with number of submissions equal to forever
        # It never raises StopIterations
        config = self.get_new_crash_source_config()
        config.number_of_submissions = "forever"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        # setup a fake iter using two form of the data to ensure it deals
        # with both forms correctly.
        config.new_crash_source.new_crash_source_class.return_value \
            .new_crashes = lambda: iter([1, ((2, ), {}), 3])

        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))
        eq_(itera.next(), ((1,), {}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))

        # Test with number of submissions equal to an integer > number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_new_crash_source_config()
        config.number_of_submissions = "5"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        config.new_crash_source.new_crash_source_class.return_value \
            .new_crashes = lambda: iter([((1, ), {'finished_func': 1,}), 2, 3])

        eq_(itera.next(), ((1,), {'finished_func': 1,}))
        eq_(itera.next(), ((2,), {}))
        eq_(itera.next(), ((3,), {}))
        eq_(itera.next(), ((1,), {'finished_func': 1,}))
        eq_(itera.next(), ((2,), {}))
        assert_raises(StopIteration, itera.next)

        # Test with number of submissions equal to an integer < number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_new_crash_source_config()
        config.number_of_submissions = "1"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        config.new_crash_source.new_crash_source_class.return_value \
            .new_crashes = lambda: iter([1, 2, 3])

        eq_(itera.next(), ((1,), {}))
        assert_raises(StopIteration, itera.next)

        # Test with number of submissions equal to an integer < number of items
        # AND the new_crashes iter returning an args, kwargs form rather than
        # than a crash_id
        # It raises StopIterations after some number of elements were called
        config = self.get_new_crash_source_config()
        config.number_of_submissions = "2"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        config.new_crash_source.new_crash_source_class.return_value \
            .new_crashes = lambda: iter(
                [
                    (((1, ['./1.json', './1.dump', './1.other.dump']), ), {}),
                    (((2, ['./2.json', './1.dump']), ), {})
                ]
            )

        eq_(
            itera.next(),
            (((1, ['./1.json', './1.dump', './1.other.dump']), ), {})
        )
        eq_(
            itera.next(),
            (((2, ['./2.json', './1.dump']), ), {})
        )
        assert_raises(StopIteration, itera.next)

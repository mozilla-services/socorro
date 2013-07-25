# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
import time
import json

from socorro.collector.submitter_app import (
    SubmitterApp,
    SubmitterFileSystemWalkerSource,
    DBSamplingCrashSource
)
from configman.dotdict import DotDict
from socorro.external.postgresql import dbapi2_util


#------------------------------------------------------------------------------
def sequencer(*args):
    def foo(*fargs, **fkwargs):
        for x in args:
            yield x
    return foo


#==============================================================================
class TestSubmitterFileSystemWalkerSource(unittest.TestCase):

    #--------------------------------------------------------------------------
    def get_standard_config(self):
        config = DotDict()
        config.search_root = None
        config.dump_suffix = '.dump'
        config.dump_field = "upload_file_minidump"

        config.logger = mock.MagicMock()

        return config

    #--------------------------------------------------------------------------
    def test_setup(self):
        config = self.get_standard_config()
        sub_walker = SubmitterFileSystemWalkerSource(config)
        self.assertEqual(sub_walker.config, config)
        self.assertEqual(sub_walker.config.logger, config.logger)

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
        self.assertTrue(isinstance(raw_crash, DotDict))
        self.assertEqual(raw_crash['name'], 'Gabi')

    #--------------------------------------------------------------------------
    def test_get_raw_dumps_as_files(self):
        config = self.get_standard_config()
        sub_walker = SubmitterFileSystemWalkerSource(config)

        dump_pathnames = ['raw_crash_file',
            '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.dump',
            '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash1.dump',
            '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash2.dump',
            ]
        raw_dumps_files = sub_walker.get_raw_dumps_as_files(dump_pathnames)

        dump_names = {'upload_file_minidump':
             '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.dump',
             'flash1':
             '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash1.dump',
             'flash2':
             '/some/path/6611a662-e70f-4ba5-a397-69a3a2121129.flash2.dump'
             }

        self.assertTrue(isinstance(raw_dumps_files, dict))
        self.assertEqual(raw_dumps_files, dump_names)

    #--------------------------------------------------------------------------
    def test_new_crashes(self):
        config = self.get_standard_config()
        sub_walker = SubmitterFileSystemWalkerSource(config)

        crash_path = sequencer('./6611a662-e70f-4ba5-a397-69a3a2121129.json',
                               './7611a662-e70f-4ba5-a397-69a3a2121129.json',
                               './8611a662-e70f-4ba5-a397-69a3a2121129.json',
                               )
        sub_walker.new_crashes = mock.Mock(side_effect=crash_path)
        new_crashes = sub_walker.new_crashes()

        self.assertTrue(isinstance(new_crashes.next(), str))
        self.assertEqual(new_crashes.next(),
            './7611a662-e70f-4ba5-a397-69a3a2121129.json')
        self.assertTrue(new_crashes.next().endswith(".json"))


#==============================================================================
class TestDBSamplingCrashSource(unittest.TestCase):

    #--------------------------------------------------------------------------
    def get_standard_config(self):
        config = DotDict()

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
        self.assertEqual(db_sampling.config, config)
        self.assertEqual(db_sampling.config.logger, config.logger)

    #--------------------------------------------------------------------------
    def test_new_crashes(self):
        config = self.get_standard_config()
        db_sampling = DBSamplingCrashSource(config)

        m_execute = mock.Mock()
        expected = sequencer('114559a5-d8e6-428c-8b88-1c1f22120314',
                             'c44245f4-c93b-49b8-86a2-c15dc3a695cb')

        db_sampling.new_crashes = mock.Mock(side_effect=expected)
        m_cursor = mock.Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchone = db_sampling.new_crashes
        conn = mock.Mock()
        conn.cursor.return_value = m_cursor

        r = dbapi2_util.execute_query_iter(conn, config.sql)
        self.assertEqual(r.next().next(),
                         '114559a5-d8e6-428c-8b88-1c1f22120314')
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with(config.sql, None)

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
        self.assertTrue(isinstance(raw_crash, DotDict))
        self.assertEqual(raw_crash['name'], 'Gabi')
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
        print raw_dumps_as_files
        self.assertTrue(isinstance(raw_dumps_as_files, dict))
        self.assertEqual(raw_dumps_as_files['upload_file_minidump'],
                         '86b58ff2-9708-487d-bfc4-9dac32121214.' \
                         'upload_file_minidump.TEMPORARY.dump'
                        )
        db_sampling._implementation.get_raw_dumps_as_files \
            .assert_called_with(crash_id)


#==============================================================================
class TestSubmitterApp(unittest.TestCase):

    #--------------------------------------------------------------------------
    def get_standard_config(self):
        config = DotDict()

        config.source = DotDict()
        mocked_source_crashstorage = mock.Mock()
        mocked_source_crashstorage.id = 'mocked_source_crashstorage'
        config.source.crashstorage_class = mock.Mock(
            return_value=mocked_source_crashstorage
        )

        config.destination = DotDict()
        mocked_destination_crashstorage = mock.Mock()
        mocked_destination_crashstorage.id = 'mocked_destination_crashstorage'
        config.destination.crashstorage_class = mock.Mock(
            return_value=mocked_destination_crashstorage
        )

        config.producer_consumer = DotDict()
        mocked_producer_consumer = mock.Mock()
        mocked_producer_consumer.id = 'mocked_producer_consumer'
        config.producer_consumer.producer_consumer_class = mock.Mock(
            return_value=mocked_producer_consumer
        )
        config.producer_consumer.number_of_threads = float(1)

        config.submitter = DotDict()
        config.submitter.delay = 0
        config.submitter.dry_run = False
        config.submitter.number_of_submissions = "all"

        config.logger = mock.MagicMock()

        return config

    #--------------------------------------------------------------------------
    def test_setup(self):
        config = self.get_standard_config()
        sub = SubmitterApp(config)
        self.assertEqual(sub.config, config)
        self.assertEqual(sub.config.logger, config.logger)

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
        mocked_get_raw_dumps_as_files = mock.Mock(return_value=fake_dump)
        sub.source.get_raw_dumps_as_files = mocked_get_raw_dumps_as_files

        sub.destination.save_raw_crash = mock.Mock()

        sub.transform(crash_id)
        sub.source.get_raw_crash.assert_called_with(crash_id)
        sub.source.get_raw_dumps_as_files.assert_called_with(crash_id)
        sub.destination.save_raw_crash.assert_called_with(fake_raw_crash,
                                                          fake_dump, crash_id)

    #--------------------------------------------------------------------------
    def test_source_iterator(self):

        # Test with number of submissions equal to all
        # It raises StopIterations after all the elements were called
        config = self.get_standard_config()
        config.submitter.number_of_submissions = "all"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sequence_generator = sequencer(1, 2, 3)
        sub.source.new_crashes = mock.Mock(side_effect=sequence_generator)

        self.assertEqual(itera.next(), ((1,), {}))
        self.assertEqual(itera.next(), ((2,), {}))
        self.assertEqual(itera.next(), ((3,), {}))
        self.assertRaises(StopIteration, itera.next)

        # Test with number of submissions equal to forever
        # It never raises StopIterations
        config = self.get_standard_config()
        config.submitter.number_of_submissions = "forever"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        itera = sub.source_iterator()

        sequence_generator = sequencer(1, 2, 3)
        sub.source.new_crashes = mock.Mock(side_effect=sequence_generator)

        self.assertEqual(itera.next(), ((1,), {}))
        self.assertEqual(itera.next(), ((2,), {}))
        self.assertEqual(itera.next(), ((3,), {}))
        self.assertEqual(itera.next(), ((1,), {}))
        self.assertEqual(itera.next(), ((2,), {}))
        self.assertEqual(itera.next(), ((3,), {}))

        # Test with number of submissions equal to an integer > number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_standard_config()
        config.submitter.number_of_submissions = "5"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sequence_generator = sequencer(1, 2, 3)
        sub.source.new_crashes = mock.Mock(side_effect=sequence_generator)

        self.assertEqual(itera.next(), ((1,), {}))
        self.assertEqual(itera.next(), ((2,), {}))
        self.assertEqual(itera.next(), ((3,), {}))
        self.assertEqual(itera.next(), ((1,), {}))
        self.assertEqual(itera.next(), ((2,), {}))
        self.assertRaises(StopIteration, itera.next)

        # Test with number of submissions equal to an integer < number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_standard_config()
        config.submitter.number_of_submissions = "1"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sequence_generator = sequencer(1, 2, 3)
        sub.source.new_crashes = mock.Mock(side_effect=sequence_generator)

        self.assertEqual(itera.next(), ((1,), {}))
        self.assertRaises(StopIteration, itera.next)

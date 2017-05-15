# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from itertools import izip_longest
from datetime import date

from mock import Mock
from nose.tools import eq_, ok_

from configman.dotdict import DotDict as ConfigmanDotDict

from socorro.unittest.testbase import TestCase
from socorro.external.postgresql.new_crash_source import (
    PGQueryNewCrashSource,
    DBCrashStorageWrapperNewCrashSource,
    PGPVNewCrashSource
)
from socorro.lib.util import DotDict as SocorroDotDict
from socorro.external.crashstorage_base import (
    FileDumpsMapping,
    MemoryDumpsMapping
)


class NewCrashSourceTestBase(TestCase):
    def get_standard_config(self):
        self.expected_sequence = ['one', 'two', 'three', 'four', 'five']
        config = ConfigmanDotDict()
        config.transaction_executor_class = Mock()
        config.transaction_executor_class.return_value.return_value = (
            self.expected_sequence
        )
        config.database_class = Mock()

        config.crash_id_query = (
            'select uuid from jobs order by '
            'queueddatetime DESC limit 1000'
        )

        config.logger = Mock()
        return config


class TestPGQueryNewCrashSource(NewCrashSourceTestBase):

    def test_init_and_close(self):
        config = self.get_standard_config()

        # the calls to be tested
        crash_source = PGQueryNewCrashSource(config, name='fred')
        crash_source.close()

        # this is what should have happened
        ok_(crash_source.config is config)
        eq_(crash_source.name, 'fred')
        config.database_class.assert_called_once_with(config)
        config.transaction_executor_class.assert_called_once_with(
            config,
            crash_source.database,
            quit_check_callback=None
        )
        crash_source.database.close.assert_called_once_with()

    def test_iter(self):
        config = self.get_standard_config()
        crash_source = PGQueryNewCrashSource(config, name='fred')
        crash_source.close()

        # the call to be tested & what should have happened
        for i, (exp, actual) in enumerate(izip_longest(
            self.expected_sequence,
            crash_source())
        ):
            eq_(exp, actual)

        eq_(
            i,
            4,
            'there should have been exactly 5 iterations, instead: %d'
            % (i + 1)
        )


class TestDBSamplingCrashStorageWrapper(NewCrashSourceTestBase):

    def get_standard_config(self):
        config = super(
            TestDBSamplingCrashStorageWrapper,
            self
        ).get_standard_config()
        config.implementation = ConfigmanDotDict()
        config.implementation.crashstorage_class = Mock()

        return config

    def test_init_and_close(self):
        config = self.get_standard_config()

        # the calls to be tested
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)
        db_sampling.close()

        # this is what should have happened
        ok_(db_sampling.config is config)
        config.database_class.assert_called_once_with(config)
        config.transaction_executor_class.assert_called_once_with(
            config,
            db_sampling.database,
            quit_check_callback=None
        )
        config.implementation.crashstorage_class.assert_called_once_with(
            config.implementation,
            None
        )
        db_sampling.database.close.assert_called_once_with()
        db_sampling._implementation.close.assert_called_once_with()

    def test_new_crashes(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        # the call to be tested & what should have happened
        for i, (exp, actual) in enumerate(izip_longest(
            self.expected_sequence,
            db_sampling.new_crashes())
        ):
            eq_(exp, actual)

        eq_(
            i,
            4,
            'there should have been exactly 5 iterations, instead: %d'
            % (i + 1)
        )

    def test_get_raw_crash(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        fake_raw_crash = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })

        mocked_get_raw_crash = Mock(return_value=fake_raw_crash)
        db_sampling._implementation.get_raw_crash = mocked_get_raw_crash

        # the call to be tested
        raw_crash = db_sampling.get_raw_crash(crash_id)

        # this is what should have happened
        ok_(fake_raw_crash is raw_crash)
        db_sampling._implementation.get_raw_crash.assert_called_with(crash_id)

    def test_get_raw_dump(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        fake_dump = 'contents of dump 86b58ff2-9708-487d-bfc4-9dac32121214'
        mocked_get_raw_dump = Mock(return_value=fake_dump)
        db_sampling._implementation.get_raw_dump = mocked_get_raw_dump

        # the call to be tested
        raw_dump = db_sampling.get_raw_dump(
            crash_id,
            'fred'
        )

        # this is what should have happened
        ok_(fake_dump is raw_dump)
        db_sampling._implementation.get_raw_dump.assert_called_with(
            crash_id,
            'fred'
        )

    def test_get_raw_dumps(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        fake_raw_dumps = MemoryDumpsMapping({
            'upload_file_minidump':
                'contents of dump 86b58ff2-9708-487d-bfc4-9dac32121214'
        })
        mocked_get_raw_dumps = Mock(return_value=fake_raw_dumps)
        db_sampling._implementation.get_raw_dumps = mocked_get_raw_dumps

        # the call to be tested
        raw_dumps = db_sampling.get_raw_dumps(crash_id)

        # this is what should have happened
        ok_(fake_raw_dumps is raw_dumps)
        db_sampling._implementation.get_raw_dumps.assert_called_with(crash_id)

    def test_get_raw_dumps_as_files(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        fake_dumps_as_files = FileDumpsMapping({
            'upload_file_minidump':
                '86b58ff2-9708-487d-bfc4-9dac32121214'
                '.upload_file_minidump.TEMPORARY.dump'
        })
        mocked_get_raw_dumps_as_files = Mock(return_value=fake_dumps_as_files)
        db_sampling._implementation.get_raw_dumps_as_files = \
            mocked_get_raw_dumps_as_files

        # the call to be tested
        raw_dumps_as_files = db_sampling.get_raw_dumps_as_files(crash_id)

        # this is what should have happened
        ok_(fake_dumps_as_files is raw_dumps_as_files)
        db_sampling._implementation.get_raw_dumps_as_files \
            .assert_called_with(crash_id)

    def test_get_processed(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        fake_processed = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })

        mocked_get_processed = Mock(return_value=fake_processed)
        db_sampling._implementation.get_processed = mocked_get_processed

        # the call to be tested
        processed = db_sampling.get_processed(crash_id)

        # this is what should have happened
        ok_(fake_processed is processed)
        db_sampling._implementation.get_processed.assert_called_with(crash_id)

    def test_get_unredacted_processed(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'
        fake_processed = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })

        mocked_get_processed = Mock(return_value=fake_processed)
        db_sampling._implementation.get_unredacted_processed = \
            mocked_get_processed

        # the call to be tested
        processed = db_sampling.get_unredacted_processed(crash_id)

        # this is what should have happened
        ok_(fake_processed is processed)
        db_sampling._implementation.get_unredacted_processed \
            .assert_called_with(crash_id)

    def test_remove(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)
        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'

        # the call to be tested
        db_sampling.remove(crash_id)

        # this is what should have happened
        db_sampling._implementation.remove \
            .assert_called_with(crash_id)

    def test_save_raw_crash(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)
        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'

        fake_raw_crash = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })
        fake_dumps = MemoryDumpsMapping({
            'upload_file_minidump':
                '86b58ff2-9708-487d-bfc4-9dac32121214'
                '.upload_file_minidump.TEMPORARY.dump'
        })

        # the call to be tested
        db_sampling.save_raw_crash(
            fake_raw_crash,
            fake_dumps,
            crash_id
        )

        # this is what should have happened
        db_sampling._implementation.save_raw_crash.assert_called_once_with(
            fake_raw_crash,
            fake_dumps,
            crash_id
        )

    def test_save_raw_crash_with_file_dumps(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)
        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'

        fake_raw_crash = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })
        fake_dumps_as_files = FileDumpsMapping({
            'upload_file_minidump':
                '86b58ff2-9708-487d-bfc4-9dac32121214'
                '.upload_file_minidump.TEMPORARY.dump'
        })

        # the call to be tested
        db_sampling.save_raw_crash_with_file_dumps(
            fake_raw_crash,
            fake_dumps_as_files,
            crash_id
        )

        # this is what should have happened
        db_sampling._implementation.save_raw_crash_with_file_dumps \
            .assert_called_once_with(
                fake_raw_crash,
                fake_dumps_as_files,
                crash_id
            )

    def test_save_processed(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)

        fake_processed = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })

        # the call to be tested
        db_sampling.save_processed(fake_processed)

        # this is what should have happened
        db_sampling._implementation.save_processed.assert_called_once_with(
            fake_processed
        )

    def test_save_raw_and_processed(self):
        config = self.get_standard_config()
        db_sampling = DBCrashStorageWrapperNewCrashSource(config)
        crash_id = '86b58ff2-9708-487d-bfc4-9dac32121214'

        fake_raw_crash = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })
        fake_dumps_as_files = FileDumpsMapping({
            'upload_file_minidump':
                '86b58ff2-9708-487d-bfc4-9dac32121214'
                '.upload_file_minidump.TEMPORARY.dump'
        })
        fake_processed = SocorroDotDict({
            "name": "Gabi",
            "submitted_timestamp": "2012-12-14T00:00:00"
        })

        # the call to be tested
        db_sampling.save_raw_and_processed(
            fake_raw_crash,
            fake_dumps_as_files,
            fake_processed,
            crash_id
        )

        # this is what should have happened
        db_sampling._implementation.save_raw_and_processed \
            .assert_called_once_with(
                fake_raw_crash,
                fake_dumps_as_files,
                fake_processed,
                crash_id
            )


class TestPGPVNewCrashSource(NewCrashSourceTestBase):

    def get_standard_config(self):
        config = super(
            TestPGPVNewCrashSource,
            self
        ).get_standard_config()
        config.crash_id_query = (
            "select uuid "
            "from reports_clean rc join product_versions pv "
            "    on rc.product_version_id = pv.product_version_id "
            "where "
            "%s <= date_processed and date_processed < %s"
            "and %s between pv.build_date and pv.sunset_date"
        )
        config.date = date(2015, 10, 18)
        return config

    def test_init_and_close(self):
        config = self.get_standard_config()

        # the calls to be tested
        a_new_crash_source = PGPVNewCrashSource(config, name='fred')
        a_new_crash_source.close()

        # this is what should have happened
        ok_(a_new_crash_source.config is config)
        config.database_class.assert_called_once_with(config)
        config.transaction_executor_class.assert_called_once_with(
            config,
            a_new_crash_source.database,
            quit_check_callback=None
        )
        a_new_crash_source.database.close.assert_called_once_with()
        eq_(
            a_new_crash_source.data,
            (
                date(2015, 10, 18),
                date(2015, 10, 19),
                date(2015, 10, 18),
            )
        )
        eq_(
            a_new_crash_source.crash_id_query,
            config.crash_id_query
        )

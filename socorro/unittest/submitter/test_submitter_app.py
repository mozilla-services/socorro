# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
import mock
import pytest

from socorro.submitter.submitter_app import SubmitterApp
from socorro.unittest.testbase import TestCase


class TestSubmitterApp(TestCase):

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

        config.new_crash_source = DotDict()
        config.new_crash_source.new_crash_source_class = None

        config.submitter = DotDict()
        config.submitter.delay = 0
        config.submitter.dry_run = False
        config.number_of_submissions = "all"

        config.logger = mock.MagicMock()

        return config

    def get_new_crash_source_config(self):
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

        config.new_crash_source = DotDict()
        mocked_new_crash_source = mock.Mock()
        mocked_new_crash_source.id = 'mocked_new_crash_source'
        config.new_crash_source.new_crash_source_class = mock.Mock(
            return_value=mocked_new_crash_source
        )

        config.submitter = DotDict()
        config.submitter.delay = 0
        config.submitter.dry_run = False
        config.number_of_submissions = "all"

        config.logger = mock.MagicMock()

        return config

    def test_setup(self):
        config = self.get_standard_config()
        sub = SubmitterApp(config)
        assert sub.config == config
        assert sub.config.logger == config.logger

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
        sub.destination.save_raw_crash_with_file_dumps.assert_called_with(
            fake_raw_crash,
            fake_dump,
            crash_id
        )

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

        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})
        with pytest.raises(StopIteration):
            itera.next()

        # Test with number of submissions equal to forever
        # It never raises StopIterations
        config = self.get_standard_config()
        config.number_of_submissions = "forever"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sub.source.new_crashes = lambda: iter([1, 2, 3])

        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})
        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})

        # Test with number of submissions equal to an integer > number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_standard_config()
        config.number_of_submissions = "5"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sub.source.new_crashes = lambda: iter([1, 2, 3])

        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})
        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        with pytest.raises(StopIteration):
            itera.next()

        # Test with number of submissions equal to an integer < number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_standard_config()
        config.number_of_submissions = "1"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        sub.source.new_crashes = lambda: iter([1, 2, 3])

        assert itera.next() == ((1,), {})
        with pytest.raises(StopIteration):
            itera.next()

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

        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})
        with pytest.raises(StopIteration):
            itera.next()

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

        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})
        assert itera.next() == ((1,), {})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})

        # Test with number of submissions equal to an integer > number of items
        # It raises StopIterations after some number of elements were called
        config = self.get_new_crash_source_config()
        config.number_of_submissions = "5"
        sub = SubmitterApp(config)
        sub._setup_source_and_destination()
        sub._setup_task_manager()
        itera = sub.source_iterator()

        def _iter():
            return iter([((1, ), {'finished_func': (1,)}), 2, 3])
        config.new_crash_source.new_crash_source_class.return_value.new_crashes = _iter

        assert itera.next() == ((1,), {'finished_func': (1,)})
        assert itera.next() == ((2,), {})
        assert itera.next() == ((3,), {})
        assert itera.next() == ((1,), {'finished_func': (1,)})
        assert itera.next() == ((2,), {})
        with pytest.raises(StopIteration):
            itera.next()

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

        assert itera.next() == ((1,), {})
        with pytest.raises(StopIteration):
            itera.next()

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

        item1 = (((1, ['./1.json', './1.dump', './1.other.dump']), ), {})
        item2 = (((2, ['./2.json', './1.dump']), ), {})
        config.new_crash_source.new_crash_source_class.return_value \
            .new_crashes = lambda: iter([item1, item2])

        assert itera.next() == item1
        assert itera.next() == item2
        with pytest.raises(StopIteration):
            itera.next()

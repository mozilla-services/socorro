# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
import mock
import pytest

from socorro.external.crashstorage_base import (
    CrashIDNotFound,
    PolyStorageError,
)
from socorro.processor.processor_app import ProcessorApp
from socorro.unittest.testbase import TestCase


def sequencer(*args):
    def foo(*fargs, **fkwargs):
        for x in args:
            yield x
    return foo


class TestProcessorApp(TestCase):

    def get_standard_config(self, sentry_dsn=None):
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

        config.processor = DotDict()
        mocked_processor = mock.Mock()
        mocked_processor.id = 'mocked_processor'
        config.processor.processor_class = mock.Mock(
            return_value=mocked_processor
        )

        config.number_of_submissions = 'forever'
        config.new_crash_source = DotDict()

        class FakedNewCrashSource(object):

            def __init__(self, *args, **kwargs):
                pass

            def new_crashes(self):
                return sequencer(
                    ((1,), {}),
                    2,  # ensure both forms acceptable
                    None,
                    ((3,), {})
                )()

        config.new_crash_source.new_crash_source_class = FakedNewCrashSource

        config.companion_process = DotDict()
        mocked_companion_process = mock.Mock()
        config.companion_process.companion_class = mock.Mock(
            return_value=mocked_companion_process
        )

        config.logger = mock.MagicMock()

        config.sentry = mock.MagicMock()
        config.sentry.dsn = sentry_dsn

        return config

    def test_source_iterator(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        g = pa.source_iterator()
        assert g.next() == ((1,), {})
        assert g.next() == ((2,), {})
        assert g.next() is None
        assert g.next() == ((3,), {})

    def test_transform_success(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()

        fake_raw_crash = DotDict()
        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)
        pa.source.get_raw_crash = mocked_get_raw_crash

        fake_dump = {'upload_file_minidump': 'fake_dump_TEMPORARY.dump'}
        mocked_get_raw_dumps_as_files = mock.Mock(return_value=fake_dump)
        pa.source.get_raw_dumps_as_files = mocked_get_raw_dumps_as_files

        fake_processed_crash = DotDict()
        mocked_get_unredacted_processed = mock.Mock(
            return_value=fake_processed_crash
        )
        pa.source.get_unredacted_processed = mocked_get_unredacted_processed

        mocked_process_crash = mock.Mock(return_value=7)
        pa.processor.process_crash = mocked_process_crash
        pa.destination.save_processed = mock.Mock()
        finished_func = mock.Mock()
        patch_path = 'socorro.processor.processor_app.os.unlink'
        with mock.patch(patch_path) as mocked_unlink:
            # the call being tested
            pa.transform(17, finished_func)
        # test results
        mocked_unlink.assert_called_with('fake_dump_TEMPORARY.dump')
        pa.source.get_raw_crash.assert_called_with(17)
        pa.processor.process_crash.assert_called_with(
            fake_raw_crash,
            fake_dump,
            fake_processed_crash
        )
        pa.destination.save_raw_and_processed.assert_called_with(
            fake_raw_crash, None, 7, 17
        )
        assert finished_func.call_count == 1

    def test_transform_crash_id_missing(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=CrashIDNotFound(17))
        pa.source.get_raw_crash = mocked_get_raw_crash

        finished_func = mock.Mock()
        pa.transform(17, finished_func)
        pa.source.get_raw_crash.assert_called_with(17)
        pa.processor.reject_raw_crash.assert_called_with(
            17,
            'this crash cannot be found in raw crash storage'
        )
        assert finished_func.call_count == 1

    def test_transform_unexpected_exception(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=Exception('bummer'))
        pa.source.get_raw_crash = mocked_get_raw_crash

        finished_func = mock.Mock()
        pa.transform(17, finished_func)
        pa.source.get_raw_crash.assert_called_with(17)
        pa.processor.reject_raw_crash.assert_called_with(
            17,
            'error in loading: bummer'
        )
        assert finished_func.call_count == 1

    def test_transform_polystorage_error_without_raven_configured(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({'raw': 'crash'})
        pa.source.get_raw_dumps_as_files.return_value = {}

        def mocked_save_raw_and_processed(*_):
            exception = PolyStorageError()
            exception.exceptions.append(NameError('waldo'))
            raise exception

        pa.destination.save_raw_and_processed.side_effect = (
            mocked_save_raw_and_processed
        )
        # The important thing is that this is the exception that
        # is raised and not something from the raven error handling.
        with pytest.raises(PolyStorageError):
            pa.transform('mycrashid')

        config.logger.warning.assert_called_with(
            'Sentry DSN is not configured and an exception happened'
        )

    @mock.patch('socorro.lib.raven_client.raven')
    def test_transform_polystorage_error_with_raven_configured_successful(self, mock_raven):
        # Mock everything
        def mock_capture_exception(exc_info=None):
            return 'someidentifier'

        raven_mock_client = mock.MagicMock()
        raven_mock_client.captureException.side_effect = mock_capture_exception
        mock_raven.Client.return_value = raven_mock_client

        # Set up a processor and mock out .save_raw_and_processed() with multiple
        # errors
        config = self.get_standard_config(sentry_dsn='https://abc123@example.com/project')
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({'raw': 'crash'})
        pa.source.get_raw_dumps_as_files.return_value = {}

        expected_exception_1 = NameError('waldo')
        expected_exception_2 = AssertionError(False)

        def mocked_save_raw_and_processed(*_):
            exception = PolyStorageError()
            exception.exceptions.append(expected_exception_1)
            exception.exceptions.append(expected_exception_2)
            raise exception

        pa.destination.save_raw_and_processed.side_effect = mocked_save_raw_and_processed

        # The important thing is that this is the exception that is raised and
        # not something from the raven error handling
        with pytest.raises(PolyStorageError):
            pa.transform('mycrashid')

        # Assert that we sent both exceptions to Sentry
        raven_mock_client.captureException.assert_has_calls([
            mock.call(expected_exception_1),
            mock.call(expected_exception_2)
        ])

        # Assert that the logger logged the appropriate thing
        config.logger.info.assert_called_with(
            'Error captured in Sentry! Reference: someidentifier'
        )

    @mock.patch('socorro.lib.raven_client.raven')
    def test_transform_save_error_with_raven_configured_successful(self, mock_raven):
        # Mock everything
        def mock_capture_exception(exc_info=None):
            return 'someidentifier'

        raven_mock_client = mock.MagicMock()
        raven_mock_client.captureException.side_effect = mock_capture_exception
        mock_raven.Client.return_value = raven_mock_client

        # Set up a processor and mock .save_raw_and_processed() to raise an exception
        config = self.get_standard_config(sentry_dsn='https://abc123@example.com/project')
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({'raw': 'crash'})
        pa.source.get_raw_dumps_as_files.return_value = {}

        expected_exception = ValueError('simulated error')

        def mocked_save_raw_and_processed(*_):
            raise expected_exception

        pa.destination.save_raw_and_processed.side_effect = mocked_save_raw_and_processed

        # Run .transform() and make sure it raises the ValueError
        with pytest.raises(ValueError):
            pa.transform('mycrashid')

        # Assert that we sent the exception to Sentry
        raven_mock_client.captureException.assert_called_once_with(expected_exception)

        # Assert that the logger logged the appropriate thing
        config.logger.info.assert_called_with(
            'Error captured in Sentry! Reference: someidentifier'
        )

    @mock.patch('socorro.lib.raven_client.raven')
    def test_transform_get_error_with_raven_configured_successful(self, mock_raven):
        # Mock everything
        def mock_capture_exception(exc_info=None):
            return 'someidentifier'

        raven_mock_client = mock.MagicMock()
        raven_mock_client.captureException.side_effect = mock_capture_exception
        mock_raven.Client.return_value = raven_mock_client

        # Set up a processor and mock .get_raw_crash() to raise an exception
        config = self.get_standard_config(sentry_dsn='https://abc123@example.com/project')
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()

        expected_exception = ValueError('simulated error')

        def mocked_get_raw_crash(*args, **kwargs):
            raise expected_exception

        pa.source.get_raw_crash.side_effect = mocked_get_raw_crash

        # Note that the processor silently ignores .get_raw_crash() and
        # .get_raw_dumps_as_files() errors and only logs stuff with the
        # assumption that they're ephemeral
        pa.transform('mycrashid')

        # Assert that the processor sent something to Sentry
        raven_mock_client.captureException.assert_called_once_with(expected_exception)

        # Assert that the logger logged the appropriate thing
        config.logger.info.assert_called_with(
            'Error captured in Sentry! Reference: someidentifier'
        )

    @mock.patch('socorro.lib.raven_client.raven')
    def test_transform_polystorage_error_with_raven_configured_failing(
        self,
        mock_raven,
    ):

        def mock_capture_exception(exc_info=None):
            raise ValueError('Someone is wrong on the Internet')

        raven_mock_client = mock.MagicMock()
        raven_mock_client.captureException.side_effect = mock_capture_exception

        mock_raven.Client.return_value = raven_mock_client

        config = self.get_standard_config(
            sentry_dsn='https://abc123@example.com/project'
        )
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({'raw': 'crash'})
        pa.source.get_raw_dumps_as_files.return_value = {}

        def mocked_save_raw_and_processed(*_):
            exception = PolyStorageError()
            exception.exceptions.append(NameError('waldo'))
            exception.exceptions.append(AssertionError(False))
            raise exception

        pa.destination.save_raw_and_processed.side_effect = (
            mocked_save_raw_and_processed
        )
        # The important thing is that this is the exception that
        # is raised and not something from the raven error handling.
        with pytest.raises(PolyStorageError):
            pa.transform('mycrashid')

        config.logger.error.assert_called_with(
            'Unable to report error with Raven', exc_info=True
        )

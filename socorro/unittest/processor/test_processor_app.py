# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest import mock

from configman.dotdict import DotDict
import pytest

from socorro.external.crashstorage_base import CrashIDNotFound, PolyStorageError
from socorro.processor.processor_app import ProcessorApp


def sequencer(*args):
    def foo(*fargs, **fkwargs):
        for x in args:
            yield x

    return foo


class FakeCrashQueue:
    def __init__(self, *args, **kwargs):
        pass

    def new_crashes(self):
        return sequencer(
            ((1,), {}), 2, None, ((3,), {})  # ensure both forms acceptable
        )()


class TestProcessorApp:
    def get_standard_config(self):
        config = DotDict()

        config.source = DotDict()
        mocked_source_crashstorage = mock.Mock()
        mocked_source_crashstorage.id = "mocked_source_crashstorage"
        config.source.crashstorage_class = mock.Mock(
            return_value=mocked_source_crashstorage
        )

        config.destination = DotDict()
        mocked_destination_crashstorage = mock.Mock()
        mocked_destination_crashstorage.id = "mocked_destination_crashstorage"
        config.destination.crashstorage_class = mock.Mock(
            return_value=mocked_destination_crashstorage
        )

        config.processor = DotDict()
        mocked_processor = mock.Mock()
        mocked_processor.id = "mocked_processor"
        config.processor.processor_class = mock.Mock(return_value=mocked_processor)

        config.queue = DotDict()
        config.queue.crashqueue_class = FakeCrashQueue

        config.companion_process = DotDict()
        mocked_companion_process = mock.Mock()
        config.companion_process.companion_class = mock.Mock(
            return_value=mocked_companion_process
        )

        return config

    def test_source_iterator(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        g = pa.source_iterator()
        assert next(g) == ((1,), {})
        assert next(g) == ((2,), {})
        assert next(g) is None
        assert next(g) == ((3,), {})

    def test_transform_success(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()

        fake_raw_crash = DotDict({"raw": "1"})
        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)
        pa.source.get_raw_crash = mocked_get_raw_crash

        fake_dumps = {"upload_file_minidump": "fake_dump_TEMPORARY.dump"}
        mocked_get_raw_dumps_as_files = mock.Mock(return_value=fake_dumps)
        pa.source.get_raw_dumps_as_files = mocked_get_raw_dumps_as_files

        fake_processed_crash = DotDict({"uuid": "9d8e7127-9d98-4d92-8ab1-065982200317"})
        mocked_get_unredacted_processed = mock.Mock(return_value=fake_processed_crash)
        pa.source.get_unredacted_processed = mocked_get_unredacted_processed

        mocked_process_crash = mock.Mock(return_value=DotDict({"processed": "1"}))
        pa.processor.process_crash = mocked_process_crash
        pa.destination.save_processed_crash = mock.Mock()
        finished_func = mock.Mock()
        patch_path = "socorro.processor.processor_app.os.unlink"
        with mock.patch(patch_path) as mocked_unlink:
            # the call being tested
            pa.transform(17, finished_func)
        # test results
        mocked_unlink.assert_called_with("fake_dump_TEMPORARY.dump")
        pa.source.get_raw_crash.assert_called_with(17)
        pa.processor.process_crash.assert_called_with(
            fake_raw_crash, fake_dumps, fake_processed_crash
        )
        pa.destination.save_processed_crash.assert_called_with(
            {"raw": "1"}, {"processed": "1"}
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
            17, "crash cannot be found in raw crash storage"
        )
        assert finished_func.call_count == 1

    def test_transform_unexpected_exception(self):
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=Exception("bummer"))
        pa.source.get_raw_crash = mocked_get_raw_crash

        finished_func = mock.Mock()
        pa.transform(17, finished_func)
        pa.source.get_raw_crash.assert_called_with(17)
        pa.processor.reject_raw_crash.assert_called_with(17, "error in loading: bummer")
        assert finished_func.call_count == 1

    def test_transform_polystorage_error_without_sentry_configured(self, caplogpp):
        caplogpp.set_level("DEBUG")

        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({"raw": "crash"})
        pa.source.get_raw_dumps_as_files.return_value = {}

        def mocked_save_processed_crash(*args, **kwargs):
            exception = PolyStorageError()
            exception.exceptions.append(NameError("waldo"))
            raise exception

        pa.destination.save_processed_crash.side_effect = mocked_save_processed_crash

        # The important thing is that this is the exception that
        # is raised and not something from the sentry error handling.
        with pytest.raises(PolyStorageError):
            pa.transform("mycrashid")

        logging_msgs = [rec.message for rec in caplogpp.records]
        assert "Sentry DSN is not configured and an exception happened" in logging_msgs

    @mock.patch("socorro.lib.sentry_client.get_hub")
    @mock.patch("socorro.lib.sentry_client.is_enabled", return_value=True)
    def test_transform_polystorage_error_with_sentry_configured_successful(
        self, is_enabled, mock_get_hub, caplogpp
    ):
        caplogpp.set_level("DEBUG")

        # Mock everything
        mock_hub = mock.MagicMock()
        mock_hub.capture_exception.return_value = "someidentifier"
        mock_get_hub.return_value = mock_hub

        # Set up a processor and mock out .save_processed_crash() with multiple
        # errors
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({"raw": "crash"})
        pa.source.get_raw_dumps_as_files.return_value = {}

        expected_exception = PolyStorageError()
        expected_exception.exceptions.append(NameError("waldo"))
        expected_exception.exceptions.append(AssertionError(False))
        pa.destination.save_processed_crash.side_effect = expected_exception

        # The important thing is that this is the exception that is raised and
        # not something from the sentry error handling
        with pytest.raises(PolyStorageError):
            pa.transform("mycrashid")

        # Assert that we sent both exceptions to Sentry
        mock_hub.capture_exception.assert_has_calls(
            [mock.call(error=exc) for exc in expected_exception.exceptions]
        )

        # Assert that the logger logged the appropriate thing
        logging_msgs = [rec.message for rec in caplogpp.records]
        assert "Error captured in Sentry! Reference: someidentifier" in logging_msgs

    @mock.patch("socorro.lib.sentry_client.get_hub")
    def test_transform_save_error_with_sentry_configured_successful(
        self, mock_get_hub, caplogpp
    ):
        caplogpp.set_level("DEBUG")

        mock_hub = mock.MagicMock()
        mock_hub.capture_exception.side_effect = RuntimeError("should not be called")
        mock_get_hub.return_value = mock_hub

        # Set up a processor and mock .save_processed_crash() to raise an exception
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({"raw": "crash"})
        pa.source.get_raw_dumps_as_files.return_value = {}

        expected_exception = ValueError("simulated error")
        pa.destination.save_processed_crash.side_effect = expected_exception

        # Run .transform() and make sure it raises the ValueError
        with pytest.raises(ValueError):
            pa.transform("mycrashid")

        # Assert that the exception was not sent to Sentry and not logged
        assert not mock_hub.capture_exception.called
        assert len(caplogpp.records) == 0

    @mock.patch("socorro.lib.sentry_client.get_hub")
    @mock.patch("socorro.lib.sentry_client.is_enabled", return_value=True)
    def test_transform_get_error_with_sentry_configured_successful(
        self, is_enabled, mock_get_hub, caplogpp
    ):
        caplogpp.set_level("DEBUG")

        mock_hub = mock.MagicMock()
        mock_hub.capture_exception.return_value = "someidentifier"
        mock_get_hub.return_value = mock_hub

        # Set up a processor and mock .get_raw_crash() to raise an exception
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()

        expected_exception = ValueError("simulated error")
        pa.source.get_raw_crash.side_effect = expected_exception

        # The processor catches all exceptions from .get_raw_crash() and
        # .get_raw_dumps_as_files(), so there's nothing we need to catch here
        pa.transform("mycrashid")

        # Assert that the processor sent something to Sentry
        assert mock_hub.capture_exception.call_args_list == [
            mock.call(error=(ValueError, expected_exception, mock.ANY))
        ]

        # Assert that the logger logged the appropriate thing
        logging_msgs = [rec.message for rec in caplogpp.records]
        assert "Error captured in Sentry! Reference: someidentifier" in logging_msgs

    @mock.patch("socorro.lib.sentry_client.get_hub")
    @mock.patch("socorro.lib.sentry_client.is_enabled", return_value=True)
    def test_transform_polystorage_error_with_sentry_configured_failing(
        self, is_enabled, mock_get_hub, caplogpp
    ):
        caplogpp.set_level("DEBUG")

        mock_hub = mock.MagicMock()

        # Mock this to throw an error if it's called because it shouldn't get called
        mock_hub.capture_exception.side_effect = ValueError("sentry error")
        mock_get_hub.return_value = mock_hub

        # Set up processor and mock .save_processed_crash() to raise an exception
        config = self.get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        pa.source.get_raw_crash.return_value = DotDict({"raw": "crash"})
        pa.source.get_raw_dumps_as_files.return_value = {}

        first_exc_info = (NameError, NameError("waldo"), "fake tb 1")
        second_exc_info = (AssertionError, AssertionError(False), "fake tb 2")
        expected_exception = PolyStorageError()
        expected_exception.exceptions.append(first_exc_info)
        expected_exception.exceptions.append(second_exc_info)
        pa.destination.save_processed_crash.side_effect = expected_exception

        # Make sure the PolyStorageError is raised and not the error from
        # .captureException()
        with pytest.raises(PolyStorageError):
            pa.transform("mycrashid")

        # Assert logs for failing to process crash
        expected = [
            # Logs for failed Sentry reporting for first exception
            ("Unable to report error with Sentry", mock.ANY),
            ("Sentry DSN is not configured and an exception happened", None),
            ("Exception occurred", first_exc_info),
            # Logs for failed Sentry reporting for second exception
            ("Unable to report error with Sentry", mock.ANY),
            ("Sentry DSN is not configured and an exception happened", None),
            ("Exception occurred", second_exc_info),
            # Log for failing to process or save the crash
            ("error in processing or saving crash mycrashid", None),
        ]
        actual = [(rec.message, rec.exc_info) for rec in caplogpp.records]

        assert actual == expected

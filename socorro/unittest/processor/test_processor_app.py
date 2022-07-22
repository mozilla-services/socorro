# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os
from pathlib import Path
from unittest import mock
from unittest.mock import ANY

from configman.dotdict import DotDict
from markus.testing import MetricsMock
import pytest

from socorro.external.crashstorage_base import CrashIDNotFound, PolyStorageError
from socorro.processor.processor_app import ProcessorApp, count_sentry_scrub_error


def sequencer(*args):
    def foo(*fargs, **fkwargs):
        yield from args

    return foo


class FakeCrashQueue:
    def __init__(self, *args, **kwargs):
        pass

    def new_crashes(self):
        return sequencer(
            ((1,), {}), 2, None, ((3,), {})  # ensure both forms acceptable
        )()


def get_standard_config():
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


class TestProcessorApp:
    def test_source_iterator(self):
        config = get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        g = pa.source_iterator()
        assert next(g) == ((1,), {})
        assert next(g) == ((2,), {})
        assert next(g) is None
        assert next(g) == ((3,), {})

    def test_transform_success(self):
        config = get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()

        fake_raw_crash = DotDict({"raw": "1"})
        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)
        pa.source.get_raw_crash = mocked_get_raw_crash

        fake_dumps = {"upload_file_minidump": "fake_dump_TEMPORARY.dump"}
        mocked_get_dumps_as_files = mock.Mock(return_value=fake_dumps)
        pa.source.get_dumps_as_files = mocked_get_dumps_as_files

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
            pa.transform("17", finished_func)
        # test results
        mocked_unlink.assert_called_with("fake_dump_TEMPORARY.dump")
        pa.source.get_raw_crash.assert_called_with("17")
        pa.processor.process_crash.assert_called_with(
            "default", fake_raw_crash, fake_dumps, fake_processed_crash
        )
        pa.destination.save_processed_crash.assert_called_with(
            {"raw": "1"}, {"processed": "1"}
        )
        assert finished_func.call_count == 1

    def test_transform_crash_id_missing(self):
        config = get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=CrashIDNotFound(17))
        pa.source.get_raw_crash = mocked_get_raw_crash

        finished_func = mock.Mock()
        pa.transform("17", finished_func)
        pa.source.get_raw_crash.assert_called_with("17")
        pa.processor.reject_raw_crash.assert_called_with(
            "17", "crash cannot be found in raw crash storage"
        )
        assert finished_func.call_count == 1

    def test_transform_unexpected_exception(self):
        config = get_standard_config()
        pa = ProcessorApp(config)
        pa._setup_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=Exception("bummer"))
        pa.source.get_raw_crash = mocked_get_raw_crash

        finished_func = mock.Mock()
        pa.transform("17", finished_func)
        pa.source.get_raw_crash.assert_called_with("17")
        pa.processor.reject_raw_crash.assert_called_with(
            "17", "error in loading: bummer"
        )
        assert finished_func.call_count == 1


TRANSFORM_GET_ERROR = {
    "breadcrumbs": ANY,
    "contexts": {
        "runtime": {
            "build": ANY,
            "name": "CPython",
            "version": ANY,
        }
    },
    "environment": "production",
    "event_id": ANY,
    "exception": {
        "values": [
            {
                "mechanism": None,
                "module": None,
                "stacktrace": {
                    "frames": [
                        {
                            "abs_path": "/app/socorro/processor/processor_app.py",
                            "context_line": ANY,
                            "filename": "socorro/processor/processor_app.py",
                            "function": "process_crash",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "socorro.processor.processor_app",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/usr/local/lib/python3.9/unittest/mock.py",
                            "context_line": ANY,
                            "filename": "unittest/mock.py",
                            "function": "__call__",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "unittest.mock",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/usr/local/lib/python3.9/unittest/mock.py",
                            "context_line": ANY,
                            "filename": "unittest/mock.py",
                            "function": "_mock_call",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "unittest.mock",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/usr/local/lib/python3.9/unittest/mock.py",
                            "context_line": ANY,
                            "filename": "unittest/mock.py",
                            "function": "_execute_mock_call",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "unittest.mock",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                    ]
                },
                "type": "ValueError",
                "value": "simulated error",
            }
        ]
    },
    "extra": {"crash_id": "930b08ba-e425-49bf-adbd-7c9172220721"},
    "level": "error",
    "modules": ANY,
    "platform": "python",
    "release": ANY,
    "sdk": {
        "integrations": [
            "atexit",
            "boto3",
            "dedupe",
            "excepthook",
            "modules",
            "stdlib",
            "threading",
        ],
        "name": "sentry.python",
        "packages": [{"name": "pypi:sentry-sdk", "version": "1.7.2"}],
        "version": "1.7.2",
    },
    "server_name": "testhost",
    "timestamp": ANY,
    "transaction_info": {},
}


def test_transform_get_error(sentry_helper, caplogpp):
    caplogpp.set_level("DEBUG")

    # Set up a processor and mock .get_raw_crash() to raise an exception
    config = get_standard_config()
    processor = ProcessorApp(config)
    # NOTE(willkg): This is relative to this file
    basedir = Path(__file__).resolve().parent.parent.parent
    host_id = "testhost"
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    processor.configure_sentry(basedir=basedir, host_id=host_id, sentry_dsn=sentry_dsn)
    processor._setup_source_and_destination()

    expected_exception = ValueError("simulated error")
    processor.source.get_raw_crash.side_effect = expected_exception

    with sentry_helper.reuse() as sentry_client:
        # The processor catches all exceptions from .get_raw_crash() and
        # .get_dumps_as_files(), so there's nothing we need to catch here
        processor.transform("930b08ba-e425-49bf-adbd-7c9172220721")

        (event,) = sentry_client.events

        # If this test fails, this will print out the new event that you can copy
        # and paste and then edit above
        print(json.dumps(event, indent=4, sort_keys=True))

        # Assert that there are no frame-local variables
        assert event == TRANSFORM_GET_ERROR

        # Assert that the logger logged the appropriate thing
        logging_msgs = [rec.message for rec in caplogpp.records]
        assert (
            f"Error captured in Sentry! Reference: {event['event_id']}" in logging_msgs
        )


def test_count_sentry_scrub_error():
    with MetricsMock() as metricsmock:
        metricsmock.clear_records()
        count_sentry_scrub_error("foo")
        metricsmock.assert_incr("processor.sentry_scrub_error", value=1)


def test_transform_polystorage_error(sentry_helper, caplogpp):
    caplogpp.set_level("DEBUG")

    # Set up processor and mock .save_processed_crash() to raise an exception
    config = get_standard_config()
    processor = ProcessorApp(config)
    # NOTE(willkg): This is relative to this file
    basedir = Path(__file__).resolve().parent.parent.parent
    host_id = "testhost"
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    processor.configure_sentry(basedir=basedir, host_id=host_id, sentry_dsn=sentry_dsn)
    processor._setup_source_and_destination()
    processor.source.get_raw_crash.return_value = DotDict({"raw": "crash"})
    processor.source.get_dumps_as_files.return_value = {}

    # FIXME(willkg): the structure of the events suggest this PolyStorageError isn't
    # really working since it's not capturing any stack information
    expected_exception = PolyStorageError()
    expected_exception.exceptions.append(NameError("waldo"))
    expected_exception.exceptions.append(AssertionError(False))
    processor.destination.save_processed_crash.side_effect = expected_exception

    crash_id = "930b08ba-e425-49bf-adbd-7c9172220721"

    with sentry_helper.reuse() as sentry_client:
        # The important thing is that this is the exception that is raised and
        # not something from the sentry error handling
        with pytest.raises(PolyStorageError):
            processor.transform(crash_id)

        name_error_event, assertion_error_event = sentry_client.events

        assert name_error_event["exception"] == {
            "values": [
                {
                    "mechanism": None,
                    "module": None,
                    "type": "NameError",
                    "value": "waldo",
                }
            ]
        }
        assert name_error_event["extra"]["crash_id"] == crash_id
        assert assertion_error_event["exception"] == {
            "values": [
                {
                    "mechanism": None,
                    "module": None,
                    "type": "AssertionError",
                    "value": "False",
                }
            ]
        }
        assert assertion_error_event["extra"]["crash_id"] == crash_id

        # Assert that the logger logged the appropriate thing
        logging_msgs = [rec.message for rec in caplogpp.records]
        nameerror_msg = (
            f"Error captured in Sentry! Reference: {name_error_event['event_id']}"
        )
        assert nameerror_msg in logging_msgs
        assertion_msg = (
            f"Error captured in Sentry! Reference: {name_error_event['event_id']}"
        )
        assert assertion_msg in logging_msgs


def test_transform_save_error(sentry_helper, caplogpp):
    caplogpp.set_level("DEBUG")

    # Set up a processor and mock .save_processed_crash() to raise an exception
    config = get_standard_config()
    processor = ProcessorApp(config)
    # NOTE(willkg): This is relative to this file
    basedir = Path(__file__).resolve().parent.parent.parent
    host_id = "testhost"
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    processor.configure_sentry(basedir=basedir, host_id=host_id, sentry_dsn=sentry_dsn)
    processor._setup_source_and_destination()
    processor.source.get_raw_crash.return_value = DotDict({"raw": "crash"})
    processor.source.get_dumps_as_files.return_value = {}

    expected_exception = ValueError("simulated error")
    processor.destination.save_processed_crash.side_effect = expected_exception

    crash_id = "930b08ba-e425-49bf-adbd-7c9172220721"

    with sentry_helper.reuse() as sentry_client:
        # Run .transform() and make sure it raises the ValueError
        with pytest.raises(ValueError):
            processor.transform(crash_id)

        # Assert that the exception was not sent to Sentry and not logged at this
        # point--it gets caught and logged  by the processor
        assert len(sentry_client.events) == 0
        assert len(caplogpp.records) == 0

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock
from unittest.mock import ANY

from fillmore.test import diff_structure
from markus.testing import MetricsMock
import pytest

from socorro import settings
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.processor.processor_app import ProcessorApp, count_sentry_scrub_error


def sequencer(*args):
    def foo(*fargs, **fkwargs):
        yield from args

    return foo


class FakeCrashQueue:
    def new_crashes(self):
        return sequencer(
            ((1,), {}),
            2,
            None,
            ((3,), {}),  # ensure both forms acceptable
        )()


@pytest.fixture
def processor_settings():
    with settings.override(
        QUEUE={
            "class": "socorro.tests.processor.test_processor_app.FakeCrashQueue",
        },
        CRASH_SOURCE={
            "class": "socorro.external.crashstorage_base.InMemoryCrashStorage",
        },
        CRASH_DESTINATIONS_ORDER=["dest1"],
        CRASH_DESTINATIONS={
            "dest1": {
                "class": "socorro.external.crashstorage_base.InMemoryCrashStorage",
            },
        },
    ):
        yield


def get_destination(app, destination_name):
    index = settings.CRASH_DESTINATIONS_ORDER.index(destination_name)
    return app.destinations[index]


class TestProcessorApp:
    def test_source_iterator(self, processor_settings):
        app = ProcessorApp()
        app._set_up_source_and_destination()

        queue = app.source_iterator()
        assert next(queue) == ((1,), {})
        assert next(queue) == ((2,), {})
        assert next(queue) is None
        assert next(queue) == ((3,), {})

    def test_heartbeat(self, sentry_helper):
        """Basic test to make sure it runs, captures metrics, and doesn't error out"""
        with sentry_helper.reuse() as sentry_client:
            with MetricsMock() as metricsmock:
                app = ProcessorApp()
                app.heartbeat()

                # Assert it emitted some metrics
                metricsmock.assert_gauge("processor.open_files")
                metricsmock.assert_gauge("processor.processes_by_type")
                metricsmock.assert_gauge("processor.processes_by_status")

                # Assert it didn't throw an exception
                assert len(sentry_client.envelopes) == 0

    def test_transform_success(self, processor_settings):
        app = ProcessorApp()
        app._set_up_source_and_destination()

        fake_raw_crash = {"raw": "1"}
        mocked_get_raw_crash = mock.Mock(return_value=fake_raw_crash)
        app.source.get_raw_crash = mocked_get_raw_crash

        fake_dumps = {"upload_file_minidump": "fake_dump_TEMPORARY.dump"}
        mocked_get_dumps_as_files = mock.Mock(return_value=fake_dumps)
        app.source.get_dumps_as_files = mocked_get_dumps_as_files

        fake_processed_crash = {"uuid": "9d8e7127-9d98-4d92-8ab1-065982200317"}
        mocked_get_processed_crash = mock.Mock(return_value=fake_processed_crash)
        app.source.get_processed_crash = mocked_get_processed_crash

        mocked_process_crash = mock.Mock(return_value={"processed": "1"})
        app.pipeline.process_crash = mocked_process_crash
        app.destinations[0].save_processed_crash = mock.Mock()
        finished_func = mock.Mock()

        # the call being tested
        app.transform("17", finished_func)

        # test results
        app.source.get_raw_crash.assert_called_with("17")
        app.pipeline.process_crash.assert_called_with(
            ruleset_name="default",
            raw_crash=fake_raw_crash,
            dumps=fake_dumps,
            processed_crash=fake_processed_crash,
            # FIXME(willkg): testing this is tricky--we'd have to mock
            # TemporaryDirectory
            tmpdir=ANY,
        )
        app.destinations[0].save_processed_crash.assert_called_with(
            {"raw": "1"}, {"processed": "1"}
        )
        assert finished_func.call_count == 1

    def test_transform_crash_id_missing(self, processor_settings):
        app = ProcessorApp()
        app._set_up_source_and_destination()

        mocked_get_raw_crash = mock.Mock(side_effect=CrashIDNotFound(17))
        app.source.get_raw_crash = mocked_get_raw_crash

        mocked_reject_raw_crash = mock.Mock()
        app.pipeline.reject_raw_crash = mocked_reject_raw_crash

        finished_func = mock.Mock()

        app.transform("17", finished_func)
        app.source.get_raw_crash.assert_called_with("17")
        app.pipeline.reject_raw_crash.assert_called_with(
            "17", "crash cannot be found in raw crash storage"
        )
        assert finished_func.call_count == 1

    def test_transform_unexpected_exception(self, processor_settings):
        app = ProcessorApp()
        app._set_up_source_and_destination()
        mocked_get_raw_crash = mock.Mock(side_effect=Exception("bummer"))
        app.source.get_raw_crash = mocked_get_raw_crash

        mocked_reject_raw_crash = mock.Mock()
        app.pipeline.reject_raw_crash = mocked_reject_raw_crash

        finished_func = mock.Mock()

        app.transform("17", finished_func)
        app.source.get_raw_crash.assert_called_with("17")
        app.pipeline.reject_raw_crash.assert_called_with(
            "17", "error in loading: bummer"
        )
        assert finished_func.call_count == 1


# NOTE(willkg): If this changes, we should update it and look for new things that should
# be scrubbed. Use ANY for things that change between tests like timestamps, source code
# data (line numbers, file names, post/pre_context), event ids, build ids, versions,
# etc.
TRANSFORM_GET_ERROR = {
    "breadcrumbs": ANY,
    "contexts": {
        "runtime": {
            "build": ANY,
            "name": "CPython",
            "version": ANY,
        },
        "trace": {
            "parent_span_id": None,
            "span_id": ANY,
            "trace_id": ANY,
        },
    },
    "environment": "production",
    "event_id": ANY,
    "exception": {
        "values": [
            {
                "mechanism": {"handled": True, "type": "generic"},
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
                            "abs_path": "/usr/local/lib/python3.11/unittest/mock.py",
                            "context_line": ANY,
                            "filename": "unittest/mock.py",
                            "function": "__call__",
                            "lineno": ANY,
                            "module": "unittest.mock",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/usr/local/lib/python3.11/unittest/mock.py",
                            "context_line": ANY,
                            "filename": "unittest/mock.py",
                            "function": "_mock_call",
                            "lineno": ANY,
                            "module": "unittest.mock",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/usr/local/lib/python3.11/unittest/mock.py",
                            "context_line": ANY,
                            "filename": "unittest/mock.py",
                            "function": "_execute_mock_call",
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
    "extra": {"crash_id": "930b08ba-e425-49bf-adbd-7c9172220721", "ruleset": "default"},
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
        "packages": [{"name": "pypi:sentry-sdk", "version": ANY}],
        "version": ANY,
    },
    "server_name": ANY,
    "timestamp": ANY,
    "transaction_info": {},
}


def test_transform_get_error(processor_settings, sentry_helper, caplogpp):
    caplogpp.set_level("DEBUG")

    # Set up a processor and mock .get_raw_crash() to raise an exception
    app = ProcessorApp()
    app._set_up_sentry()
    app._set_up_source_and_destination()

    expected_exception = ValueError("simulated error")
    mocked_get_raw_crash = mock.Mock(side_effect=expected_exception)
    app.source.get_raw_crash = mocked_get_raw_crash

    crash_id = "930b08ba-e425-49bf-adbd-7c9172220721"

    with sentry_helper.reuse() as sentry_client:
        # The processor catches all exceptions from .get_raw_crash() and
        # .get_dumps_as_files(), so there's nothing we need to catch here
        app.transform(crash_id)

        (event,) = sentry_client.envelope_payloads

        # Assert that the event is what we expected
        differences = diff_structure(event, TRANSFORM_GET_ERROR)
        assert differences == []

        # Assert that the logger logged the appropriate thing
        logging_msgs = [rec.message for rec in caplogpp.records]
        assert (
            f"error: crash id {crash_id}: ValueError('simulated error')" in logging_msgs
        )


def test_count_sentry_scrub_error():
    with MetricsMock() as metricsmock:
        metricsmock.clear_records()
        count_sentry_scrub_error("foo")
        metricsmock.assert_incr("processor.sentry_scrub_error", value=1)


def test_transform_save_error(processor_settings, sentry_helper, caplogpp, tmp_path):
    with settings.override(TEMPORARY_PATH=str(tmp_path)):
        caplogpp.set_level("DEBUG")

        # Set up a processor and mock .save_processed_crash() to raise an exception
        app = ProcessorApp()
        app._set_up_sentry()
        app._set_up_source_and_destination()

        # Truncate the rulesets--we're not testing the pipeline here
        app.pipeline.rulesets = {}

        # Clear all the logging up to this point
        caplogpp.clear()

        # Set up crash storage
        crash_id = "930b08ba-e425-49bf-adbd-7c9172220721"
        raw_crash = {
            "uuid": crash_id,
            "ProductName": "Firefox",
        }
        app.source.save_raw_crash(crash_id=crash_id, raw_crash=raw_crash, dumps={})

        # Mock the destination to throw an error
        expected_exception = ValueError("simulated error")
        mocked_save_processed_crash = mock.Mock(side_effect=expected_exception)
        app.destinations[0].save_processed_crash = mocked_save_processed_crash

        with sentry_helper.reuse() as sentry_client:
            # Run .transform() and make sure it raises the ValueError
            with pytest.raises(ValueError):
                app.transform(crash_id)

            # Assert that the exception was not sent to Sentry and not logged at this
            # point--it gets caught and logged  by the processor
            assert len(sentry_client.envelopes) == 0

            # Assert what got logged. It should be all the messages except the last
            # "completed" one because this kicked up a ValueError in saving
            messages = [record.message for record in caplogpp.records]
            assert messages == [
                "starting 930b08ba-e425-49bf-adbd-7c9172220721 with default",
                "fetching data 930b08ba-e425-49bf-adbd-7c9172220721",
                "processing 930b08ba-e425-49bf-adbd-7c9172220721",
                "saving 930b08ba-e425-49bf-adbd-7c9172220721",
                (
                    "error: crash id 930b08ba-e425-49bf-adbd-7c9172220721: "
                    + "ValueError('simulated error') (dest1)"
                ),
            ]

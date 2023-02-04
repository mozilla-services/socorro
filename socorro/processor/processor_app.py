#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The processor app converts raw crashes into processed crashes.

It uses a fetch/transform/save model.

1. fetch: a queue class determines which crash report to process next and
   crash storage fetches the data from a crash storage source
2. transform: a pipeline class runs the crash report through a set of
   processing rules which results in a processed crash
3. save: crash storage saves the data to crash storage destinations

"""

from contextlib import suppress
from functools import partial
import os
import signal
import sys
import tempfile
import time

from configman import Namespace
from configman.converters import class_converter
from fillmore.libsentry import set_up_sentry
from fillmore.scrubber import Scrubber, SCRUB_RULES_DEFAULT
import markus
import sentry_sdk
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.boto3 import Boto3Integration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

from socorro.app.socorro_app import App
from socorro.external.crashstorage_base import CrashIDNotFound, PolyStorageError
from socorro.lib.libdatetime import isoformat_to_time
from socorro.lib.libdockerflow import get_release_name
from socorro.lib.task_manager import respond_to_SIGTERM


CONFIG_DEFAULTS = {
    "always_ignore_mismatches": True,
    "queue": {"crashqueue_class": "socorro.external.sqs.crashqueue.SQSCrashQueue"},
    "source": {
        "benchmark_tag": "BotoS3CrashStorage",
        "crashstorage_class": "socorro.external.crashstorage_base.BenchmarkingCrashStorage",
        "wrapped_crashstore": "socorro.external.boto.crashstorage.BotoS3CrashStorage",
    },
    "destination": {
        "crashstorage_class": "socorro.external.crashstorage_base.PolyCrashStorage",
        # Each key in this list corresponds to a key in this dict containing
        # a crash storage config.
        "storage_namespaces": ",".join(["s3", "elasticsearch", "statsd", "telemetry"]),
        "s3": {
            "active_list": "save_processed_crash",
            "benchmark_tag": "BotoS3CrashStorage",
            "crashstorage_class": "socorro.external.crashstorage_base.MetricsBenchmarkingWrapper",
            "metrics_prefix": "processor.s3",
            "wrapped_object_class": "socorro.external.boto.crashstorage.BotoS3CrashStorage",
        },
        "elasticsearch": {
            "active_list": "save_processed_crash",
            "benchmark_tag": "ElasticsearchCrashStorage",
            "crashstorage_class": "socorro.external.crashstorage_base.MetricsBenchmarkingWrapper",
            "metrics_prefix": "processor.es",
            "wrapped_object_class": "socorro.external.es.crashstorage.ESCrashStorage",
        },
        "statsd": {
            "active_list": "save_processed_crash",
            "crashstorage_class": "socorro.external.crashstorage_base.MetricsCounter",
            "metrics_prefix": "processor",
        },
        "telemetry": {
            "active_list": "save_processed_crash",
            "bucket_name": "org-mozilla-telemetry-crashes",
            "crashstorage_class": "socorro.external.crashstorage_base.MetricsBenchmarkingWrapper",
            "metrics_prefix": "processor.telemetry",
            "wrapped_object_class": (
                "socorro.external.boto.crashstorage.TelemetryBotoS3CrashStorage"
            ),
        },
    },
    "companion_process": {
        "companion_class": "socorro.processor.symbol_cache_manager.SymbolLRUCacheManager",
        "symbol_cache_size": "40G",
        "verbosity": 0,
    },
    "producer_consumer": {"maximum_queue_size": 8, "number_of_threads": 4},
    "resource": {
        "boto": {"prefix": "", "boto_metrics_prefix": "processor.s3"},
    },
}


METRICS = markus.get_metrics("processor")


def count_sentry_scrub_error(msg):
    METRICS.incr("sentry_scrub_error", 1)


class ProcessorApp(App):
    """Configman app that transforms raw crashes into processed crashes."""

    app_name = "processor"
    app_version = "3.0"
    app_description = __doc__
    config_defaults = CONFIG_DEFAULTS

    required_config = Namespace()

    # The queue class has an iterator for work items to be processed.
    required_config.namespace("queue")
    required_config.queue.add_option(
        "crashqueue_class",
        doc="an iterable that will stream work items for processing",
        default="",
        from_string_converter=class_converter,
    )

    # The source class has methods to fetch the data to use.
    required_config.source = Namespace()
    required_config.source.add_option(
        "crashstorage_class",
        doc="the source storage class",
        default="socorro.external.fs.crashstorage.FSPermanentStorage",
        from_string_converter=class_converter,
    )

    # The destination class has methods to save the transformed data to storage.
    required_config.destination = Namespace()
    required_config.destination.add_option(
        "crashstorage_class",
        doc="the destination storage class",
        default="socorro.external.fs.crashstorage.FSPermanentStorage",
        from_string_converter=class_converter,
    )

    required_config.producer_consumer = Namespace()
    required_config.producer_consumer.add_option(
        "producer_consumer_class",
        doc="the class implements a threaded producer consumer queue",
        default="socorro.lib.threaded_task_manager.ThreadedTaskManager",
        from_string_converter=class_converter,
    )

    # The processor is the pipeline that transforms raw crashes into
    # processed crashes.
    required_config.namespace("processor")
    required_config.processor.add_option(
        "processor_class",
        doc="the class that transforms raw crashes into processed crashes",
        default="socorro.processor.processor_pipeline.ProcessorPipeline",
        from_string_converter=class_converter,
    )
    required_config.processor.add_option(
        "temporary_path",
        doc=(
            "a local filesystem path that can be used as a workspace for processing "
            + "rules"
        ),
        default=os.path.join(tempfile.gettempdir(), "workspace"),
    )

    # The companion_process runs alongside the processor and cleans up
    # the symbol lru cache.
    required_config.namespace("companion_process")
    required_config.companion_process.add_option(
        "companion_class",
        doc="a classname that runs a process in parallel with the processor",
        default="",
        # default='socorro.processor.symbol_cache_manager.SymbolLRUCacheManager',
        from_string_converter=class_converter,
    )

    @classmethod
    def configure_sentry(cls, basedir, host_id, sentry_dsn):
        release = get_release_name(basedir)
        scrubber = Scrubber(
            rules=SCRUB_RULES_DEFAULT,
            error_handler=count_sentry_scrub_error,
        )
        set_up_sentry(
            sentry_dsn=sentry_dsn,
            release=release,
            host_id=host_id,
            # Disable frame-local variables
            with_locals=False,
            # Disable request data from being added to Sentry events
            request_bodies="never",
            # All integrations should be intentionally enabled
            default_integrations=False,
            integrations=[
                AtexitIntegration(),
                Boto3Integration(),
                ExcepthookIntegration(),
                DedupeIntegration(),
                StdlibIntegration(),
                ModulesIntegration(),
                ThreadingIntegration(),
            ],
            # Scrub sensitive data
            before_send=scrubber,
        )

    def _basic_iterator(self):
        """Yields an infinite list of processing tasks."""
        try:
            for x in self.queue.new_crashes():
                if x is None or isinstance(x, tuple):
                    yield x
                else:
                    yield ((x,), {})
            yield None
        except Exception as exc:
            # NOTE(willkg): Queue code should not be throwing unhandled exceptions. If
            # it does, we should send it to sentry, log it, and then re-raise it so the
            # caller can deal with it and/or crash
            sentry_sdk.capture_exception(exc)
            self.logger.exception("error in crash id iterator")
            raise

    def source_iterator(self):
        """Iterate infinitely yielding tasks."""
        while True:
            yield from self._basic_iterator()

    def transform(self, task, finished_func=(lambda: None)):
        try:
            if ":" in task:
                crash_id, ruleset_name = task.split(":", 1)
            else:
                crash_id, ruleset_name = task, "default"

            # Set up metrics and sentry scopes
            with METRICS.timer("process_crash", tags=[f"ruleset:{ruleset_name}"]):
                with sentry_sdk.push_scope() as scope:
                    scope.set_extra("crash_id", crash_id)
                    scope.set_extra("ruleset", ruleset_name)

                    # Create temporary directory context
                    with tempfile.TemporaryDirectory(dir=self.temporary_path) as tmpdir:
                        # Process the crash report
                        self.process_crash(
                            crash_id=crash_id,
                            ruleset_name=ruleset_name,
                            tmpdir=tmpdir,
                        )

        finally:
            # no matter what causes this method to end, we need to make sure
            # that the finished_func gets called. If the new crash source is
            # Pub/Sub, this is what removes the job from the queue.
            try:
                finished_func()
            except Exception:
                # when run in a thread, a failure here is not a problem, but if
                # we're running all in the same thread, a failure here could
                # derail the the whole processor. Best just log the problem
                # so that we can continue.
                self.logger.exception(f"Error calling finishing_func() on {task}")

    def process_crash(self, crash_id, ruleset_name, tmpdir):
        """Processed crash data using a specified ruleset into a processed crash.

        :arg crash_id: unique identifier for the crash report used to fetch the data and
            save the processed data
        :arg ruleset_name: the name of the ruleset to process the crash report with
        :arg tmpdir: the temporary directory to use as a workspace

        """
        self.logger.info("starting %s with %s", crash_id, ruleset_name)

        self.logger.debug("fetching data %s", crash_id)
        # Fetch crash annotations and dumps
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
            dumps = self.source.get_dumps_as_files(crash_id, tmpdir)
        except CrashIDNotFound:
            # If the crash isn't found, we just reject it--no need to capture
            # errors here
            self.processor.reject_raw_crash(
                crash_id, "crash cannot be found in raw crash storage"
            )
            return
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            self.logger.exception("error: crash id %s: %r", crash_id, exc)
            self.processor.reject_raw_crash(crash_id, f"error in loading: {exc}")
            return

        # Fetch processed crash data--there won't be any if this crash hasn't
        # been processed, yet
        try:
            processed_crash = self.source.get_processed(crash_id)
            new_crash = False
        except CrashIDNotFound:
            new_crash = True
            processed_crash = {}

        # Process the crash to generate a processed crash
        self.logger.debug("processing %s", crash_id)
        processed_crash = self.processor.process_crash(
            ruleset_name=ruleset_name,
            raw_crash=raw_crash,
            dumps=dumps,
            processed_crash=processed_crash,
            tmpdir=tmpdir,
        )

        # Save data to crash storage
        try:
            self.logger.debug("saving %s", crash_id)
            self.destination.save_processed_crash(raw_crash, processed_crash)
            self.logger.info("saved %s", crash_id)
        except PolyStorageError as poly_storage_error:
            # Capture and log the exceptions raised by storage backends
            for storage_error in poly_storage_error:
                sentry_sdk.capture_exception(storage_error)
                self.logger.error("error: crash id %s: %r", crash_id, storage_error)

            # Re-raise the original exception with the correct traceback
            raise

        if ruleset_name == "default" and new_crash:
            # Capture the total time for ingestion covering when the crash report
            # was collected (submitted_timestamp) to the end of processing (now). We
            # only want to do this for crash reports being processed for the first
            # time.
            collected = raw_crash.get("submitted_timestamp", None)
            if collected:
                delta = time.time() - isoformat_to_time(collected)
                delta = delta * 1000
                METRICS.timing("ingestion_timing", value=delta)

        self.logger.info("completed %s", crash_id)

    def _setup_source_and_destination(self):
        """Instantiate classes necessary for processing."""
        self.queue = self.config.queue.crashqueue_class(
            self.config.queue,
            namespace=self.app_instance_name,
        )
        self.source = self.config.source.crashstorage_class(
            self.config.source,
            namespace=self.app_name,
        )
        self.destination = self.config.destination.crashstorage_class(
            self.config.destination,
            namespace=self.app_name,
        )

        if self.config.companion_process.companion_class:
            self.companion_process = self.config.companion_process.companion_class(
                self.config.companion_process
            )
        else:
            self.companion_process = None

        self.processor = self.config.processor.processor_class(
            config=self.config.processor, host_id=self.app_instance_name
        )

        self.temporary_path = self.config.processor.temporary_path
        os.makedirs(self.temporary_path, exist_ok=True)

    def _setup_task_manager(self):
        """instantiate the threaded task manager to run the producer/consumer
        queue that is the heart of the processor."""
        self.logger.info("installing signal handers")
        # Set up the signal handler for dealing with SIGTERM. The target should be this
        # app instance so the signal handler can reach in and set the quit flag to be
        # True. See the 'respond_to_SIGTERM' method for the more information
        respond_to_SIGTERM_with_logging = partial(respond_to_SIGTERM, target=self)
        signal.signal(signal.SIGTERM, respond_to_SIGTERM_with_logging)

        self.task_manager = self.config.producer_consumer.producer_consumer_class(
            self.config.producer_consumer,
            job_source_iterator=self.source_iterator,
            task_func=self.transform,
        )

    def close(self):
        """Clean up the processor on shutdown."""
        with suppress(AttributeError):
            self.queue.close()

        with suppress(AttributeError):
            self.source.close()

        with suppress(AttributeError):
            self.destination.close()

        with suppress(AttributeError):
            self.companion_process.close()

        with suppress(AttributeError):
            self.processor.close()

    def main(self):
        """Main routine

        Sets up the signal handlers, the source and destination crashstorage systems at
        the theaded task manager. That starts a flock of threads that are ready to
        shepherd tasks from the source to the destination.

        """

        self._setup_task_manager()
        self._setup_source_and_destination()
        self.task_manager.blocking_start()
        self.close()
        self.logger.info("done.")


if __name__ == "__main__":
    sys.exit(ProcessorApp.run())

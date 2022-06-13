#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The processor app converts raw crashes into processed crashes."""

import os
import sys
import time

from configman import Namespace
from configman.converters import class_converter
from configman.dotdict import DotDict
import markus

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp
from socorro.external.crashstorage_base import CrashIDNotFound, PolyStorageError
from socorro.lib import sentry_client
from socorro.lib.libdatetime import isoformat_to_time
from socorro.lib.util import dotdict_to_dict


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
            "es_redactor": {
                "forbidden_keys": ", ".join(
                    [
                        # NOTE(willkg): "java_stack_trace_full" messes the Elasticsearch
                        # crashstorage up and causes errors. We can remove it in
                        # August 2020. Bug #1619638
                        "java_stack_trace_full",
                        "memory_report",
                        "upload_file_minidump_browser.json_dump",
                        "upload_file_minidump_flash1.json_dump",
                        "upload_file_minidump_flash2.json_dump",
                    ]
                )
            },
            "metrics_prefix": "processor.es",
            "wrapped_object_class": (
                "socorro.external.es.crashstorage.ESCrashStorageRedactedJsonDump"
            ),
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


class ProcessorApp(FetchTransformSaveApp):
    """Configman app that transforms raw crashes into processed crashes."""

    app_name = "processor"
    app_version = "3.0"
    app_description = __doc__
    config_defaults = CONFIG_DEFAULTS

    required_config = Namespace()

    # The processor is the pipeline that transforms raw crashes into
    # processed crashes.
    required_config.namespace("processor")
    required_config.processor.add_option(
        "processor_class",
        doc="the class that transforms raw crashes into processed crashes",
        default="socorro.processor.processor_pipeline.ProcessorPipeline",
        from_string_converter=class_converter,
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

    def _capture_error(self, exc_info, crash_id=None):
        """Capture an error in sentry if able.

        :arg crash_id: a crash id
        :arg exc_info: the exc info as it comes from sys.exc_info()

        """
        extra = {}
        if crash_id:
            extra["crash_id"] = crash_id

        sentry_client.capture_error(self.logger, exc_info, extra=extra)

    def _basic_iterator(self):
        """Yields an infinite list of processing tasks."""
        try:
            yield from super()._basic_iterator()
        except Exception:
            self._capture_error(sys.exc_info())
            self.logger.warning("error in crashid iterator", exc_info=True)

            # NOTE(willkg): Queue code should not be throwing unhandled exceptions. If
            # we hit one, we should make sure it gets to sentry and then let the caller
            # deal with it
            raise

    def _transform(self, task):
        """Runs a transform on a task.

        The ``task`` passed in is in the form of CRASHID or CRASHID:RULESET.
        In the case of the former, it uses the default pipeline.

        """

        if ":" in task:
            crash_id, ruleset_name = task.split(":", 1)
        else:
            crash_id, ruleset_name = task, "default"

        with METRICS.timer("process_crash", tags=[f"ruleset:{ruleset_name}"]):
            self.process_crash(crash_id, ruleset_name)

    def process_crash(self, crash_id, ruleset_name):
        """Processed crash data using a specified ruleset into a processed crash.

        The ``crash_id`` is a key to fetch the raw crash data from the ``source``, the
        ``processor_class`` processes the crash and the processed crash is saved to the
        ``destination``.

        """
        # Fetch the raw crash data
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
            dumps = self.source.get_dumps_as_files(crash_id)
        except CrashIDNotFound:
            # If the crash isn't found, we just reject it--no need to capture
            # errors here
            self.processor.reject_raw_crash(
                crash_id, "crash cannot be found in raw crash storage"
            )
            return
        except Exception as x:
            # We don't know what this error is, so we should capture it
            self._capture_error(sys.exc_info(), crash_id)
            self.logger.warning("error loading crash %s", crash_id, exc_info=True)
            self.processor.reject_raw_crash(crash_id, "error in loading: %s" % x)
            return

        # Fetch processed crash data--there won't be any if this crash hasn't
        # been processed, yet
        try:
            processed_crash = self.source.get_unredacted_processed(crash_id)
            new_crash = False
        except CrashIDNotFound:
            new_crash = True
            processed_crash = DotDict()

        # Process the crash and remove any temporary artifacts from disk
        try:
            # Process the crash to generate a processed crash
            processed_crash = self.processor.process_crash(
                ruleset_name, raw_crash, dumps, processed_crash
            )

            # Convert the raw and processed crashes from DotDict into Python standard
            # data structures
            raw_crash = dotdict_to_dict(raw_crash)
            processed_crash = dotdict_to_dict(processed_crash)

            self.destination.save_processed_crash(raw_crash, processed_crash)
            self.logger.info("saved - %s", crash_id)
        except PolyStorageError as poly_storage_error:
            # Capture and log the exceptions raised by storage backends
            for storage_error in poly_storage_error:
                self._capture_error(storage_error, crash_id)
            self.logger.warning("error in processing or saving crash %s", crash_id)

            # Re-raise the original exception with the correct traceback
            raise

        finally:
            # Clean up any dump files saved to the file system
            for a_dump_pathname in dumps.values():
                if "TEMPORARY" in a_dump_pathname:
                    try:
                        os.unlink(a_dump_pathname)
                    except OSError as x:
                        self.logger.info("deletion of dump failed: %s", x)

        if ruleset_name == "default" and new_crash:
            # Capture the total time for ingestion covering when the crash report was
            # collected (submitted_timestamp) to the end of processing (now). We only
            # want to do this for crash reports being processed for the first time.
            collected = raw_crash.get("submitted_timestamp", None)
            if collected:
                delta = time.time() - isoformat_to_time(collected)
                delta = delta * 1000
                METRICS.timing("ingestion_timing", value=delta)

    def _setup_source_and_destination(self):
        """Instantiate classes necessary for processing."""
        super()._setup_source_and_destination()
        if self.config.companion_process.companion_class:
            self.companion_process = self.config.companion_process.companion_class(
                self.config.companion_process
            )
        else:
            self.companion_process = None

        self.config.processor_name = self.app_instance_name

        # This function will be called by the MainThread periodically
        # while the threaded_task_manager processes crashes.
        self.waiting_func = None

        self.processor = self.config.processor.processor_class(self.config.processor)

    def close(self):
        """Clean up the processor on shutdown."""
        super().close()
        try:
            self.companion_process.close()
        except AttributeError:
            # There is either no companion or it doesn't have a close method
            # we can skip on
            pass
        try:
            self.processor.close()
        except AttributeError:
            # The processor implementation does not have a close method
            # we can blithely skip on
            pass


if __name__ == "__main__":
    sys.exit(ProcessorApp.run())

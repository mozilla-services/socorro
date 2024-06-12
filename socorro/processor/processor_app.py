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
import logging
import os
from pathlib import Path
import signal
import tempfile
import time

from fillmore.libsentry import set_up_sentry
from fillmore.scrubber import Scrubber, SCRUB_RULES_DEFAULT
import psutil
import sentry_sdk
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.boto3 import Boto3Integration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

from socorro import settings
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.libclass import build_instance, build_instance_from_settings
from socorro.libmarkus import set_up_metrics, METRICS
from socorro.lib.libdatetime import isoformat_to_time
from socorro.lib.libdockerflow import get_release_name, get_version_info
from socorro.lib.liblogging import set_up_logging
from socorro.lib.task_manager import respond_to_SIGTERM


def count_sentry_scrub_error(msg):
    METRICS.incr("processor.sentry_scrub_error", value=1, tags=["service:processor"])


class ProcessorApp:
    """App that transforms raw crashes into processed crashes."""

    def __init__(self):
        self.basedir = Path(__file__).resolve().parent.parent.parent
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def log_config(self):
        version_info = get_version_info(self.basedir)
        data = ", ".join(
            [f"{key!r}: {val!r}" for key, val in sorted(version_info.items())]
        )
        data = data or "no version data"
        self.logger.info("version.json: %s", data)
        settings.log_settings(logger=self.logger)

    def _set_up_sentry(self):
        if not settings.SENTRY_DSN:
            return

        release = get_release_name(self.basedir)
        scrubber = Scrubber(
            rules=SCRUB_RULES_DEFAULT,
            error_handler=count_sentry_scrub_error,
        )
        set_up_sentry(
            sentry_dsn=settings.SENTRY_DSN,
            release=release,
            host_id=settings.HOSTNAME,
            # Disable frame-local variables
            include_local_variables=False,
            # Disable request data from being added to Sentry events
            max_request_body_size="never",
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
            with METRICS.timer(
                "processor.process_crash", tags=[f"ruleset:{ruleset_name}"]
            ):
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
                self.logger.exception("Error calling finishing_func() on %s", task)

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
            self.pipeline.reject_raw_crash(
                crash_id, "crash cannot be found in raw crash storage"
            )
            return
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            self.logger.exception("error: crash id %s: %r", crash_id, exc)
            self.pipeline.reject_raw_crash(crash_id, f"error in loading: {exc}")
            return

        # Fetch processed crash data--there won't be any if this crash hasn't
        # been processed, yet
        try:
            processed_crash = self.source.get_processed_crash(crash_id)
            new_crash = False
        except CrashIDNotFound:
            new_crash = True
            processed_crash = {}

        # Process the crash to generate a processed crash
        self.logger.debug("processing %s", crash_id)
        processed_crash = self.pipeline.process_crash(
            ruleset_name=ruleset_name,
            raw_crash=raw_crash,
            dumps=dumps,
            processed_crash=processed_crash,
            tmpdir=tmpdir,
        )

        # Save data to crash storage destinations
        self.logger.debug("saving %s", crash_id)
        for dest in self.destinations:
            try:
                with METRICS.timer(
                    f"processor.{dest.crash_destination_name}.save_processed_crash"
                ):
                    dest.save_processed_crash(raw_crash, processed_crash)
            except Exception as storage_error:
                self.logger.error(
                    "error: crash id %s: %r (%s)",
                    crash_id,
                    storage_error,
                    dest.crash_destination_name,
                )
                # Re-raise the original exception with the correct traceback
                raise

        METRICS.incr("processor.save_processed_crash")

        self.logger.info("saved %s", crash_id)

        if ruleset_name == "default" and new_crash:
            # Capture the total time for ingestion covering when the crash report
            # was collected (submitted_timestamp) to the end of processing (now). We
            # only want to do this for crash reports being processed for the first
            # time.
            collected = raw_crash.get("submitted_timestamp", None)
            if collected:
                delta = time.time() - isoformat_to_time(collected)
                delta = delta * 1000
                METRICS.timing("processor.ingestion_timing", value=delta)

        self.logger.info("completed %s", crash_id)

    def _set_up_source_and_destination(self):
        """Instantiate classes necessary for processing."""
        self.queue = build_instance_from_settings(settings.QUEUE)
        self.source = build_instance_from_settings(settings.CRASH_SOURCE)
        destinations = []
        for key in settings.CRASH_DESTINATIONS_ORDER:
            dest_obj = build_instance_from_settings(settings.CRASH_DESTINATIONS[key])
            dest_obj.crash_destination_name = key
            destinations.append(dest_obj)
        self.destinations = destinations

        self.pipeline = build_instance_from_settings(settings.PROCESSOR["pipeline"])

        self.temporary_path = settings.PROCESSOR["temporary_path"]
        os.makedirs(self.temporary_path, exist_ok=True)

    def _set_up_task_manager(self):
        """Create and set up task manager."""
        self.logger.info("installing signal handers")
        # Set up the signal handler for dealing with SIGTERM. The target should be this
        # app instance so the signal handler can reach in and set the quit flag to be
        # True. See the 'respond_to_SIGTERM' method for the more information
        respond_to_SIGTERM_with_logging = partial(respond_to_SIGTERM, target=self)
        signal.signal(signal.SIGTERM, respond_to_SIGTERM_with_logging)

        # Create task manager
        manager_class = settings.PROCESSOR["task_manager"]["class"]
        manager_settings = settings.PROCESSOR["task_manager"]["options"]
        manager_settings.update(
            {
                "job_source_iterator": self.source_iterator,
                "heartbeat_func": self.heartbeat,
                "task_func": self.transform,
            }
        )
        self.task_manager = build_instance(
            class_path=manager_class, kwargs=manager_settings
        )

    def heartbeat(self):
        """Runs once a second from the main thread.

        Note: If this raises an exception, it could kill the process or put it in a
        weird state.

        """
        try:
            processes_by_type = {}
            processes_by_status = {}
            open_files = 0
            for proc in psutil.process_iter(["cmdline", "status", "open_files"]):
                try:
                    # NOTE(willkg): This is all intertwined with exactly how we run the
                    # processor in a Docker container. If we ever make changes to that, this
                    # will change, too. However, even if we never update this, seeing
                    # "zombie" and "orphaned" as process statuses or seeing lots of
                    # processes as a type will be really fishy and suggestive that evil is a
                    # foot.
                    cmdline = proc.cmdline() or ["unknown"]

                    if cmdline[0] in ["/bin/sh", "/bin/bash"]:
                        proc_type = "shell"
                    elif cmdline[0] in ["python", "/usr/local/bin/python"]:
                        proc_type = "python"
                    elif "stackwalk" in cmdline[0]:
                        proc_type = "stackwalker"
                    else:
                        proc_type = "other"

                    open_files_count = len(proc.open_files())
                    proc_status = proc.status()

                except psutil.Error:
                    # For any psutil error, we want to track that we saw a process, but
                    # the details don't matter
                    proc_type = "unknown"
                    proc_status = "unknown"
                    open_files_count = 0

                processes_by_type[proc_type] = processes_by_type.get(proc_type, 0) + 1
                processes_by_status[proc_status] = (
                    processes_by_status.get(proc_status, 0) + 1
                )
                open_files += open_files_count

            METRICS.gauge("processor.open_files", open_files)
            for proc_type, val in processes_by_type.items():
                METRICS.gauge(
                    "processor.processes_by_type", val, tags=[f"proctype:{proc_type}"]
                )
            for status, val in processes_by_status.items():
                METRICS.gauge(
                    "processor.processes_by_status", val, tags=[f"procstatus:{status}"]
                )

        except Exception as exc:
            sentry_sdk.capture_exception(exc)

    def close(self):
        """Clean up the processor on shutdown."""
        with suppress(AttributeError):
            self.queue.close()

        with suppress(AttributeError):
            self.source.close()

        with suppress(AttributeError):
            self.destination.close()

        with suppress(AttributeError):
            self.pipeline.close()

    def set_up(self):
        """Set up processor process scaffolding"""
        set_up_logging(
            local_dev_env=settings.LOCAL_DEV_ENV,
            logging_level=settings.LOGGING_LEVEL,
            hostname=settings.HOSTNAME,
        )
        self.log_config()

        set_up_metrics(
            statsd_host=settings.STATSD_HOST,
            statsd_port=settings.STATSD_PORT,
            hostname=settings.HOSTNAME,
            debug=settings.LOCAL_DEV_ENV,
        )
        self._set_up_sentry()

        self._set_up_task_manager()
        self._set_up_source_and_destination()

    def main(self):
        """Run task manager blocking_start and then close when done"""
        self.task_manager.blocking_start()
        self.close()


def main():
    app = ProcessorApp()
    app.set_up()
    app.main()


if __name__ == "__main__":
    # NOTE(willkg): we need to do this so that the processor app logger isn't `__main__`
    # which causes problems when logging
    from socorro.processor import processor_app

    processor_app.main()

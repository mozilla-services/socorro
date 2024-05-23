# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import contextlib
import datetime
import logging
import sys
import time
import traceback

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from crashstats.cron import (
    JOBS,
    MAX_ONGOING,
    ERROR_RETRY_TIME,
    DEFAULT_FREQUENCY,
    JobNotFoundError,
    OngoingJobError,
)
from crashstats.cron.models import Job, Log
from crashstats.cron.utils import (
    convert_frequency,
    convert_time,
    format_datetime,
    get_matching_job_specs,
    get_run_times,
    time_to_run,
)
from socorro.libmarkus import METRICS


logger = logging.getLogger("crashstats.cron")


class Command(BaseCommand):
    help = "Run cron jobs."

    def add_arguments(self, parser):
        parser.add_argument("--job", help="Run a specific job.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force a job to run even if it is not time.",
        )
        parser.add_argument(
            "--job-arg",
            action="append",
            help="Cron job command arguments in name=value format.",
        )

    def handle(self, **options):
        """Execute cronrun command."""
        if options["job"]:
            job_args = options.get("job_arg") or []
            # Re-add the -- because they're optional arguments; note that this
            # doesn't support positional arguments
            cmd_args = ["--%s" % arg for arg in job_args]
            return self.cmd_run_one(options["job"], options["force"], cmd_args)
        else:
            return self.cmd_run_all()

    @contextlib.contextmanager
    def stdout_to_logger(self, cmd):
        class StdoutLogger:
            def write(self, txt):
                logger.info("%s: %s" % (cmd, txt.strip()))

        stdout = self.stdout
        self.stdout = StdoutLogger()
        yield
        self.stdout = stdout

    def cmd_run_all(self):
        logger.info("Running all jobs...")
        for job_spec in JOBS:
            try:
                self._run_one(job_spec, cmd_args=job_spec.get("cmd_args", []))
            except OngoingJobError:
                # If the job is already running somehow, then move on
                logger.error("OngoingJobError: %s", job_spec.get("cmd", "no command"))
                pass
        return 0

    def cmd_run_one(self, description, force=False, cmd_args=None):
        job_spec = get_matching_job_specs(description)
        if job_spec:
            return self._run_one(job_spec, force=force, cmd_args=cmd_args)
        raise JobNotFoundError(description)

    def _run_one(self, job_spec, force=False, cmd_args=None):
        """Run a single job.

        :arg job_spec: job spec dict
        :arg force: forces the job to run even if it's not time to run
        :arg cmd_args: list of "--key=val" positional args as you would pass
            them on a command line

        """
        cmd_args = cmd_args or []
        cmd = job_spec["cmd"]

        # Make sure we have a job record before trying to run anything
        job = Job.objects.get_or_create(app_name=cmd)[0]

        if force:
            # If we're forcing the job, just run it without the bookkeeping.
            return self._run_job(job_spec, *cmd_args)

        # Figure out whether this job should be run now
        seconds = convert_frequency(job_spec.get("frequency", DEFAULT_FREQUENCY))
        if not time_to_run(job_spec, job):
            logger.info("skipping %s: not time to run", cmd)
            return

        logger.info("about to run %s", cmd)

        now = timezone.now()
        start_time = None
        run_time = None

        with self.lock_job(job_spec["cmd"]):
            try:
                cmd_kwargs = {}
                last_success = job.last_success

                # Backfill jobs can have multiple run-times, so we iterate
                # through all possible ones until either we get them all done
                # or it dies
                for run_time in get_run_times(job_spec, job.last_success):
                    if job_spec.get("backfill", False):
                        # If "backfill" is in the spec, then we want to pass in
                        # run_time as an argument
                        cmd_kwargs["run_time"] = format_datetime(run_time)

                    if job_spec.get("last_success", False):
                        # If "last_success" is in the spec, we want to pass in
                        # the last_success as an argument
                        cmd_kwargs["last_success"] = format_datetime(last_success)

                    logger.info("running: %s %s %s", cmd, cmd_args, cmd_kwargs)

                    start_time = time.time()
                    self._run_job(job_spec, *cmd_args, **cmd_kwargs)
                    end_time = time.time()

                    logger.info("successfully ran %s on %s", cmd, run_time)
                    last_success = run_time

                    self._remember_success(cmd, last_success, end_time - start_time)

                    # Log each backfill task as a successful completion so that if
                    # one of them fails, we start at the failure date rather than
                    # all the way back at the beginning.
                    self._log_run(
                        cmd,
                        seconds,
                        job_spec.get("time"),
                        run_time,
                        now,
                    )

            except OngoingJobError:
                # Catch and raise this so it doesn't get handled by the Exception
                # handling
                raise

            except Exception:
                end_time = time.time()
                exc_type, exc_value, exc_tb = sys.exc_info()
                single_line_tb = "".join(
                    traceback.format_exception(*sys.exc_info())
                ).replace("\n", "\\n")

                logger.error(
                    "error when running %s (%s): %s", cmd, run_time, single_line_tb
                )
                self._remember_failure(
                    cmd, end_time - start_time, exc_type, exc_value, exc_tb
                )
                self._log_run(
                    cmd,
                    seconds,
                    job_spec.get("time"),
                    run_time,
                    now,
                    exc_type,
                    exc_value,
                    exc_tb,
                )

    def _run_job(self, job_spec, *cmd_args, **cmd_kwargs):
        """Run job with specified args."""
        with self.stdout_to_logger(job_spec["cmd"]):
            return call_command(
                job_spec["cmd"], *cmd_args, stdout=self.stdout, **cmd_kwargs
            )

    def _remember_success(self, cmd, success_date, duration):
        Log.objects.create(
            app_name=cmd, success=success_date, duration="%.5f" % duration
        )
        METRICS.gauge("cron.job_success_runtime", value=duration, tags=["job:%s" % cmd])

    def _remember_failure(self, cmd, duration, exc_type, exc_value, exc_tb):
        Log.objects.create(
            app_name=cmd,
            duration="%.5f" % duration,
            exc_type=repr(exc_type),
            exc_value=repr(exc_value),
            exc_traceback="".join(traceback.format_tb(exc_tb)),
        )
        METRICS.gauge("cron.job_failure_runtime", value=duration, tags=["job:%s" % cmd])

    @contextlib.contextmanager
    def lock_job(self, cmd):
        """Manage locking and unlocking a job.

        :raises OngoingJobError: if the job is currently running

        """
        now = timezone.now()

        # Try to lock the job
        results = Job.objects.filter(app_name=cmd, ongoing=None).update(ongoing=now)
        if results == 1:
            yield
            Job.objects.filter(app_name=cmd).update(ongoing=None)
            return

        # Didn't lock the job, so it's in use by something else; if it's been
        # going on for too long, let's try to lock it again
        job = Job.objects.filter(app_name=cmd).get()
        if (now - job.ongoing).seconds > MAX_ONGOING:
            results = Job.objects.filter(app_name=cmd, ongoing=job.ongoing).update(
                ongoing=now
            )
            if results == 1:
                yield
                Job.objects.filter(app_name=cmd).update(ongoing=None)
                return

        # Can't lock it, so raise an error
        raise OngoingJobError("%s: %s" % (job.app_name, job.ongoing))

    def _log_run(
        self,
        cmd,
        seconds,
        time_,
        last_success,
        now,
        exc_type=None,
        exc_value=None,
        exc_tb=None,
    ):
        job = Job.objects.get_or_create(app_name=cmd)[0]

        if not job.first_run:
            job.first_run = now
        job.last_run = now
        if last_success:
            job.last_success = last_success

        next_run = None
        if exc_type:
            # it errored, try very soon again
            next_run = now + datetime.timedelta(seconds=ERROR_RETRY_TIME)
        else:
            next_run = now + datetime.timedelta(seconds=seconds)
            if time_:
                hh, mm = convert_time(time_)
                next_run = next_run.replace(hour=hh, minute=mm, second=0, microsecond=0)
        job.next_run = next_run

        if exc_type:
            tb = "".join(traceback.format_tb(exc_tb))
            job.last_error = {
                "type": exc_type,
                "value": str(exc_value),
                "traceback": tb,
            }
            job.error_count = job.error_count + 1
        else:
            job.last_error = {}
            job.error_count = 0

        job.save()

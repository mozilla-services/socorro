# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import datetime
import logging
import re
import sys
import time
import traceback

import markus

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from crashstats.cron.models import Job, Log


logger = logging.getLogger('crashstats.crontabber')

metrics = markus.get_metrics('crontabber')


# NOTE(willkg): Times are in UTC. These are Django-based jobs. The other
# crontabber handles the jobs that haven't been converted, yet.
#
# NOTE(willkg): You can't have the same job in here twice with two different
# frequencies. If we ever need to do that, we'll need to stop using "cmd" as
# the key in the db.
3
# cmd, frequency, time, backfill
JOBS = [
    {
        # Test cron job
        'cmd': 'crontest',
        'frequency': '1d',
    },
]

# Map of cmd -> job_spec
JOBS_MAP = dict([(job_spec['cmd'], job_spec) for job_spec in JOBS])


# The maximum time we let a job go for before we declare it a zombie (in seconds)
MAX_ONGOING = 60 * 60 * 2


# Error retry time (in seconds)
ERROR_RETRY_TIME = 60


class FrequencyDefinitionError(Exception):
    pass


class JobNotFoundError(Exception):
    pass


class TimeDefinitionError(Exception):
    pass


class OngoingJobError(Exception):
    """Error raised when a job is currently running."""

    pass


FREQUENCY_RE = re.compile(r'^(\d+)([^\d])$')


def convert_frequency(value):
    """return the number of seconds that a certain frequency string represents.
    For example: `1d` means 1 day which means 60 * 60 * 24 seconds.
    The recognized formats are:
        10d  : 10 days
        3m   : 3 minutes
        12h  : 12 hours
    """
    match = FREQUENCY_RE.match(value)
    if not match:
        raise FrequencyDefinitionError(value)

    number = int(match.group(1))
    unit = match.group(2)

    if unit == 'h':
        number *= 60 * 60
    elif unit == 'm':
        number *= 60
    elif unit == 'd':
        number *= 60 * 60 * 24
    elif unit:
        raise FrequencyDefinitionError(value)
    return number


VALID_TIME_RE = re.compile(r'^\d\d:\d\d$')


def convert_time(value):
    """Return (h, m) as tuple."""
    if not VALID_TIME_RE.match(value):
        raise TimeDefinitionError("Invalid definition of time %r" % value)

    hh, mm = value.split(':')
    if int(hh) > 23 or int(mm) > 59:
        raise TimeDefinitionError("Invalid definition of time %r" % value)
    return (int(hh), int(mm))


def get_matching_job_specs(cmds):
    """Return list of matching job specs for this cmd.

    :arg cmds: "all" returns list of all job_specs, cmds return single job_spec,
        list of cmds returns list of job_specs

    """
    if cmds == ['all']:
        return JOBS
    if isinstance(cmds, str):
        return JOBS_MAP.get(cmds)
    return [JOBS_MAP[cmd] for cmd in cmds if cmd in JOBS_MAP]


def time_to_run(job_spec, job):
    """Determine whether it's time for this cmd to run."""
    now = timezone.now()
    time_ = job_spec.get('time')

    if job.next_run is None:
        if time_:
            # Only run if this hour and minute is < now
            hh, mm = convert_time(time_)
            return (now.hour, now.minute) >= (hh, mm)

        else:
            return True

    return job.next_run < now


def get_run_times(job_spec, last_success):
    """Return generator of run_times for this job."""
    now = timezone.now()

    # If this is not a backfill job, just run it
    if not job_spec.get('backfill', False):
        yield now
        return

    # If this is a backfill command that's never been run before, run it
    if last_success is None:
        yield now
        return

    # Figure out the backfill times and yield those; base it on the
    # first_run datetime so the job doesn't drift
    when = last_success
    if job_spec.get('time'):
        # So, reset the hour/minute part to always match the
        # intention.
        hh, mm = convert_time(job_spec['time'])
        when = when.replace(
            hour=hh,
            minute=mm,
            second=0,
            microsecond=0
        )
    seconds = convert_frequency(job_spec.get('frequency'))
    interval = datetime.timedelta(seconds=seconds)
    # Loop over each missed interval from the time of the last success,
    # forward by each interval until it reaches the time 'now'.
    while (when + interval) <= now:
        when += interval
        yield when


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--list-jobs', action='store_true',
            help='List all jobs.'
        )
        parser.add_argument(
            '--mark-success', type=str, default='',
            help='Comma-delimited list of job names to mark successful or "all" for all.'
        )
        parser.add_argument(
            '--reset-job', type=str, default='',
            help='Comma-delimited list of job names to reset or "all" for all.'
        )
        parser.add_argument(
            '--job', type=str, default='',
            help='Job name for job you want to run.'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Force a job to run even if it is not time.'
        )

        # This allows us to pass in sub command arguments through the cron
        # command
        parser.add_argument(
            '--job-arg', action='append',
            help='Cron job command arguments in name=value format.'
        )

    def handle(self, **options):
        """Execute crontabber command."""
        if options['list_jobs']:
            return self.cmd_list_jobs()
        elif options['mark_success']:
            return self.cmd_mark_success(options['mark_success'])
        elif options['reset_job']:
            return self.cmd_reset_job(options['reset_job'])
        elif options['job']:
            job_args = {}
            for arg in (options['job_arg'] or []):
                if '=' in arg:
                    key, val = arg.split('=', 1)
                else:
                    key, val = arg, True
                job_args[key] = val
            return self.cmd_run_one(options['job'], options['force'], job_args)
        else:
            return self.cmd_run_all()

    def cmd_list_jobs(self):
        """Subcommand to list jobs and job state."""
        for job_spec in JOBS:
            self.stdout.write(job_spec['cmd'])
            schedule = []
            if job_spec.get('frequency'):
                schedule.append('every ' + job_spec['frequency'])
            if job_spec.get('time'):
                schedule.append(job_spec['time'] + ' UTC')
            schedule = ' @ '.join(schedule)
            self.stdout.write('    schedule:     %s' % schedule)

            try:
                job = Job.objects.get(app_name=job_spec['cmd'])
                self.stdout.write('    last run:     %s' % job.last_run)
                self.stdout.write('    last_success: %s' % job.last_success)
                self.stdout.write('    next run:     %s' % job.next_run)
                if job.last_error:
                    self.stdout.write('    ' + job.last_error)
            except Job.DoesNotExist:
                self.stdout.write('    Never run.')
        return 0

    def cmd_mark_success(self, cmds):
        """Mark jobs as successful in crontabber bookkeeping."""
        cmds = cmds.split(',')
        job_specs = get_matching_job_specs(cmds)

        now = timezone.now()
        for job_spec in job_specs:
            cmd = job_spec['cmd']
            self.stdout.write('Marking %s for success at %s...' % (cmd, now))
            self._log_run(
                cmd,
                seconds=0,
                time_=job_spec.get('time'),
                last_success=now,
                now=now,
                exc_type=None,
                exc_value=None,
                exc_tb=None
            )
        return 0

    def cmd_reset_job(self, cmds):
        """Reset jobs by removing all bookkeeping state."""
        cmds = cmds.split(',')
        job_specs = get_matching_job_specs(cmds)

        for job_spec in job_specs:
            cmd = job_spec['cmd']
            try:
                job = Job.objects.get(app_name=cmd)
                job.delete()
                self.stdout.write('Job %s is reset.' % cmd)
            except Job.DoesNotExist:
                self.stdout.write('Job %s already reset' % cmd)
        return 0

    def cmd_run_all(self):
        logger.info('Running all jobs...')
        for job_spec in JOBS:
            self._run_one(job_spec)
        return 0

    def cmd_run_one(self, description, force=False, job_args=None):
        for job_spec in JOBS:
            if job_spec['cmd'] == description:
                return self._run_one(job_spec, force=force, job_args=job_args)
        raise JobNotFoundError(description)

    def _run_one(self, job_spec, force=False, job_args=None):
        job_args = job_args or {}
        cmd = job_spec['cmd']

        # Make sure we have a job record before trying to run anything
        job = Job.objects.get_or_create(app_name=cmd)[0]

        if force:
            # If we're forcing the job, just run it without the bookkeeping.
            return self._run_job(job_spec, job_args)

        # Figure out whether this job should be run now
        seconds = convert_frequency(job_spec.get('frequency'))
        if not time_to_run(job_spec, job):
            logger.info("skipping %s because it's not time to run", cmd)
            return

        logger.info('about to run %s', cmd)

        now = timezone.now()
        log_run = True
        exc_type = exc_value = exc_tb = None
        start_time = None
        run_time = None

        try:
            with self.lock_job(job_spec['cmd']):
                # Backfill jobs can have multiple run-times, so we iterate
                # through all possible ones until either we get them all done
                # or it dies
                for run_time in get_run_times(job_spec, job.last_success):
                    # If "backfill" is in the spec, then we want to additionally
                    # pass in a run_time argument
                    if job_spec.get('backfill', True):
                        job_args['run_time'] = run_time

                    start_time = time.time()
                    self._run_job(job_spec, job_args)
                    end_time = time.time()

                    logger.info('successfully ran %s on %s', cmd, run_time)
                    self._remember_success(cmd, run_time, end_time - start_time)

        except OngoingJobError:
            log_run = False
            raise

        except Exception:
            end_time = time.time()
            exc_type, exc_value, exc_tb = sys.exc_info()
            single_line_tb = (
                ''.join(traceback.format_exception(*sys.exc_info()))
                .replace('\n', '\\n')
            )
            logger.error('error when running %s (%s): %s', cmd, run_time, single_line_tb)
            self._remember_failure(
                cmd,
                end_time - start_time,
                exc_type,
                exc_value,
                exc_tb
            )

        finally:
            if log_run:
                self._log_run(
                    cmd,
                    seconds,
                    job_spec.get('time'),
                    run_time,
                    now,
                    exc_type, exc_value, exc_tb
                )

    def _run_job(self, job_spec, job_args):
        """Run job with specified args."""
        return call_command(job_spec['cmd'], stdout=self.stdout, **job_args)

    def _remember_success(self, cmd, success_date, duration):
        Log.objects.create(
            app_name=cmd,
            success=success_date,
            duration='%.5f' % duration,
        )
        metrics.gauge('job_success_runtime', value=duration, tags=['job:%s' % cmd])

    def _remember_failure(self, cmd, duration, exc_type, exc_value, exc_tb):
        Log.objects.create(
            app_name=cmd,
            duration='%.5f' % duration,
            exc_type=repr(exc_type),
            exc_value=repr(exc_value),
            exc_traceback=''.join(traceback.format_tb(exc_tb))
        )
        metrics.gauge('job_failure_runtime', value=duration, tags=['job:%s' % cmd])

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
            results = Job.objects.filter(app_name=cmd, ongoing=job.ongoing).update(ongoing=now)
            if results == 1:
                yield
                Job.objects.filter(app_name=cmd).update(ongoing=None)
                return

        # Can't lock it, so raise an error
        raise OngoingJobError(job.ongoing)

    def _log_run(self, cmd, seconds, time_, last_success, now, exc_type, exc_value, exc_tb):
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
            tb = ''.join(traceback.format_tb(exc_tb))
            job.last_error = {
                'type': exc_type,
                'value': str(exc_value),
                'traceback': tb,
            }
            job.error_count = job.error_count + 1
        else:
            job.last_error = {}
            job.error_count = 0

        job.save()

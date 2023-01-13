# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import re

from django.utils import timezone

from crashstats.cron import (
    FrequencyDefinitionError,
    TimeDefinitionError,
    DEFAULT_FREQUENCY,
    JOBS,
    JOBS_MAP,
)


FREQUENCY_RE = re.compile(r"^(\d+)([^\d])$")


def convert_frequency(value):
    """Return number of seconds that a frequency string represents.

    For example: `1d` means 1 day which means 60 * 60 * 24 seconds.
    Examples:

    * 10d: 10 days
    * 3m: 3 minutes
    * 12h: 12 hours

    """
    match = FREQUENCY_RE.match(value)
    if not match:
        raise FrequencyDefinitionError(value)

    number = int(match.group(1))
    unit = match.group(2)

    if unit == "h":
        number *= 60 * 60
    elif unit == "m":
        number *= 60
    elif unit == "d":
        number *= 60 * 60 * 24
    elif unit:
        raise FrequencyDefinitionError(value)
    return number


VALID_TIME_RE = re.compile(r"^\d\d:\d\d$")


def convert_time(value):
    """Return (h, m) as tuple."""
    if not VALID_TIME_RE.match(value):
        raise TimeDefinitionError("Invalid definition of time %r" % value)

    hh, mm = value.split(":")
    if int(hh) > 23 or int(mm) > 59:
        raise TimeDefinitionError("Invalid definition of time %r" % value)
    return (int(hh), int(mm))


def get_matching_job_specs(cmds):
    """Return list of matching job specs for this cmd.

    :arg cmds: ['all'] returns list of all job_specs, cmds (str) returns
        a single job_spec, and list of cmds returns list of job_specs

    """
    if cmds == ["all"]:
        return JOBS
    if isinstance(cmds, str):
        return JOBS_MAP.get(cmds)
    return [JOBS_MAP[cmd] for cmd in cmds if cmd in JOBS_MAP]


def time_to_run(job_spec, job):
    """Determine whether it's time for this cmd to run."""
    now = timezone.now()
    time_ = job_spec.get("time")

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
    if not job_spec.get("backfill", False):
        yield now
        return

    # If this is a backfill command that's never been run before, run it
    if last_success is None:
        yield now
        return

    # Figure out the backfill times and yield those; base it on the
    # first_run datetime so the job doesn't drift
    when = last_success
    if job_spec.get("time"):
        # So, reset the hour/minute part to always match the
        # intention.
        hh, mm = convert_time(job_spec["time"])
        when = when.replace(hour=hh, minute=mm, second=0, microsecond=0)
    seconds = convert_frequency(job_spec.get("frequency", DEFAULT_FREQUENCY))
    interval = datetime.timedelta(seconds=seconds)
    # Loop over each missed interval from the time of the last success,
    # forward by each interval until it reaches the time 'now'.
    while (when + interval) <= now:
        when += interval
        yield when


def format_datetime(value):
    """Return '' or '%Y-%m-%dT%H:%M' formatted datetime."""
    if not value:
        return ""
    return value.strftime("%Y-%m-%dT%H:%M")

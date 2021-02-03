# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# NOTE(willkg): You can't have the same job in here twice with two different
# frequencies. If we ever need to do that, we'll need to stop using "cmd" as
# the key in the db.
#
# Times are in UTC
#
# cmd, cmd_args, frequency, time, backfill, last_success
JOBS = [
    {
        # Test cron job
        "cmd": "crontest",
        "frequency": "1d",
    },
    {
        # Audit hackers group every week
        "cmd": "auditgroups",
        "frequency": "7d",
        "time": "05:00",
    },
    {
        # Expire old cronlog entries every week
        "cmd": "cleanse_cronlog",
        "frequency": "7d",
        "time": "05:00",
    },
    {
        # Update BugAssociations every hour
        "cmd": "bugassociations",
        "frequency": "1h",
        "last_success": True,
    },
    {
        # Update Signature bookkeeping every hour
        "cmd": "updatesignatures",
        "frequency": "1h",
        "last_success": True,
        "backfill": True,
    },
    {
        # Clean elasticsaerch indices every week at 6:00am
        "cmd": "esclean",
        "frequency": "7d",
        "time": "06:00",
    },
    {
        # Verify Socorro processed all incoming crashes daily at 4:00am
        "cmd": "verifyprocessed",
        "frequency": "1d",
        "time": "04:00",
        "backfill": True,
    },
    {
        # Check past missing crashes and update status daily at 3:00am
        "cmd": "updatemissing",
        "frequency": "1d",
        "time": "03:00",
    },
    {
        # Scrape archive.mozilla.org for productversion data every hour
        "cmd": "archivescraper",
        "frequency": "1h",
    },
]

# Map of cmd -> job_spec
JOBS_MAP = {job_spec["cmd"]: job_spec for job_spec in JOBS}


# The maximum time we let a job go for before we declare it a zombie (in seconds)
MAX_ONGOING = 60 * 60 * 2


# Error retry time (in seconds)
ERROR_RETRY_TIME = 60


# Default frequency for jobs
DEFAULT_FREQUENCY = "1d"


class FrequencyDefinitionError(Exception):
    pass


class JobNotFoundError(Exception):
    pass


class TimeDefinitionError(Exception):
    pass


class OngoingJobError(Exception):
    """Error raised when a job is currently running."""

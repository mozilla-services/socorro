# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# NOTE(willkg): Times are in UTC. These are Django-based jobs. The other
# crontabber handles the jobs that haven't been converted, yet.
#
# NOTE(willkg): You can't have the same job in here twice with two different
# frequencies. If we ever need to do that, we'll need to stop using "cmd" as
# the key in the db.
#
# cmd, frequency, time, backfill
JOBS = [
    {
        # Test cron job
        'cmd': 'crontest',
        'frequency': '1d',
    },

    {
        # Audit hackers group every week
        'cmd': 'auditgroups',
        'cmd_args': ['--persist'],
        'frequency': '7d',
        'time': '05:00',
    },
    {
        # Update BugAssociations every hour
        'cmd': 'bugassociations',
        'frequency': '1h',
        'last_success': True,
    },
    {
        # Update Signature bookkeeping every hour
        'cmd': 'updatesignatures',
        'frequency': '1h',
        'last_success': True,
        'backfill': True,
    }
]

# Map of cmd -> job_spec
JOBS_MAP = dict([(job_spec['cmd'], job_spec) for job_spec in JOBS])


# The maximum time we let a job go for before we declare it a zombie (in seconds)
MAX_ONGOING = 60 * 60 * 2


# Error retry time (in seconds)
ERROR_RETRY_TIME = 60


# Default frequency for jobs
DEFAULT_FREQUENCY = '1d'


class FrequencyDefinitionError(Exception):
    pass


class JobNotFoundError(Exception):
    pass


class TimeDefinitionError(Exception):
    pass


class OngoingJobError(Exception):
    """Error raised when a job is currently running."""

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import collections
import datetime
import re
import subprocess

from socorro.lib.datetimeutil import utc_now
from configman import Namespace, RequiredConfig


class FrequencyDefinitionError(Exception):
    pass


class CircularDAGError(Exception):
    pass


def reorder_dag(sequence,
                depends_getter=lambda x: x.depends_on,
                name_getter=lambda x: x.app_name,
                impatience_max=100):
    """
    DAG = Directed Acyclic Graph
    If we have something like:
        C depends on B
        B depends on A
        A doesn't depend on any

    Given the order of [C, B, A] expect it to return [A, B, C]

    parameters:

        :sequence: some sort of iterable list

        :depends_getter: a callable that extracts the depends on sub-list

        :name_getter: a callable that extracts the name

        :impatience_max: a max count that is reached before we end up in
                         an infinite loop.
    """

    ordered_jobs = []
    ordered_jobs_set = set()

    jobs = collections.defaultdict(list)
    map_ = {}
    _count_roots = 0
    for each in sequence:
        name = name_getter(each)
        depends_on = depends_getter(each)
        if depends_on is None:
            depends_on = []
        elif isinstance(depends_on, tuple):
            depends_on = list(depends_on)
        elif not isinstance(depends_on, list):
            depends_on = [depends_on]
        if not depends_on:
            _count_roots += 1
        jobs[name] += depends_on
        map_[name] = each

    if not _count_roots:
        raise CircularDAGError("No job is at the root")
    count = 0
    while len(ordered_jobs) < len(jobs.keys()):
        for job, deps in jobs.iteritems():
            if job in ordered_jobs_set:
                continue
            if not set(deps).issubset(ordered_jobs_set):
                continue
            ordered_jobs.append(job)
            ordered_jobs_set = set(ordered_jobs)
        count += 1
        if count > impatience_max:
            raise CircularDAGError("Circular reference somewhere")

    return [map_[x] for x in ordered_jobs]


def convert_frequency(frequency):
    """return the number of seconds that a certain frequency string represents.
    For example: `1d` means 1 day which means 60 * 60 * 24 seconds.
    The recognized formats are:
        10d  : 10 days
        3m   : 3 minutes
        12h  : 12 hours
    """
    number = int(re.findall('\d+', frequency)[0])
    unit = re.findall('[^\d]+', frequency)[0]
    if unit == 'h':
        number *= 60 * 60
    elif unit == 'm':
        number *= 60
    elif unit == 'd':
        number *= 60 * 60 * 24
    elif unit:
        raise FrequencyDefinitionError(unit)
    return number


class BaseCronApp(RequiredConfig):
    """The base class from which Socorro apps are based"""
    required_config = Namespace()

    def __init__(self, config, job_information):
        self.config = config
        self.job_information = job_information

# commented out because it doesn't work and I don't know why!
#    def __repr__(self):  # pragma: no cover
#        return ('<%s (app_name: %r, app_version:%r)>' % (
#                self.__class__,
#                self.app_name,
#                self.app_version))

    def main(self, function=None, once=True):
        if function is None:
            function = self._run_proxy
        now = utc_now()
        if once or not self.job_information:
            if once:
                function()
            else:
                function(now)
            yield now
        else:
            # figure out when it was last run
            last_success = self.job_information.get(
                'last_success',
                self.job_information.get('first_run')
            )
            if not last_success:
                # either it has never run successfully or it was previously run
                # before the 'first_run' key was added (legacy).
                self.config.logger.warning(
                    'No previous last_success information available'
                )
                function(now)
                yield now
            else:
                when = last_success
                # The last_success datetime is originally based on the
                # first_run. From then onwards it just adds the interval to
                # it so the hour is not likely to drift from that original
                # time.
                # However, what can happen is that on a given day, "now" is
                # LESS than the day before. This can happen because the jobs
                # that are run BEFORE are variable in terms of how long it
                # takes. Thus, one day, now might be "18:02" and the next day
                # the it's "18:01". If this happens the original difference
                # will prevent it from running the backfill again.
                #
                # For more info see the
                # test_backfilling_with_configured_time_slow_job unit test.
                if self.config.time:
                    # So, reset the hour/minute part to always match the
                    # intention.
                    h, m = [int(x) for x in self.config.time.split(':')]
                    when = when.replace(
                        hour=h,
                        minute=m,
                        second=0,
                        microsecond=0
                    )
                seconds = convert_frequency(self.config.frequency)
                interval = datetime.timedelta(seconds=seconds)
                while (when + interval) < now:
                    when += interval
                    function(when)
                    yield when

    def _run_proxy(self):
        return self.run()

    def run(self):  # pragma: no cover
        raise NotImplementedError("Your fault!")


class BaseBackfillCronApp(BaseCronApp):

    def main(self, function=None):
        return super(BaseBackfillCronApp, self).main(once=False,
                                                     function=function)

    def _run_proxy(self, date):
        return self.run(date)

    def run(self, date):  # pragma: no cover
        raise NotImplementedError("Your fault!")


class PostgresCronApp(BaseCronApp):

    def _run_proxy(self):
        database = self.config.database.database_class(self.config.database)
        with database() as connection:
            self.run(connection)

    def run(self, connection):  # pragma: no cover
        raise NotImplementedError("Your fault!")


class PostgresBackfillCronApp(BaseBackfillCronApp):

    def _run_proxy(self, date):
        database = self.config.database.database_class(self.config.database)
        with database() as connection:
            self.run(connection, date)

    def run(self, connection, date):  # pragma: no cover
        raise NotImplementedError("Your fault!")


class PostgresTransactionManagedCronApp(BaseCronApp):

    # XXX put transaction_executor here?

    def main(self):
        database = self.config.database.database_class(self.config.database)
        executor = self.config.database.transaction_executor_class(
            self.config.database,
            database
        )
        executor(self.run)
        yield utc_now()

    def run(self, connection):  # pragma: no cover
        raise NotImplementedError("Your fault!")


class SubprocessMixin(object):

    def run_process(self, command, input=None):
        """
        Run the command and return a tuple of three things.

        1. exit code - an integer number
        2. stdout - all output that was sent to stdout
        2. stderr - all output that was sent to stderr
        """
        if isinstance(command, (tuple, list)):
            command = ' '.join('"%s"' % x for x in command)

        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate(input=input)
        return proc.returncode, out.strip(), err.strip()

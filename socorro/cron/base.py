# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging
import re

from configman import Namespace, RequiredConfig

from socorro.lib.datetimeutil import utc_now


class FrequencyDefinitionError(Exception):
    pass


def convert_frequency(frequency):
    """return the number of seconds that a certain frequency string represents.
    For example: `1d` means 1 day which means 60 * 60 * 24 seconds.
    The recognized formats are:
        10d  : 10 days
        3m   : 3 minutes
        12h  : 12 hours
    """
    number = int(re.findall(r'\d+', frequency)[0])
    unit = re.findall(r'[^\d]+', frequency)[0]
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
    """The base class from which Socorro cron apps are based.  Subclasses
    should use the cron app class decorators below to add features such as
    PostgreSQL connections or backfill capability."""
    required_config = Namespace()

    def __init__(self, config, job_information):
        self.config = config
        self.job_information = job_information
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def main(self, function=None, once=True):
        if not function:
            function = self._run_proxy
        now = utc_now()

        # handle one of four possible cases

        # case 1: no backfill, just run this job now
        if once:
            function()
            yield now
            return

        # case 2: this could be a backfil, but we don't have any
        #   job information.  Run it with today's date
        if not self.job_information:
            function(now)
            yield now
            return

        # back fill cases:
        # figure out when it was last run successfully
        last_success = self.job_information.get(
            'last_success',
            self.job_information.get('first_run')
        )

        # case 3: either it has never run successfully or it was previously run
        #   before the 'first_run' key was added (legacy).
        if not last_success:
            self.logger.warning(
                'No previous last_success information available'
            )
            # just run it for the time 'now'
            function(now)
            yield now
            return

        # case 4:
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
        # loop over each missed interval from the time of the last success,
        # forward by each interval until it reaches the time 'now'.  Run the
        # cron app once for each interval.
        while (when + interval) < now:
            when += interval
            function(when)
            yield when

    def _run_proxy(self, *args, **kwargs):
        """this is indirection to the run function.  By exectuting this method
        instead of the actual "run" method directly, we can use inheritance
        to provide some resources to the run function via the run function's
        arguments"""
        return self.run(*args, **kwargs)

    def run(self):  # pragma: no cover
        # crontabber apps should define their own run functions and not rely
        # on these base classes.  This default base method threatens a runtime
        # error
        raise NotImplementedError('please implement')

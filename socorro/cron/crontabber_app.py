#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from configman import Namespace, class_converter
from crontabber.app import (
    classes_in_namespaces_converter_with_compression,
    CronTabberBase,
    get_extra_as_options,
    JobNotFoundError,
    line_splitter,
    pipe_splitter,
)

from socorro.app.socorro_app import App
from socorro.lib.datetimeutil import utc_now


# NOTE(willkg): This is what we have in -prod. Note that the
# FetchADIFromHiveCronApp job runs on a separate box with a separate crontabber
# configuration. Times are in UTC.
DEFAULT_JOBS_BASE = [
    # DB partition table and ES maintenance
    'socorro.cron.jobs.weekly_reports_partitions.WeeklyReportsPartitionsCronApp|7d|06:00',
    'socorro.cron.jobs.drop_old_partitions.DropOldPartitionsCronApp|7d|06:00',
    'socorro.cron.jobs.truncate_partitions.TruncatePartitionsCronApp|7d|06:00',
    'socorro.cron.jobs.elasticsearch_cleanup.ElasticsearchCleanupCronApp|7d|06:00',

    # ADI maintenance
    'socorro.cron.jobs.clean_raw_adi.CleanRawADICronApp|1d|06:00',
    'socorro.cron.jobs.matviews.ADUCronApp|1d|08:30',
    'socorro.cron.jobs.matviews.BuildADUCronApp|1d|08:30',

    # Product/version maintenance
    'socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1h',
    'socorro.cron.jobs.featured_versions_automatic.FeaturedVersionsAutomaticCronApp|1h',
    'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d|05:00',

    # Crash data analysis
    'socorro.cron.jobs.bugzilla.BugzillaCronApp|1h',
    'socorro.cron.jobs.update_signatures.UpdateSignaturesCronApp|1h',
]

DEFAULT_JOBS = ', '.join(DEFAULT_JOBS_BASE)

# Jobs that run in the -stage environment
STAGE_JOBS = ', '.join(
    DEFAULT_JOBS_BASE + [
        'socorro.cron.jobs.fetch_adi_alt.FAKEFetchADIFromHiveCronApp|1d|08:20',
        'socorro.cron.jobs.monitoring.DependencySecurityCheckCronApp|1d',
    ]
)


# Jobs that run in the -stage-new and -prod-new environments
STAGE_NEW_JOBS = ', '.join(
    DEFAULT_JOBS_BASE + [
        'socorro.cron.jobs.fetch_adi_alt.RawADIMoverCronApp|1d|08:20'
    ]
)


def jobs_converter(path_or_jobs):
    """Takes a Python dotted path or a jobs spec and returns crontabber jobs

    Example Python dotted path::

        jobs_converter('socorro.cron.crontabber_app.DEFAULT_JOBS')

    Example jobs spec::

        jobs_converter('socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1h')


    :arg str path_or_jobs: a Python dotted path or a crontabber jobs spec

    :returns: crontabber jobs InnerClassList

    """
    if '|' not in path_or_jobs:
        # NOTE(willkg): crontabber's class_converter returns the value pointed
        # to by a Python dotted path
        input_str = class_converter(path_or_jobs)
    else:
        input_str = path_or_jobs

    from_string_converter = classes_in_namespaces_converter_with_compression(
        reference_namespace=Namespace(),
        list_splitter_fn=line_splitter,
        class_extractor=pipe_splitter,
        extra_extractor=get_extra_as_options
    )
    return from_string_converter(input_str)


class CronTabberApp(CronTabberBase, App):
    config_defaults = {
        'always_ignore_mismatches': True,

        'resource': {
            'postgresql': {
                'database_class': (
                    'socorro.external.postgresql.connection_context.ConnectionContext'
                ),
            },
        },
        'crontabber': {
            'max_ongoing_age_hours': 2
        }
    }
    required_config = CronTabberBase.required_config.safe_copy()

    # Stomp on the existing "crontabber.jobs" configuration with one that can
    # also take Python dotted paths
    required_config.crontabber.add_option(
        'jobs',
        default='socorro.cron.crontabber_app.DEFAULT_JOBS',
        from_string_converter=jobs_converter,
        doc='Crontabber jobs spec or Python dotted path to jobs spec',
    )
    required_config.add_option(
        name='mark-success',
        default='',
        doc='Mark specified jobs as successful. Comma-separated list of jobs or "all".',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    def get_job_data(self, job_list_string):
        """Converts job_list_string specification into list of jobs

        :arg str job_list_string: specifies the jobs to return as a comma separated
            list of app names or description or "all" to return them all

        :returns: list of ``(class_name, job_class)`` tuples

        """
        class_list = self.config.crontabber.jobs.class_list
        class_list = self._reorder_class_list(class_list)

        if job_list_string.lower() == 'all':
            return class_list

        job_list = [item.strip() for item in job_list_string.split(',')]

        job_classes = []
        for description in job_list:
            for class_name, job_class in class_list:
                python_module = job_class.__module__ + '.' + job_class.__name__
                if description == job_class.app_name or description == python_module:
                    job_classes.append((class_name, job_class))
                    break
            else:
                raise JobNotFoundError(description)
        return job_classes

    def mark_success(self, job_list_string):
        """Mark jobs as successful in crontabber bookkeeping"""
        job_classes = self.get_job_data(job_list_string)
        now = utc_now()

        for class_name, job_class in job_classes:
            app_name = job_class.app_name
            job_name = job_class.__module__ + '.' + job_class.__name__
            job_config = self.config.crontabber['class-%s' % class_name]
            self.config.logger.info('Marking %s (%s) for success...', app_name, job_name)
            self._log_run(
                job_class,
                seconds=0,
                time_=job_config.time,
                last_success=now,
                now=now,
                exc_type=None,
                exc_value=None,
                exc_tb=None
            )
            self._remember_success(job_class, success_date=now, duration=0)

    def main(self):
        if self.config.get('mark-success'):
            self.mark_success(self.config.get('mark-success'))
            return 0
        return super(CronTabberApp, self).main()


if __name__ == '__main__':
    sys.exit(CronTabberApp.run())

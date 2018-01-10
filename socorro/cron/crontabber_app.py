#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from configman import Namespace, class_converter
from crontabber.app import (
    CronTabberBase,
    classes_in_namespaces_converter_with_compression,
    get_extra_as_options,
    line_splitter,
    main,
    pipe_splitter,
)

from socorro.app.socorro_app import App


# NOTE(willkg): This is what we have in -prod
DEFAULT_JOBS_BASE = [
    'socorro.cron.jobs.weekly_reports_partitions.WeeklyReportsPartitionsCronApp|7d',
    'socorro.cron.jobs.matviews.ProductVersionsCronApp|1d|05:00',
    'socorro.cron.jobs.matviews.SignaturesCronApp|1d|05:00',
    'socorro.cron.jobs.matviews.RawUpdateChannelCronApp|1d|05:00',
    'socorro.cron.jobs.matviews.ADUCronApp|1d|08:30',
    'socorro.cron.jobs.matviews.DuplicatesCronApp|1h',
    'socorro.cron.jobs.matviews.ReportsCleanCronApp|1h',
    'socorro.cron.jobs.bugzilla.BugzillaCronApp|1h',
    'socorro.cron.jobs.matviews.BuildADUCronApp|1d|08:30',
    'socorro.cron.jobs.matviews.AndroidDevicesCronApp|1d|05:00',
    'socorro.cron.jobs.matviews.GraphicsDeviceCronApp|1d|05:00',
    'socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1h',
    'socorro.cron.jobs.elasticsearch_cleanup.ElasticsearchCleanupCronApp|7d',
    'socorro.cron.jobs.drop_old_partitions.DropOldPartitionsCronApp|7d',
    'socorro.cron.jobs.truncate_partitions.TruncatePartitionsCronApp|7d',
    'socorro.cron.jobs.clean_raw_adi_logs.CleanRawADILogsCronApp|1d',
    'socorro.cron.jobs.clean_raw_adi.CleanRawADICronApp|1d',
    'socorro.cron.jobs.clean_missing_symbols.CleanMissingSymbolsCronApp|1d',
    'socorro.cron.jobs.missingsymbols.MissingSymbolsCronApp|1d',
    'socorro.cron.jobs.featured_versions_automatic.FeaturedVersionsAutomaticCronApp|1h',
    'socorro.cron.jobs.upload_crash_report_json_schema.UploadCrashReportJSONSchemaCronApp|1h',
]

DEFAULT_JOBS = ', '.join(DEFAULT_JOBS_BASE)

# Jobs that run in the -stage environment
STAGE_JOBS = ', '.join(
    DEFAULT_JOBS_BASE + [
        'socorro.cron.jobs.fetch_adi_from_hive.FAKEFetchADIFromHiveCronApp|1d|08:20',
        'socorro.cron.jobs.monitoring.DependencySecurityCheckCronApp|1d',
    ]
)


# Jobs that run in the -stage-new environment
STAGE_NEW_JOBS = ', '.join(
    [job for job in DEFAULT_JOBS_BASE if 'MissingSymbolsCronApp' not in job] +
    [
        'socorro.cron.jobs.fetch_adi_from_hive.RawADIMoverCronApp|1d|08:20'
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
    required_config = CronTabberBase.required_config.safe_copy()

    # Stomp on the existing "crontabber.jobs" configuration with one that can
    # also take Python dotted paths
    required_config.crontabber.add_option(
        'jobs',
        default='socorro.cron.crontabber_app.DEFAULT_JOBS',
        from_string_converter=jobs_converter,
        doc='Crontabber jobs spec or Python dotted path to jobs spec',
    )


# NOTE(willkg): We need to "fix" the defaults here rather than use App's
# get_application_defaults() because that doesn't support nested configuration
# defaults
CronTabberApp.required_config.crontabber.database_class.default = (
    'socorro.external.postgresql.connection_context.ConnectionContext'
)
CronTabberApp.required_config.crontabber.job_state_db_class.default.required_config.database_class.default = (  # noqa
    'socorro.external.postgresql.connection_context.ConnectionContext'
)


if __name__ == '__main__':
    sys.exit(main(CronTabberApp))

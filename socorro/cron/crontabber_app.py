#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crontabber.app import CronTabberBase


# NOTE(willkg): This is what we have in -prod
DEFAULT_JOBS = '''
socorro.cron.jobs.weekly_reports_partitions.WeeklyReportsPartitionsCronApp|7d
socorro.cron.jobs.matviews.ProductVersionsCronApp|1d|05:00
socorro.cron.jobs.matviews.SignaturesCronApp|1d|05:00
socorro.cron.jobs.matviews.RawUpdateChannelCronApp|1d|05:00
socorro.cron.jobs.matviews.ADUCronApp|1d|08:30
socorro.cron.jobs.matviews.DuplicatesCronApp|1h
socorro.cron.jobs.matviews.ReportsCleanCronApp|1h
socorro.cron.jobs.bugzilla.BugzillaCronApp|1h
socorro.cron.jobs.matviews.BuildADUCronApp|1d|08:30
socorro.cron.jobs.matviews.AndroidDevicesCronApp|1d|05:00
socorro.cron.jobs.matviews.GraphicsDeviceCronApp|1d|05:00
socorro.cron.jobs.matviews.CrashAduByBuildSignatureCronApp|1d|08:30
socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1h
socorro.cron.jobs.elasticsearch_cleanup.ElasticsearchCleanupCronApp|7d
socorro.cron.jobs.drop_old_partitions.DropOldPartitionsCronApp|7d
socorro.cron.jobs.truncate_partitions.TruncatePartitionsCronApp|7d
socorro.cron.jobs.clean_raw_adi_logs.CleanRawADILogsCronApp|1d
socorro.cron.jobs.clean_raw_adi.CleanRawADICronApp|1d
socorro.cron.jobs.clean_missing_symbols.CleanMissingSymbolsCronApp|1d
socorro.cron.jobs.missingsymbols.MissingSymbolsCronApp|1d
socorro.cron.jobs.featured_versions_automatic.FeaturedVersionsAutomaticCronApp|1h
socorro.cron.jobs.upload_crash_report_json_schema.UploadCrashReportJSONSchemaCronApp|1h
'''


# this class is for eventual support of CronTabber with the universal
# socorro app.
from socorro.app.socorro_app import App as App


class CronTabberApp(CronTabberBase, App):
    @staticmethod
    def get_application_defaults():
        return {
            'jobs': DEFAULT_JOBS,
            'crontabber.database_class':
            'socorro.external.postgresql.connection_context.ConnectionContext',
            'crontabber.transaction_executor_class':
            'socorro.database.transaction_executor.TransactionExecutor',
            'crontabber.job_state_db_class.database_class':
            'socorro.external.postgresql.connection_context.ConnectionContext',

        }


from crontabber.app import CronTabber

# These settings should ideally be done in config, but because, at
# the moment, it's easier for us to maintain python we're doing it here.
CronTabber.required_config.crontabber.jobs.default = DEFAULT_JOBS
CronTabber.required_config.crontabber.database_class.default = (
    'socorro.external.postgresql.connection_context.ConnectionContext'
)
CronTabber.required_config.crontabber.job_state_db_class.default \
    .required_config.database_class.default = (
        'socorro.external.postgresql.connection_context.ConnectionContext'
    )

if __name__ == '__main__':  # pragma: no cover
    from crontabber.app import main
    import sys
    sys.exit(main(CronTabber))

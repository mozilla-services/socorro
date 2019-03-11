# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This script verifies that all the incoming crash reports for a specified day
were processed. It does this by listing the raw crash files for the day, then
checking to see if each of those raw crash files have corresponding processed
crash files.
"""

import datetime
from functools import partial
import logging
import multiprocessing
import sys

from configman import Namespace, class_converter
import markus
import more_itertools
from psycopg2 import IntegrityError

from socorro.cron.base import BaseCronApp
from socorro.cron.mixins import as_backfill_cron_app
from socorro.lib.dbutil import execute_no_results
from socorro.lib.raven_client import capture_error
from socorro.lib.transaction import transaction_context


metrics = markus.get_metrics('crontabber.verifyprocessed')


def check_crashids(entropy, boto_conn, bucket_name, date, sentry_dsn):
    """Checks crash ids for a given entropy and date."""
    logger = logging.getLogger(__name__)
    try:
        bucket = boto_conn.get_bucket(bucket_name)

        raw_crash_prefix_template = 'v2/raw_crash/%s/%s/'
        processed_crash_template = 'v1/processed_crash/%s'
        raw_crash_key_prefix = raw_crash_prefix_template % (entropy, date)

        missing = []
        for key_instance in bucket.list(raw_crash_key_prefix):
            raw_crash_key = key_instance.key
            crash_id = raw_crash_key.split('/')[-1]

            processed_crash_key = bucket.get_key(processed_crash_template % crash_id)
            if processed_crash_key is None:
                missing.append(crash_id)

        return missing
    except Exception:
        capture_error(
            sentry_dsn=sentry_dsn,
            logger=logger,
            exc_info=sys.exc_info(),
            extra={'entropy': entropy, 'date': date}
        )
        raise


@as_backfill_cron_app
class VerifyProcessedCronApp(BaseCronApp):
    app_name = 'verifyprocessed'
    app_description = 'verifies that incoming crash reports were processed'
    app_version = '1.0'

    required_config = Namespace()
    required_config.add_option(
        'crashstorage_class',
        default='socorro.external.boto.crashstorage.BotoS3CrashStorage',
        doc='S3 crash storage class',
        from_string_converter=class_converter,
        reference_value_from='resource.boto'
    )
    required_config.add_option(
        'database_class',
        default='socorro.external.postgresql.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql'
    )
    required_config.add_option(
        'num_workers',
        default=20,
        doc='Number of concurrent workers to list raw_crashes.'
    )
    required_config.add_option(
        'date',
        default='backfill',
        doc=(
            'The YYYYMMDD date. By default, this will use the backfill date from '
            'the db.'
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = self.config.database_class(self.config)
        self.crashstorage = self.config.crashstorage_class(self.config)

    def get_entropy(self):
        """Generate all entropy combinations."""
        chars = '0123456789abcdef'
        for x in chars:
            for y in chars:
                for z in chars:
                    yield x + y + z

    def find_missing_multiprocessing(self, date):
        connection_source = self.crashstorage.connection_source
        bucket_name = connection_source.config.bucket_name
        boto_conn = connection_source._connect()

        num_workers = self.config.num_workers

        check_crashids_for_date = partial(
            check_crashids,
            boto_conn=boto_conn,
            bucket_name=bucket_name,
            date=date,
            sentry_dsn=self.config.sentry.dsn
        )

        pool = multiprocessing.Pool(num_workers)
        missing = more_itertools.flatten(
            pool.map(
                check_crashids_for_date,
                self.get_entropy(),
                chunksize=1
            )
        )
        return list(missing)

    def handle_missing(self, date, missing):
        """Report crash ids for missing processed crashes."""
        metrics.gauge('missing_processed', len(missing))
        if missing:
            for crash_id in missing:
                self.logger.info('Missing: %s', crash_id)

                with transaction_context(self.database) as conn:
                    sql = """
                    INSERT INTO crashstats_missingprocessedcrashes (crash_id, created)
                    VALUES (%s, current_timestamp)
                    """
                    params = (crash_id,)
                    try:
                        execute_no_results(conn, sql, params)
                    except IntegrityError:
                        # If there's already one, that's fine--just move on
                        pass
        else:
            self.logger.info('All crashes for %s were processed.', date)

    def run(self, end_datetime):
        """Run cron app."""
        if self.config.date == 'backfill':
            # Change to previous day and convert to YYYYMMDD
            date = end_datetime - datetime.timedelta(days=1)
            date = date.strftime('%Y%m%d')
        else:
            # Run for the date the user specified
            date = self.config.date

        missing = self.find_missing_multiprocessing(date)

        self.handle_missing(date, missing)
        self.logger.info('Done!')

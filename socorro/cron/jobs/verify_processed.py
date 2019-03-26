# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This script verifies that all the incoming crash reports for a specified day
were processed. It does this by listing the raw crash files for the day, then
checking to see if each of those raw crash files have corresponding processed
crash files.
"""

import concurrent.futures
import datetime
from functools import partial

from configman import Namespace, class_converter
import markus
from psycopg2 import IntegrityError

from socorro.cron.base import BaseCronApp
from socorro.cron.mixins import as_backfill_cron_app
from socorro.lib.dbutil import execute_no_results, execute_query_fetchall
from socorro.lib.transaction import transaction_context


RAW_CRASH_PREFIX_TEMPLATE = 'v2/raw_crash/%s/%s/'
PROCESSED_CRASH_TEMPLATE = 'v1/processed_crash/%s'


metrics = markus.get_metrics('crontabber.verifyprocessed')


def check_crashids(entropy, boto_conn, bucket_name, date):
    """Checks crash ids for a given entropy and date."""
    bucket = boto_conn.get_bucket(bucket_name)

    raw_crash_key_prefix = RAW_CRASH_PREFIX_TEMPLATE % (entropy, date)

    missing = []
    for key_instance in bucket.list(raw_crash_key_prefix):
        raw_crash_key = key_instance.key
        crash_id = raw_crash_key.split('/')[-1]

        processed_crash_key = bucket.get_key(PROCESSED_CRASH_TEMPLATE % crash_id)
        if processed_crash_key is None:
            missing.append(crash_id)

    return missing


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

    def find_missing(self, date):
        connection_source = self.crashstorage.connection_source
        bucket_name = connection_source.config.bucket_name
        boto_conn = connection_source._connect()

        num_workers = self.config.num_workers

        check_crashids_for_date = partial(
            check_crashids,
            boto_conn=boto_conn,
            bucket_name=bucket_name,
            date=date,
        )

        missing = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            for result in executor.map(check_crashids_for_date, self.get_entropy(), timeout=300):
                missing.extend(result)

        return list(missing)

    def handle_missing(self, date, missing):
        """Report crash ids for missing processed crashes."""
        metrics.gauge('missing_processed', len(missing))
        if missing:
            for crash_id in missing:
                self.logger.info('Missing: %s', crash_id)

                with transaction_context(self.database) as conn:
                    sql = """
                    INSERT INTO crashstats_missingprocessedcrash (crash_id, is_processed, created)
                    VALUES (%s, False, current_timestamp)
                    """
                    params = (crash_id,)
                    try:
                        execute_no_results(conn, sql, params)
                    except IntegrityError:
                        # If there's already one, that's fine--just move on
                        pass
        else:
            self.logger.info('All crashes for %s were processed.', date)

    def check_past_missing(self):
        """Check the table for missing crashes and check to see if they exist."""
        connection_source = self.crashstorage.connection_source
        bucket_name = connection_source.config.bucket_name
        boto_conn = connection_source._connect()

        crash_ids = []

        with transaction_context(self.database) as conn:
            sql = """
            SELECT crash_id
            FROM crashstats_missingprocessedcrash
            WHERE is_processed=False
            """
            params = ()
            crash_ids = [item[0] for item in execute_query_fetchall(conn, sql, params)]

        no_longer_missing = []

        for crash_id in crash_ids:
            bucket = boto_conn.get_bucket(bucket_name)
            processed_crash_key = bucket.get_key(PROCESSED_CRASH_TEMPLATE % crash_id)
            if processed_crash_key is not None:
                no_longer_missing.append(crash_id)

        if no_longer_missing:
            with transaction_context(self.database) as conn:
                sql = """
                UPDATE crashstats_missingprocessedcrash
                SET is_processed=True
                WHERE crash_id IN %s
                """
                params = (tuple(no_longer_missing),)
                execute_no_results(conn, sql, params)

        self.logger.info(
            'Updated %s missing crashes which have since been processed',
            len(no_longer_missing)
        )

    def run(self, end_datetime):
        """Run cron app."""

        # Check and update existing missing before finding new missing things
        self.check_past_missing()

        if self.config.date == 'backfill':
            # Change to previous day and convert to YYYYMMDD
            date = end_datetime - datetime.timedelta(days=1)
            date = date.strftime('%Y%m%d')
        else:
            # Run for the date the user specified
            date = self.config.date

        missing = self.find_missing(date)

        self.handle_missing(date, missing)
        self.logger.info('Done!')

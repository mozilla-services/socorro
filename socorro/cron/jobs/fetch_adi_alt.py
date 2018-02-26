# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Contains alternate crontabber apps for "acquiring" ADI data. For the app
that actually talks to hive, see ``fetch_adi_from_hive.py``.

"""

import datetime

from configman import Namespace, class_converter
from crontabber.base import BaseCronApp
from crontabber.mixins import as_backfill_cron_app
from socorro.external.postgresql.connection_context import ConnectionContext


@as_backfill_cron_app
class FAKEFetchADIFromHiveCronApp(BaseCronApp):
    """Because of firewalls, we can't generally run the real
    'fetch-adi-from-hive' in a staging environment. That means that
    various other crontabber apps that depend on this refuses to
    run.

    By introducing a fake version - one that does nothing - we circumvent
    that problem as we're able to keep the same name as the real class.

    NB. The reason for prefixing this class with the word FAKE in
    all upper case is to make it extra noticable so that you never
    enable this class in a crontabber environment on production.

    For more information, see:
    https://bugzilla.mozilla.org/show_bug.cgi?id=1246673
    """

    app_name = 'fetch-adi-from-hive'
    app_description = 'FAKE Fetch ADI From Hive App that does nothing'
    app_version = '0.1'

    def run(self, date):
        self.config.logger.info(
            'Faking the fetching of ADI from Hive :)'
        )


@as_backfill_cron_app
class RawADIMoverCronApp(BaseCronApp):
    """Moves raw ADI data from one db to another

    Use this instead of ``FAKEFetchADIFromHiveCronApp`` and
    FetchADIFromHiveCronApp``.

    It uses the same app_name to fulfill cron job depdencies.

    To force a dry run, reset the state::
        ./socorro/cron/crontabber_app.py --reset-job=fetch-adi-from-hive

        ./socorro/cron/crontabber_app.py --job=fetch-adi-from-hive \
            --crontabber.class-RawADIMoverCronApp.dry_run

    """

    app_name = 'fetch-adi-from-hive'
    app_description = 'Raw ADI mover app'
    app_version = '0.1'

    required_config = Namespace()

    required_config.add_option(
        'dry_run',
        default=False,
        doc='Print instead of storing raw_adi data',
    )

    required_config.namespace('source')
    required_config.source.add_option(
        'database_class',
        default=ConnectionContext,
        doc='The class responsible for connecting to Postgres',
        reference_value_from='resource.postgresql',
    )

    required_config.namespace('destination')
    required_config.destination.add_option(
        'transaction_executor_class',
        default='socorro.database.transaction_executor.TransactionExecutorWithInfiniteBackoff',
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )
    required_config.destination.add_option(
        'database_class',
        default='socorro.external.postgresql.connection_context.ConnectionContext',
        doc=(
            'The class responsible for connecting to Postgres. '
            'Optionally set this to an empty string to entirely '
            'disable the secondary destination.'
        ),
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )

    def get_source_data(self, connection, target_date):
        """Retrives the raw_adi_logs data from the source for the given target date"""
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                adi_count,
                date,
                product_name,
                product_os_platform,
                product_os_version,
                product_version,
                build,
                product_guid,
                update_channel
            FROM raw_adi
            WHERE date = %s;
            """,
            vars=(target_date,)
        )
        data = [row for row in cursor]
        return data

    def save_data_to_destination(self, connection, source_data):
        """Saves data to destination db"""
        cursor = connection.cursor()
        for row in source_data:
            cursor.execute(
                """
                INSERT INTO raw_adi (
                    adi_count,
                    date,
                    product_name,
                    product_os_platform,
                    product_os_version,
                    product_version,
                    build,
                    product_guid,
                    update_channel
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                vars=row
            )

    def run(self, date):
        source_db = self.config.source.database_class(self.config.source)

        dest_db = self.config.destination.database_class(self.config.destination)
        tx_class = self.config.destination.transaction_executor_class
        transaction = tx_class(self.config, dest_db)

        # NOTE(willkg): Running on day x pulls in ADI from day x - 1 to match
        # the other fetch-adi-from-hive job.
        target_date = (date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        source_data = self.get_source_data(source_db.connection(), target_date)
        self.config.logger.info('Source data for %s: %s rows' % (target_date, len(source_data)))
        if not source_data:
            self.config.logger.info('Nothing to do.')
            return

        if self.config.dry_run:
            for row in source_data:
                self.config.logger.info('row: %s', row)
        else:
            transaction(self.save_data_to_destination, source_data)
        self.config.logger.debug('Done!')

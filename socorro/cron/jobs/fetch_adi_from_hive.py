# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Detailed documentation on columns avaiable from our Hive system at:
https://intranet.mozilla.org/Metrics/Blocklist

Columns being queried are:

* report_date
* product_name
* product_os_platform
* product_os_version
* product_version
* build
* build_channel
* product_guid
* count

"""

import codecs
import datetime
import urllib2
import os
import tempfile
import unicodedata

import pyhs2

from configman import Namespace, class_converter
from crontabber.base import BaseCronApp
from crontabber.mixins import as_backfill_cron_app
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.external.postgresql.dbapi2_util import execute_no_results


class NoRowsWritten(Exception):
    pass


_QUERY = """
    select
        ds,
        split(request_url,'/')[6],
        split(split(request_url,'/')[11], '%%20')[0],
        split(split(request_url,'/')[11], '%%20')[1],
        split(request_url,'/')[5],
        split(request_url,'/')[7],
        split(request_url,'/')[10],
        split(request_url,'/')[4],
        count(*)
    FROM v2_raw_logs
    WHERE
        (
            domain='addons.mozilla.org' OR
            domain='blocklists.settings.services.mozilla.com'
        )
        and http_status_code = '200'
        and request_url like '/v1/blocklist/3/%%'
        and ds='%s'
    GROUP BY
        ds,
        split(request_url,'/')[6],
        split(split(request_url,'/')[11], '%%20')[0],
        split(split(request_url,'/')[11], '%%20')[1],
        split(request_url,'/')[5],
        split(request_url,'/')[7],
        split(request_url,'/')[10],
        split(request_url,'/')[4]
"""

_RAW_ADI_QUERY = """
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
    SELECT
        sum(count),
        report_date,
        CASE WHEN (raw_adi_logs.product_name = 'Fennec'
            AND product_guid = '{aa3c5121-dab2-40e2-81ca-7ea25febc110}')
        THEN 'FennecAndroid'
        WHEN (raw_adi_logs.product_name = 'Webapp Runtime')
        THEN 'WebappRuntime'
        ELSE raw_adi_logs.product_name
        END,
        product_os_platform,
        product_os_version,
        product_version,
        build,
        CASE WHEN (product_guid = 'webapprt@mozilla.org')
        THEN '{webapprt@mozilla.org}'
        ELSE product_guid
        END,
        CASE WHEN (build_channel ILIKE 'release%%')
        THEN 'release'
        ELSE build_channel
        END
    FROM raw_adi_logs
        -- FILTER with product_productid_map
        JOIN product_productid_map ON productid =
            CASE WHEN (product_guid = 'webapprt@mozilla.org')
            THEN '{webapprt@mozilla.org}'
            ELSE product_guid
            END
    WHERE
        report_date=%s
    GROUP BY
        report_date,
        raw_adi_logs.product_name,
        product_os_platform,
        product_os_version,
        product_version,
        build,
        product_guid,
        build_channel
"""

_FENNEC38_ADI_CHANNEL_CORRECTION_SQL = """
    update raw_adi
        set update_channel = 'beta'
        where product_name = 'FennecAndroid'
              and product_version = '38.0'
              and build = '20150427090529'
              and date > '2015-04-27';"""


@as_backfill_cron_app
class FetchADIFromHiveCronApp(BaseCronApp):
    """ This cron is our daily blocklist ping web logs query
        that rolls up all the browser checkins and let's us know
        how many browsers we think were active on the internet
        for a particular day """
    app_name = 'fetch-adi-from-hive'
    app_description = 'Fetch ADI From Hive App'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'query',
        default=_QUERY,
        doc='Hive query for fetching ADI data')

    required_config.add_option(
        'hive_host',
        default='localhost',
        doc='Hostname to run Hive query on')

    required_config.add_option(
        'hive_port',
        default=10000,
        doc='Port to run Hive query on')

    required_config.add_option(
        'hive_user',
        default='socorro',
        doc='User to connect to Hive with')

    required_config.add_option(
        'hive_password',
        default='ignored',
        doc='Password to connect to Hive with',
        secret=True)

    required_config.add_option(
        'hive_database',
        default='default',
        doc='Database name to connect to Hive with')

    required_config.add_option(
        'hive_auth_mechanism',
        default='PLAIN',
        doc='Auth mechanism for Hive')

    required_config.add_option(
        'timeout',
        default=30 * 60,  # 30 minutes
        doc='number of seconds to wait before timing out')

    required_config.namespace('primary_destination')
    required_config.primary_destination.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )
    required_config.primary_destination.add_option(
        'database_class',
        default=ConnectionContext,
        doc='The class responsible for connecting to Postgres',
        reference_value_from='resource.postgresql',
    )

    required_config.namespace('secondary_destination')
    required_config.secondary_destination.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )
    required_config.secondary_destination.add_option(
        'database_class',
        default=ConnectionContext,
        doc=(
            'The class responsible for connecting to Postgres. '
            'Optionally set this to an empty string to entirely '
            'disable the secondary destination.'
        ),
        reference_value_from='resource.postgresql',
    )

    @staticmethod
    def remove_control_characters(s):
        if isinstance(s, str):
            s = unicode(s, 'utf-8', errors='replace')
        return ''.join(c for c in s if unicodedata.category(c)[0] != "C")

    def _database_transaction(
        self,
        connection,
        raw_adi_logs_pathname,
        target_date
    ):
        with codecs.open(raw_adi_logs_pathname, 'r', 'utf-8') as f:
            pgcursor = connection.cursor()
            pgcursor.copy_from(
                f,
                'raw_adi_logs',
                null='None',
                columns=[
                    'report_date',
                    'product_name',
                    'product_os_platform',
                    'product_os_version',
                    'product_version',
                    'build',
                    'build_channel',
                    'product_guid',
                    'count'
                ]
            )
            pgcursor.execute(_RAW_ADI_QUERY, (target_date,))

        # for Bug 1159993
        execute_no_results(connection, _FENNEC38_ADI_CHANNEL_CORRECTION_SQL)

    def run(self, date):

        db_class = self.config.primary_destination.database_class
        primary_database = db_class(self.config.primary_destination)
        tx_class = self.config.primary_destination.transaction_executor_class
        primary_transaction = tx_class(
            self.config,
            primary_database,
        )
        transactions = [primary_transaction]

        db_class = self.config.secondary_destination.database_class
        # The reason for checking if this is anything at all is
        # because one way of disabling the secondary destination
        # is to set the database_class to an empty string.
        if db_class:
            secondary_database = db_class(self.config.secondary_destination)
            if secondary_database.config != primary_database.config:
                # The secondary really is different from the first one.
                # By default, if not explicitly set, it'll pick up the same
                # resource values as the first one.
                tx_class = (
                    self.config.secondary_destination
                    .transaction_executor_class
                )
                secondary_transaction = tx_class(
                    self.config,
                    secondary_database,
                )
                transactions.append(secondary_transaction)

        target_date = (date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        raw_adi_logs_pathname = os.path.join(
            tempfile.gettempdir(),
            "%s.raw_adi_logs.TEMPORARY%s" % (
                target_date,
                '.txt'
            )
        )
        try:
            with codecs.open(raw_adi_logs_pathname, 'w', 'utf-8') as f:
                hive = pyhs2.connect(
                    host=self.config.hive_host,
                    port=self.config.hive_port,
                    authMechanism=self.config.hive_auth_mechanism,
                    user=self.config.hive_user,
                    password=self.config.hive_password,
                    database=self.config.hive_database,
                    # the underlying TSocket setTimeout() wants milliseconds
                    timeout=self.config.timeout * 1000
                )

                cur = hive.cursor()
                query = self.config.query % target_date
                cur.execute(query)
                rows_written = 0
                for row in cur:
                    if None in row:
                        continue
                    f.write(
                        "\t"
                        .join(
                            self.remove_control_characters(
                                urllib2.unquote(v)
                            ).replace('\\', '\\\\')
                            if isinstance(v, basestring) else str(v)
                            for v in row
                        )
                    )
                    f.write("\n")
                    rows_written += 1

            if not rows_written:
                raise NoRowsWritten('hive yielded no rows to write')

            self.config.logger.info(
                'Wrote %d rows from doing hive query' % rows_written
            )
            for transaction in transactions:
                transaction(
                    self._database_transaction,
                    raw_adi_logs_pathname,
                    target_date
                )

        finally:
            if os.path.isfile(raw_adi_logs_pathname):
                os.remove(raw_adi_logs_pathname)


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

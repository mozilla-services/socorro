# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This file defines PostgreSQLCrashStorage.

import datetime
import json
from psycopg2 import ProgrammingError

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound
)
from configman import (
    Namespace,
    class_converter
)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.lib.datetimeutil import uuid_to_date
from socorro.external.postgresql.dbapi2_util import (
    SQLDidNotReturnSingleValue,
    single_value_sql,
    execute_no_results
)


class PostgreSQLCrashStorage(CrashStorageBase):
    """Saves crash data to postgresql"""

    required_config = Namespace()

    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        'database_class',
        default=ConnectionContext,
        doc='the class responsible for connecting to Postgres',
        reference_value_from='resource.postgresql',
    )

    _reports_table_mappings = (
        # processed name, reports table name
        ("addons_checked", "addons_checked", None),
        ("address", "address", 20),
        ("app_notes", "app_notes", 1024),
        ("build", "build", 30),
        ("client_crash_date", "client_crash_date", None),
        ("completeddatetime", "completed_datetime", None),
        ("cpu_info", "cpu_info", 100),
        ("cpu_name", "cpu_name", 100),
        ("date_processed", "date_processed", None),
        ("distributor", "distributor", 20),
        ("distributor_version", "distributor_version", 20),
        ("email", "email", 100),
        ("exploitability", "exploitability", None),
        # ("flash_process_dump", "flash_process_dump", None),  # future
        ("flash_version", "flash_version", None),
        ("hangid", "hangid", None),
        ("install_age", "install_age", None),
        ("last_crash", "last_crash", None),
        ("os_name", "os_name", 100),
        ("os_version", "os_version", 100),
        ("processor_notes", "processor_notes", None),
        ("process_type", "process_type", None),
        ("product", "product", 30),
        ("productid", "productid", None),
        ("reason", "reason", 255),
        ("release_channel", "release_channel", None),
        ("signature", "signature", 255),
        ("startedDateTime", "started_datetime", None),
        ("success", "success", None),
        ("topmost_filenames", "topmost_filenames", None),
        ("truncated", "truncated", None),
        ("uptime", "uptime", None),
        ("user_comments", "user_comments", 1024),
        ("user_id", "user_id", 50),
        ("url", "url", 255),
        ("uuid", "uuid", 50),
        ("version", "version", 16),
    )

    def __init__(self, config, namespace='', quit_check_callback=None):
        super(PostgreSQLCrashStorage, self).__init__(
            config,
            namespace=namespace,
            quit_check_callback=quit_check_callback
        )
        self.database = config.database_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.database,
            quit_check_callback=quit_check_callback
        )

    def save_processed(self, processed_crash):
        self.transaction(self._save_processed_transaction, processed_crash)

    def _save_processed_transaction(self, connection, processed_crash):
        self._save_processed_report(connection, processed_crash)

    def _save_processed_report(self, connection, processed_crash):
        """Here we INSERT or UPDATE a row in the reports table.
        This is the first stop before imported data gets into our normalized
        batch reporting (next table: reports_clean).

        At some point in the future, we will switch to using the raw_crash
        table and JSON transforms instead. This work will require an overhaul
        and optimization of the update_reports_clean() and
        update_reports_duplicates() stored procedures.

        We perform an UPSERT using a PostgreSQL CTE (aka WITH clause) that
        first tests whether a row exists and performs an UPDATE if it can, or
        it performs an INSERT. Because we're using raw SQL in this function,
        we've got a substantial parameterized query that requires two sets of
        parameters to be passed in via value_list. The value_list ends up
        having an extra crash_id added to the list, and being doubled before
        being passed to single_value_sql().

        The SQL produced isn't beautiful, but a side effect of the CTE style of
        UPSERT-ing. We look forward to SQL UPSERT being adopted as a
        first-class citizen in PostgreSQL.

        Similar code is present for _save_raw_crash() and
        _save_processed_crash(), but is much simpler seeming because there are
        far fewer columns being passed into the parameterized query.
        """

        column_list = []
        placeholder_list = []
        # create a list of values to go into the reports table
        value_list = []
        for pro_crash_name, report_name, length in (
            self._reports_table_mappings
        ):
            column_list.append(report_name)
            placeholder_list.append('%s')
            value = processed_crash[pro_crash_name]
            if isinstance(value, basestring) and length:
                    value_list.append(value[:length])
            else:
                value_list.append(value)

        def print_eq(a, b):
            # Helper for UPDATE SQL clause
            return a + ' = ' + b

        def print_as(a, b):
            # Helper for INSERT SQL clause
            return b + ' as ' + a

        crash_id = processed_crash['uuid']
        reports_table_name = (
            'reports_%s' % self._table_suffix_for_crash_id(crash_id)
        )
        upsert_sql = """
        WITH
        update_report AS (
            UPDATE %(table)s SET
                %(joined_update_clause)s
            WHERE uuid = %%s
            RETURNING id
        ),
        insert_report AS (
            INSERT INTO %(table)s (%(column_list)s)
            ( SELECT
                %(joined_select_clause)s
                WHERE NOT EXISTS (
                    SELECT uuid from %(table)s
                    WHERE
                        uuid = %%s
                    LIMIT 1
                )
            )
            RETURNING id
        )
        SELECT * from update_report
        UNION ALL
        SELECT * from insert_report
        """ % {
            'joined_update_clause':
            ", ".join(map(print_eq, column_list, placeholder_list)),
            'table': reports_table_name,
            'column_list': ', '. join(column_list),
            'joined_select_clause':
            ", ".join(map(print_as, column_list, placeholder_list)),
        }

        value_list.append(crash_id)
        value_list.extend(value_list)

        report_id = single_value_sql(connection, upsert_sql, value_list)
        return report_id

    @staticmethod
    def _table_suffix_for_crash_id(crash_id):
        """given an crash_id, return the name of its storage table"""
        crash_id_date = uuid_to_date(crash_id)
        previous_monday_date = (
            crash_id_date + datetime.timedelta(days=-crash_id_date.weekday())
        )
        return '%4d%02d%02d' % (previous_monday_date.year,
                                previous_monday_date.month,
                                previous_monday_date.day)

    def get_raw_crash(self, crash_id):
        """the default implementation of fetching a raw_crash

        parameters:
           crash_id - the id of a raw crash to fetch

        """
        return self.transaction(
            self._get_raw_crash_transaction,
            crash_id
        )

    def _get_raw_crash_transaction(self, connection, crash_id):
        raw_crash_table_name = (
            'raw_crashes_%s' % self._table_suffix_for_crash_id(crash_id)
        )
        fetch_sql = 'select raw_crash from %s where uuid = %%s' % \
                    raw_crash_table_name
        try:
            return single_value_sql(connection, fetch_sql, (crash_id,))
        except ProgrammingError as e:
            err = 'relation "%s" does not exist' % raw_crash_table_name
            if err in str(e):
                raise CrashIDNotFound(crash_id)
            raise
        except SQLDidNotReturnSingleValue:
            raise CrashIDNotFound(crash_id)

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """nota bene: this function does not save the dumps in PG, only
        the raw crash json is saved."""
        self.transaction(self._save_raw_crash_transaction, raw_crash, crash_id)

    def _save_raw_crash_transaction(self, connection, raw_crash, crash_id):
        raw_crash_table_name = (
            'raw_crashes_%s' % self._table_suffix_for_crash_id(crash_id)
        )

        upsert_sql = """
        WITH
        update_raw_crash AS (
            UPDATE %(table)s SET
                raw_crash = %%(raw_crash)s,
                date_processed = %%(date_processed)s
            WHERE uuid = %%(crash_id)s
            RETURNING 1
        ),
        insert_raw_crash AS (
            INSERT into %(table)s (uuid, raw_crash, date_processed)
            ( SELECT
                %%(crash_id)s as uuid,
                %%(raw_crash)s as raw_crash,
                %%(date_processed)s as date_processed
                WHERE NOT EXISTS (
                    SELECT uuid from %(table)s
                    WHERE
                        uuid = %%(crash_id)s
                    LIMIT 1
                )
            )
            RETURNING 2
        )
        SELECT * from update_raw_crash
        UNION ALL
        SELECT * from insert_raw_crash
        """ % {'table': raw_crash_table_name}

        values = {
            'crash_id': crash_id,
            'raw_crash': json.dumps(raw_crash),
            'date_processed': raw_crash["submitted_timestamp"]
        }
        execute_no_results(connection, upsert_sql, values)

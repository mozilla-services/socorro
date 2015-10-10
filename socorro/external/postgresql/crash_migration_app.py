# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Moves a limited list of crashes from a PostgreSQL database to any other
database. Main use is for local development, to move the results of fakedata
from PostgreSQL to another database.

By default, it is configured to move crashes from PostgreSQL to Elasticsearch.
'''

from socorro.app.fetch_transform_save_app import main
from socorro.collector.crashmover_app import RawAndProcessedCopierApp
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.external.postgresql.dbapi2_util import (
    SQLDidNotReturnSingleValue,
    execute_query_iter,
    single_value_sql,
)

from configman import Namespace

class DumbPostgreSQLCrashStorage(PostgreSQLCrashStorage):
    '''Dumb version of the PostgreSQL crashstorage class that fetches data
    from the non-versioned tables. '''

    def _get_raw_crash_transaction(self, connection, crash_id):
        fetch_sql = 'select raw_crash from raw_crashes where uuid = %s'
        try:
            return single_value_sql(connection, fetch_sql, (crash_id,))
        except SQLDidNotReturnSingleValue:
            raise CrashIDNotFound(crash_id)

    def _get_processed_crash_transaction(self, connection, crash_id):
        fetch_sql = (
            'select processed_crash from processed_crashes where uuid = %s'
        )
        try:
            return single_value_sql(connection, fetch_sql, (crash_id,))
        except SQLDidNotReturnSingleValue:
            raise CrashIDNotFound(crash_id)


class CrashMigrationApp(RawAndProcessedCopierApp):
    app_name = 'crash_migration'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()
    required_config.add_option(
        'no_dumps',
        doc="don't copy binary dumps",
        default=True
    )

    @staticmethod
    def get_application_defaults():
        return {
            'source.crashstorage_class': DumbPostgreSQLCrashStorage,
            'destination.crashstorage_class':
                'socorro.external.es.crashstorage.'
                'ESCrashStorageNoStackwalkerOutput',
            "worker_task.worker_task_impl":
                "socorro.app.fts_worker_methods.CopyAllWorkerMethod",
            "number_of_submissions": "all",
        }

    def _create_iter(self):
        connection = self.source.database.connection()
        sql = 'select uuid from raw_crashes;'
        return execute_query_iter(connection, sql)


if __name__ == '__main__':
    main(CrashMigrationApp)

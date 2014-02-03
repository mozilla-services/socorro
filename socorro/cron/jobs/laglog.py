# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""an app to monitor and report on replication lag in PG databases"""

from configman import Namespace

from socorro.cron.base import PostgresTransactionManagedCronApp
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
)


#==============================================================================
class LagLog(PostgresTransactionManagedCronApp):

    app_name = 'LagLog'
    app_version = '0.1'
    app_description = __doc__

    #--------------------------------------------------------------------------
    required_config = Namespace()
    required_config.add_option(
        'transaction_executor',
        default='socorro.database.transaction_executor.TransactionExecutor',
        doc='the transaction class to use',
        reference_value_from='resource.postgresql',
    )

    insert_sql = (
        "INSERT INTO laglog (replica_name, moment, lag, master) "
        "VALUES (%s, %s, %s, %s)"
    )
    each_server_sql = (
        "SELECT NOW(), client_addr, sent_location, replay_location "
        "FROM pg_stat_replication"
    )

    #--------------------------------------------------------------------------
    @staticmethod
    def xlog_transform(xlog):
        logid, offset = xlog.split('/')
        return int('ffffffff', 16) * int(logid, 16) + int(offset, 16)

    #--------------------------------------------------------------------------
    def run(self, connection_ignored):

        database_transaction = self.config.transaction_executor(
            self.config,
            self.config.database
        )

        each_server = database_transaction(
            execute_query_fetchall,
            self.each_server_sql
        )

        self.config.logger.debug(
            'replication database servers: %s',
            each_server
        )
        for now, client_addr, sent_location, replay_location in each_server:
            sent_location = self.xlog_transform(sent_location)
            replay_location = self.xlog_transform(replay_location)
            lag = sent_location - replay_location
            self.config.logger.debug(
                '%s %s %s %s',
                client_addr,
                now,
                lag,
                self.config.database.database_name
            )
            database_transaction(
                execute_no_results,
                self.insert_sql,
                (client_addr, now, lag, self.config.database.database_name)
            )

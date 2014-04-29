# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""an app to monitor and report on replication lag in PG databases"""

from crontabber.base import BaseCronApp
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
)
from crontabber.mixins import with_postgres_transactions


#==============================================================================
@with_postgres_transactions()
class LagLog(BaseCronApp):

    app_name = 'LagLog'
    app_version = '0.1'
    app_description = __doc__

    #--------------------------------------------------------------------------
    insert_sql = (
        "INSERT INTO lag_log (replica_name, moment, lag, master) "
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
    def run(self):
        each_server = self.database_transaction_executor(
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
            self.database_transaction_executor(
                execute_no_results,
                self.insert_sql,
                (client_addr, now, lag, self.config.database.database_name)
            )

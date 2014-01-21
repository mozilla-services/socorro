#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""an app to monitor and report on replication lag in PG databases"""

# This app can be invoked like this:
#     .../socorro/cron/laglog_app.py --help

from socorro.app.generic_app import App, main
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
)
from socorro.database.transaction_executor import TransactionExecutor

from configman import Namespace


#==============================================================================
class LagLogApp(App):
    app_name = 'LagLog'
    app_version = '0.1'
    app_description = __doc__

    #--------------------------------------------------------------------------
    required_config = Namespace()
    required_config.add_option(
        'database',
        default=
            'socorro.external.postgresql.connection_context.ConnectionContext',
        doc='the database class to use'
    )
    required_config.add_option(
        'transaction_executor',
        default='socorro.database.transaction_executor.TransactionExecutor',
        doc='the transaction class to use'
    )

    #--------------------------------------------------------------------------
    def xlog_transform(xlog):
        logid, offset = xlog.split('/')
        return (int('ffffffff', 16) * int(logid, 16)) + int(offset, 16)

    #--------------------------------------------------------------------------
    def main(self):
        
        database_transaction = self.transaction_executor(
            self.config,
            self.config.database
        )
        
        insert_sql = (
            "insert into laglog ('replica_name, moment, lag, master') "
            "values %s, %s, %s, %s"
        )
        each_server_sql = (
            "select now(), client_addr, sent_location, replay_location "
            "from pg_stat_replication"
        )
        each_server = database_transaction(
            execute_query_fetchall,
            each_server_sql
        )
        self.logger.debug('replication database servers: %s', str(each_server))
        for now, client_addr, sent_location, replay_location in each_server:
            sent_location = xlog_transform(sent_location)
            replay_location = xlog_transform(replay_location)
            lag = sent_location - replay_location
            self.logger.debug(
                '%s %s %s %s',
                client_addr, 
                now, 
                lag, 
                self.config.database.database_name
            )
            database_transaction(
                execute_no_results, 
                insert_sql, 
                (client_addr, now, lag, self.config.database.database_name)
            )
            

if __name__ == '__main__':
    main(LagLogApp)

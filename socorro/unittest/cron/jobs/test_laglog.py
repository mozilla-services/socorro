# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from mock import Mock, call, patch
from datetime import datetime

from socorro.cron.jobs.laglog_app import LagLog
from socorro.lib.util import SilentFakeLogger

from configman.dotdict import DotDict


class TestLagLog(unittest.TestCase):
    
    def _get_mocked_config(self):
        config = DotDict()
        config.database = Mock()
        config.transaction_executor = Mock()
        config.logger = SilentFakeLogger()
        self.config = config
        
    
    def test_run(self):
        self._get_mocked_config()
        database_transaction_return_value = [
            [
                (datetime(2014, 01, 22, 01, 13, 38), '192.168.168.140', 
                     '1798/552C598', '1798/5527C40'),
                (datetime(2014, 01, 22, 01, 13, 38), '192.168.168.141', 
                     '1798/552C598', '1798/5527C40'),
                (datetime(2014, 01, 22, 01, 13, 38), '192.168.168.142', 
                     '1798/552C598', '1798/5527C40'),
            ],
            None,
            None,
            None,
        ]
        self.config.transaction_executor.return_value.side_effect = \
            database_transaction_return_value
        laglog_app = LagLog(self.config, None)
        laglog_app.run(None)  # totally faked and unused connection
        trans_executor_calls = [
            call(
                self.config.database.return_value,
                laglog_app._each_server_sql
            ),
            call(
                self.config.database.return_value,
                laglog_app._insert_sql,
                database_transaction_return_value[0],
            ),
            call(
                self.config.database.return_value,
                laglog_app._insert_sql,
                database_transaction_return_value[1],
            ),
            call(
                self.config.database.return_value,
                laglog_app._insert_sql,
                database_transaction_return_value[2],
            ),
        ]
        self.config.transaction_executor.has_calls(
            trans_executor_calls
        )

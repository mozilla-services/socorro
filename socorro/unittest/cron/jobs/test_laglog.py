# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
import datetime

from socorro.cron.jobs.laglog import LagLog
from socorro.lib.util import SilentFakeLogger

from configman.dotdict import DotDict


class TestLagLog(unittest.TestCase):

    def _get_mocked_config(self):
        config = DotDict()
        config.database = mock.Mock()
        config.transaction_executor = mock.Mock()
        config.logger = SilentFakeLogger()
        self.config = config

    def test_run(self):
        self._get_mocked_config()
        database_transaction_return_value = [
            [
                (
                    datetime.datetime(2014, 01, 22, 01, 13, 38),
                    '192.168.168.140',
                    '1798/552C598',
                    '1798/5527C40'
                ),
                (
                    datetime.datetime(2014, 01, 22, 01, 13, 38),
                    '192.168.168.141',
                    '1798/552C598',
                    '1798/5527C40'
                ),
                (
                    datetime.datetime(2014, 01, 22, 01, 13, 38),
                    '192.168.168.142',
                    '1798/552C598',
                    '1798/5527C40'
                ),
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
            mock.call(
                self.config.database.return_value,
                laglog_app.each_server_sql
            ),
            mock.call(
                self.config.database.return_value,
                laglog_app.insert_sql,
                database_transaction_return_value[0],
            ),
            mock.call(
                self.config.database.return_value,
                laglog_app.insert_sql,
                database_transaction_return_value[1],
            ),
            mock.call(
                self.config.database.return_value,
                laglog_app.insert_sql,
                database_transaction_return_value[2],
            ),
        ]
        self.config.transaction_executor.has_calls(
            trans_executor_calls
        )

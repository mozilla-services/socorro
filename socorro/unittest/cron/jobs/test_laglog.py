# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import mock

from socorro.cron.jobs.laglog import LagLog
from socorro.lib.util import SilentFakeLogger
from socorro.unittest.testbase import TestCase
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)

from configman.dotdict import DotDict


class TestLagLog(TestCase):

    def get_standard_config(self):
        return get_config_manager_for_crontabber().get_config()

    def _get_mocked_config(self):
        config = DotDict()
        config.database = DotDict()
        config.database.database_class = mock.Mock()
        config.database.database_transaction_executor_class = mock.Mock()
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
        faked_transaction_executor = mock.MagicMock()
        self.config.database.database_transaction_executor_class \
            .return_value = faked_transaction_executor
        faked_transaction_executor.return_value.side_effect = \
            database_transaction_return_value
        faked_connection = mock.Mock()
        self.config.database.database_class.return_value.return_value = \
            faked_connection
        laglog_app = LagLog(self.config, None)
        laglog_app.run()
        trans_executor_calls = [
            mock.call(
                faked_connection,
                laglog_app.each_server_sql
            ),
            mock.call(
                faked_connection,
                laglog_app.insert_sql,
                database_transaction_return_value[0],
            ),
            mock.call(
                faked_connection,
                laglog_app.insert_sql,
                database_transaction_return_value[1],
            ),
            mock.call(
                faked_connection,
                laglog_app.insert_sql,
                database_transaction_return_value[2],
            ),
        ]
        faked_transaction_executor.has_calls(
            trans_executor_calls
        )

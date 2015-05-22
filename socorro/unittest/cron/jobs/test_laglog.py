# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import mock
from nose.tools import eq_

from socorro.cron.jobs.laglog import LagLog
from socorro.unittest.testbase import TestCase
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
    execute_query_fetchall,
)

from configman.dotdict import DotDict


class TestLagLog(TestCase):

    def setUp(self):
        super(TestLagLog, self).setUp()

        config = DotDict()
        config.database = DotDict()
        config.database.database_name = "mydatabase"
        config.database.database_class = mock.Mock()
        config.database.database_transaction_executor_class = mock.Mock()
        self.mocked_logger = mock.Mock()
        config.logger = self.mocked_logger
        self.config = config

    def get_standard_config(self):
        return get_config_manager_for_crontabber().get_config()

    def test_run(self):
        inserts = []

        def mocked_transaction_executor(function, sql, *args):
            if function == execute_query_fetchall:
                assert sql.startswith('SELECT')
                assert not args
                return [
                    (
                        datetime.datetime(2014, 01, 22, 01, 13, 38),
                        '192.168.168.140',
                        '1798/552C598',
                        '1798/5527C40'
                    ),
                    (
                        datetime.datetime(2014, 01, 22, 01, 13, 39),
                        '192.168.168.140',
                        None,
                        '1798/5527C40'
                    ),
                    (
                        datetime.datetime(2014, 01, 22, 01, 13, 40),
                        '192.168.168.140',
                        '1798/552C598',
                        None
                    ),
                ]
            elif function == execute_no_results:
                assert sql.startswith('INSERT INTO')
                inserts.append(args)
            else:
                raise NotImplementedError

        faked_transaction_executor = mock.MagicMock()
        self.config.database.database_transaction_executor_class \
            .return_value = faked_transaction_executor
        faked_transaction_executor.side_effect = mocked_transaction_executor

        laglog_app = LagLog(self.config, None)
        laglog_app.run()
        eq_(len(inserts), 1)
        first, = inserts[0]
        ip, date, bytes, database_name = first
        eq_(ip, '192.168.168.140')
        eq_(date, datetime.datetime(2014, 01, 22, 01, 13, 38))

        logid, offset = '1798/552C598'.split('/')
        sent = int('ffffffff', 16) * int(logid, 16) + int(offset, 16)
        logid, offset = '1798/5527C40'.split('/')
        replay = int('ffffffff', 16) * int(logid, 16) + int(offset, 16)
        eq_(bytes, sent - replay)
        eq_(database_name, self.config.database.database_name)

        self.config.logger.warning.assert_any_call(
            'replay_location comes back as NULL from pg_stat_replication '
            '(now:2014-01-22 01:13:40, database:mydatabase)'
        )
        self.config.logger.warning.assert_any_call(
            'sent_location comes back as NULL from pg_stat_replication '
            '(now:2014-01-22 01:13:39, database:mydatabase)'
        )

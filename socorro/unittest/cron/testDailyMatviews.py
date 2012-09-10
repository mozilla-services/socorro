# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import unittest
import psycopg2
import socorro.cron.dailyMatviews  # needed for Mock
import socorro.cron.dailyMatviews as dailyMatviews

from socorro.lib.datetimeutil import utc_now

from socorro.unittest.config.commonconfig import databaseHost
from socorro.unittest.config.commonconfig import databaseName
from socorro.unittest.config.commonconfig import databaseUserName
from socorro.unittest.config.commonconfig import databasePassword

from mock import patch


class mock_connection:
    def __init__(self, c):
        self.c = c

    def _void(self):
        pass

    commit = rollback = _void

    def cursor(self):
        return self.c


class mock_psycopg2:
    InternalError = Exception

    def __init__(self, cursor):
        self.cursor = cursor

    def connect(self, *args, **kwargs):
        return mock_connection(self.cursor)


class mock_cursor:
    def __init__(self, returns):
        self.returns = returns
        self.called = []

    def callproc(self, name, params):
        self.name = name
        self.called.append(name)

    def fetchone(self):
        if self.name in self.returns:
            return self.returns[self.name]
        return (True,)

    def execute(self, sql, params):
        pass


class TestCase(unittest.TestCase):
    def setUp(self):
        self.config = {
          'databaseHost': '',
          'databasePassword': '',
          'databaseName': '',
          'databaseUserName': '',
        }

    def test_failing__update_product_versions(self):
        cursor = mock_cursor({
          'update_product_versions': (False,),
        })
        dailyMatviews.psycopg2 = mock_psycopg2(cursor)
        with patch('socorro.cron.dailyMatviews.logger') as mock_logger:
            dailyMatviews.update(self.config, 'some date')
            self.assertEqual(cursor.called, ['update_product_versions',
              'update_signatures', 'update_os_versions', 'update_tcbs',
              'update_adu', 'update_hang_report',
              'update_rank_compare', 'update_nightly_builds',
              'update_build_adu', 'update_crashes_by_user',
              'update_crashes_by_user_build', 'update_correlations',
              'update_home_page_graph', 'update_home_page_graph_build',
              'update_tcbs_build', 'update_explosiveness'])
            self.assertEqual(mock_logger.info.call_count, 16)
            self.assertEqual(mock_logger.warn.call_count, 1)
            self.assertEqual(mock_logger.error.call_count, 0)

    def test_all_works(self):
        cursor = mock_cursor({})
        dailyMatviews.psycopg2 = mock_psycopg2(cursor)
        with patch('socorro.cron.dailyMatviews.logger') as mock_logger:
            dailyMatviews.update(self.config, 'some date')
            self.assertEqual(mock_logger.info.call_count, 16)
            self.assertEqual(mock_logger.warn.call_count, 0)
            self.assertEqual(mock_logger.error.call_count, 0)

    def test_mock_internal_error(self):
        cursor = mock_cursor({
          'update_signatures': psycopg2.InternalError,
        })
        dailyMatviews.psycopg2 = mock_psycopg2(cursor)
        with patch('socorro.cron.dailyMatviews.logger') as mock_logger:
            dailyMatviews.update(self.config, 'some date')
            self.assertEqual(mock_logger.info.call_count, 16)
            self.assertEqual(mock_logger.warn.call_count, 0)
            self.assertEqual(mock_logger.error.call_count, 1)

    # failure is OK for some functions
    def test_failing__update_adu(self):
        cursor = mock_cursor({
          'update_adu': (False,),
        })
        dailyMatviews.psycopg2 = mock_psycopg2(cursor)
        with patch('socorro.cron.dailyMatviews.logger') as mock_logger:
            dailyMatviews.update(self.config, 'some date')
            self.assertEqual(mock_logger.error.call_count, 0)

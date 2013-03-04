# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import unittest

from socorro.lib.util import SilentFakeLogger, DotDict
from socorro.external.hb.crashstorage import HBaseCrashStorage, CrashIDNotFound
from socorro.database.transaction_executor import TransactionExecutor


class TestCrashStorage(unittest.TestCase):
    def setUp(self):
        self.context = mock.MagicMock()
        self.context.__enter__.return_value = self.context
        config = DotDict({
          'hbase_host': 'host',
          'database_name': 'name',
          'hbase_port': 9090,
          'hbase_timeout': 9000,
          'number_of_retries': 2,
          'logger': SilentFakeLogger(),
          'hbase_connection_context_class': mock.Mock(
              return_value=self.context
          ),
          'forbidden_keys': [],
          'transaction_executor_class': TransactionExecutor,
          'new_crash_limit': 10 ** 6
        })
        self.storage = HBaseCrashStorage(config)

    def test_close(self):
        self.storage.close()
        self.assertEqual(self.storage.hbase.close.call_count, 1)

    def test_save_processed(self):
        self.storage.save_processed({
            "uuid": "936ce666-ff3b-4c7a-9674-367fe2120408",
            "completeddatetime": "2012-04-08 10:56:50.902884"
        })
        with self.storage.hbase() as conn:
            self.assertEqual(conn.client.mutateRow.call_count, 2)

    def test_save_raw_crash(self):
        self.storage.save_raw_crash({
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
        }, {}, "0bba929f-8721-460c-dead-a43c20071027")
        with self.storage.hbase() as conn:
            self.assertEqual(conn.client.mutateRow.call_count, 5)

    def test_save_raw_crash_hang(self):
        self.storage.save_raw_crash({
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00",
            "HangID": "?"
        }, {}, "0bba929f-8721-460c-dead-a43c20071027")
        with self.storage.hbase() as conn:
            self.assertEqual(conn.client.mutateRow.call_count, 7)

    def test_get_raw_dumps(self):
        self.storage.get_raw_dumps("936ce666-ff3b-4c7a-9674-367fe2120408")
        with self.storage.hbase() as conn:
            self.assertEqual(conn.client.getRowWithColumns.call_count, 1)

    def test_get_raw_dumps_as_files(self):
        self.storage.get_raw_dumps_as_files(
            "936ce666-ff3b-4c7a-9674-367fe2120408")
        with self.storage.hbase() as conn:
            self.assertEqual(conn.client.getRowWithColumns.call_count, 1)

    def test_get_processed(self):
        with self.storage.hbase() as conn:
            conn.client.getRowWithColumns.return_value = []
            self.assertRaises(
                CrashIDNotFound,
                self.storage.get_processed,
                "936ce666-ff3b-4c7a-9674-367fe2120408"
            )

    def test_new_crashes(self):
        self.storage._salted_scanner_iterable = mock.Mock(
            return_value=iter([])
        )
        self.assertEqual(list(self.storage.new_crashes()), [])

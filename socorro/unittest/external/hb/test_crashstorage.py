# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import unittest
import json

from socorro.lib.util import SilentFakeLogger, DotDict
from socorro.external.crashstorage_base import Redactor
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
          'transaction_executor_class': TransactionExecutor,
          'new_crash_limit': 10 ** 6,
          'redactor_class': Redactor,
          'forbidden_keys': Redactor.required_config.forbidden_keys.default,
        })
        self.storage = HBaseCrashStorage(config)

    def _fake_processed_crash(self):
        d = DotDict()
        # these keys survive redaction
        d.a = DotDict()
        d.a.b = DotDict()
        d.a.b.c = 11
        d.sensitive = DotDict()
        d.sensitive.x = 2
        d.not_url = 'not a url'

        return d

    def _fake_redacted_processed_crash(self):
        d =  self._fake_unredacted_processed_crash()
        del d.url
        del d.email
        del d.user_id
        del d.exploitability
        del d.json_dump.sensitive
        del d.upload_file_minidump_flash1.json_dump.sensitive
        del d.upload_file_minidump_flash2.json_dump.sensitive
        del d.upload_file_minidump_browser.json_dump.sensitive

        return d

    def _fake_unredacted_processed_crash(self):
        d = self._fake_processed_crash()

        # these keys do not survive redaction
        d['url'] = 'http://very.embarassing.com'
        d['email'] = 'lars@fake.com'
        d['user_id'] = '3333'
        d['exploitability'] = 'yep'
        d.json_dump = DotDict()
        d.json_dump.sensitive = 22
        d.upload_file_minidump_flash1 = DotDict()
        d.upload_file_minidump_flash1.json_dump = DotDict()
        d.upload_file_minidump_flash1.json_dump.sensitive = 33
        d.upload_file_minidump_flash2 = DotDict()
        d.upload_file_minidump_flash2.json_dump = DotDict()
        d.upload_file_minidump_flash2.json_dump.sensitive = 33
        d.upload_file_minidump_browser = DotDict()
        d.upload_file_minidump_browser.json_dump = DotDict()
        d.upload_file_minidump_browser.json_dump.sensitive = DotDict()
        d.upload_file_minidump_browser.json_dump.sensitive.exploitable = 55
        d.upload_file_minidump_browser.json_dump.sensitive.secret = 66

        return d

    def _fake_unredacted_processed_crash_as_string(self):
        d = self._fake_unredacted_processed_crash()
        s = json.dumps(d)
        return s


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

    def test_get_unredacted_processed(self):
        faked_hb_row_object = DotDict()
        faked_hb_row_object.columns = DotDict()
        faked_hb_row_object.columns['processed_data:json'] = DotDict()
        faked_hb_row_object.columns['processed_data:json'].value = \
            self._fake_unredacted_processed_crash_as_string()

        processed_crash = DotDict()
        with self.storage.hbase() as conn:
            conn.client.getRowWithColumns.return_value = [faked_hb_row_object]

            processed_crash = self.storage.get_unredacted_processed(
                "936ce666-ff3b-4c7a-9674-367fe2120408"
            )
            self.assertEqual(
                processed_crash,
                self._fake_unredacted_processed_crash()
            )

    def test_get_processed(self):
        faked_hb_row_object = DotDict()
        faked_hb_row_object.columns = DotDict()
        faked_hb_row_object.columns['processed_data:json'] = DotDict()
        faked_hb_row_object.columns['processed_data:json'].value = \
            self._fake_unredacted_processed_crash_as_string()

        processed_crash = DotDict()
        with self.storage.hbase() as conn:
            conn.client.getRowWithColumns.return_value = [faked_hb_row_object]

            processed_crash = self.storage.get_processed(
                "936ce666-ff3b-4c7a-9674-367fe2120408"
            )
            self.assertEqual(
                processed_crash,
                self._fake_redacted_processed_crash()
            )


    def test_get_processed_failure(self):
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

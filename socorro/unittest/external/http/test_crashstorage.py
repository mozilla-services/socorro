# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import patch, Mock, MagicMock
import unittest
import socket

from socorro.lib.util import SilentFakeLogger, DotDict

from socorro.external.http.crashstorage import HTTPPOSTCrashStorage
from socorro.database.transaction_executor import (
    TransactionExecutor,
    TransactionExecutorWithLimitedBackoff
)


class TestCrashStorage(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock()
        self.config.__enter__.return_value = self.config
        config = DotDict({
            'url': 'http://totally.fake.url/submit',
            'transaction_executor_class': TransactionExecutor,
            'timeout': 1,
            'dump_field_name': 'upload_file_minidump',
            'logger': Mock(),
            'redactor_class': Mock(),
        })
        self.storage = HTTPPOSTCrashStorage(config)

    def setUpForTimeout(self):
        self.config = MagicMock()
        self.config.__enter__.return_value = self.config
        config = DotDict({
            'url': 'http://totally.fake.url/submit',
            'transaction_executor_class': TransactionExecutorWithLimitedBackoff,
            'backoff_delays': [1, 1],
            'wait_log_interval': 10,
            'timeout': 1,
            'dump_field_name': 'upload_file_minidump',
            'logger': Mock(),
            'redactor_class': Mock(),
        })
        self.storage = HTTPPOSTCrashStorage(config)


    def test_save_raw_crash(self):
        raw_crash = {
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00",
            "HangID": "?",
            "Product": "FireSquid",
            "Version": "-33",
        }
        dumps = {
            'upload_file_minidump': 'dump #1',
            'browser': 'dump #2'
        }
        crash_id = "0bba929f-8721-460c-dead-a43c20071027"
        m_quit_check = Mock()
        with patch("socorro.external.http.crashstorage.poster") as m_poster:
            with patch("socorro.external.http.crashstorage.urllib2") as m_urllib:
                m_poster.encode.multipart_encode.return_value = (1, 2)
                m_urllib.Request.return_value = 23

                self.storage.save_raw_crash(raw_crash, dumps, crash_id)

                self.assertEqual(m_poster.encode.MultipartParam.call_count, 2)
                m_poster.encode.multipart_encode.assert_called_once_with(
                    raw_crash
                )
                m_urllib.Request.assert_called_once_with(
                    self.storage.config.url,
                    1,
                    2
                )
                m_urllib.urlopen.assert_called_once_with(
                    23
                )

    def test_save_raw_crash_with_timeouts_to_falure(self):
        self.setUpForTimeout()

        raw_crash = {
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00",
            "HangID": "?",
            "Product": "FireSquid",
            "Version": "-33",
        }
        dumps = {
            'upload_file_minidump': 'dump #1',
            'browser': 'dump #2'
        }
        crash_id = "0bba929f-8721-460c-dead-a43c20071027"
        m_quit_check = Mock()
        with patch("socorro.external.http.crashstorage.poster") as m_poster:
            with patch("socorro.external.http.crashstorage.urllib2") as m_urllib:
                m_poster.encode.multipart_encode.return_value = (1, 2)
                m_urllib.Request.return_value = 23
                m_urllib.urlopen.side_effect = socket.timeout

                self.assertRaises(
                    socket.timeout,
                    self.storage.save_raw_crash,
                    raw_crash, dumps, crash_id,
                )

                self.assertEqual(m_poster.encode.MultipartParam.call_count, 4)
                self.assertEqual(m_urllib.Request.call_count, 2)
                self.assertEqual(m_urllib.urlopen.call_count, 2)




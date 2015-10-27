# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import json
import tempfile
import shutil
from os.path import join

import boto.exception

from socorro.lib.util import DotDict
from socorro.external.crashstorage_base import (
    Redactor,
    MemoryDumpsMapping
)
from socorro.external.boto.connection_context import (
    ConnectionContext
)
from socorro.external.boto.crashstorage import (
    BotoS3CrashStorage,
    SupportReasonAPIStorage
)
from socorro.database.transaction_executor import (
    TransactionExecutor,
    TransactionExecutorWithLimitedBackoff,
)
from socorro.external.crashstorage_base import CrashIDNotFound
import socorro.unittest.testbase


a_raw_crash = {
    "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
}
a_raw_crash_as_string = json.dumps(a_raw_crash)


class ABadDeal(Exception):
    pass

class ConditionallyABadDeal(Exception):
    pass

ConnectionContext.operational_exceptions = (ABadDeal, )
ConnectionContext.conditional_exceptions = (ConditionallyABadDeal, )


class TestCase(socorro.unittest.testbase.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestCase, cls).setUpClass()
        cls.TEMPDIR = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        super(TestCase, cls).tearDownClass()
        shutil.rmtree(cls.TEMPDIR)

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
        d = self._fake_unredacted_processed_crash()
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

    def setup_mocked_s3_storage(
            self,
            executor=TransactionExecutor,
            executor_for_gets=TransactionExecutor,
            storage_class='BotoS3CrashStorage',
            host='',
            port=0):

        config = DotDict({
            'source': {
                'dump_field': 'dump'
            },
            'transaction_executor_class': executor,
            'transaction_executor_class_for_get': executor_for_gets,
            'resource_class': ConnectionContext,
            'backoff_delays': [0, 0, 0],
            'redactor_class': Redactor,
            'forbidden_keys': Redactor.required_config.forbidden_keys.default,
            'logger': mock.Mock(),
            'host': host,
            'port': port,
            'access_key': 'this is the access key',
            'secret_access_key': 'secrets',
            'temporary_file_system_storage_path': self.TEMPDIR,
            'dump_file_suffix': '.dump',
            'bucket_name': 'mozilla-support-reason',
            'prefix': 'dev',
            'calling_format': mock.Mock()
        })
        if storage_class == 'BotoS3CrashStorage':
            config.bucket_name = 'crash_storage'
            s3 = BotoS3CrashStorage(config)
        elif storage_class == 'SupportReasonAPIStorage':
            s3 = SupportReasonAPIStorage(config)
        s3_conn = s3.connection_source
        s3_conn._connect_to_endpoint = mock.Mock()
        s3_conn._mocked_connection = s3_conn._connect_to_endpoint.return_value
        s3_conn._calling_format.return_value = mock.Mock()
        s3_conn._CreateError = mock.Mock()
        s3_conn._S3ResponseError = mock.Mock()
        s3_conn._open = mock.MagicMock()

        return s3

    def assert_s3_connection_parameters(self, boto_s3_store, host='', port=0):
        kwargs = {
            "aws_access_key_id": boto_s3_store.config.access_key,
            "aws_secret_access_key": boto_s3_store.config.secret_access_key,
            "is_secure": True,
            "calling_format": boto_s3_store.connection_source._calling_format.return_value
        }
        if host:
            kwargs['host'] = host
        if port:
            kwargs['port'] = port
        boto_s3_store.connection_source._connect_to_endpoint.assert_called_with(**kwargs)

    def test_connect_with_host_port(self):
        boto_s3_store = self.setup_mocked_s3_storage(
            host='somewhere.sometime.someplace',
            port=666,
        )
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            MemoryDumpsMapping(),
            "0bba929f-8721-460c-dead-a43c20071027"
        )
        self.assert_s3_connection_parameters(
            boto_s3_store,
            host='somewhere.sometime.someplace',
            port=666,
        )

    def test_save_raw_crash_1(self):
        boto_s3_store = self.setup_mocked_s3_storage()

        # the tested call
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            MemoryDumpsMapping(),
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        bucket_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 2)
        bucket_mock.new_key.assert_has_calls(
            [
                mock.call('dev/v1/raw_crash/0bba929f-8721-460c-dead-a43c20071027'),
                mock.call('dev/v1/dump_names/0bba929f-8721-460c-dead-a43c20071027'),
            ],
            any_order=True,
        )

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            2
        )
        storage_key_mock.set_contents_from_string.assert_has_calls(
            [
                mock.call(
                    '{"submitted_timestamp": '
                    '"2013-01-09T22:21:18.646733+00:00"}'
                ),
                mock.call('[]'),
            ],
            any_order=True,
        )

    def test_save_raw_crash_2(self):
        boto_s3_store = self.setup_mocked_s3_storage()

        # the tested call
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            MemoryDumpsMapping(
                {'dump': 'fake dump', 'flash_dump': 'fake flash dump'}
            ),
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        bucket_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 4)
        bucket_mock.new_key.assert_has_calls(
            [
                mock.call('dev/v1/raw_crash/0bba929f-8721-460c-dead-a43c20071027'),
                mock.call('dev/v1/dump_names/0bba929f-8721-460c-dead-a43c20071027'),
                mock.call('dev/v1/dump/0bba929f-8721-460c-dead-a43c20071027'),
                mock.call('dev/v1/flash_dump/0bba929f-8721-460c-dead-a43c20071027'),
            ],
            any_order=True,
        )

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            4
        )
        storage_key_mock.set_contents_from_string.assert_has_calls(
            [
                mock.call(
                    '{"submitted_timestamp": '
                    '"2013-01-09T22:21:18.646733+00:00"}'
                ),
                mock.call('["flash_dump", "dump"]'),
                mock.call('fake dump'),
                mock.call('fake flash dump'),
            ],
            any_order=True,
        )

    def test_save_raw_crash_3_failing_get_bucket(self):
        boto_s3_store = self.setup_mocked_s3_storage()
        boto_s3_store.connection_source._S3ResponseError = ABadDeal

        boto_s3_store.connection_source._mocked_connection.get_bucket.side_effect = (
            boto_s3_store.connection_source._S3ResponseError
        )

        # the tested call
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            MemoryDumpsMapping(
                {'dump': 'fake dump', 'flash_dump': 'fake flash dump'}
            ),
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.create_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )
        boto_s3_store.connection_source._mocked_connection.create_bucket.assert_called_with(
            'crash_storage'
        )

        bucket_mock = boto_s3_store.connection_source._mocked_connection.create_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 4)
        bucket_mock.new_key.assert_has_calls(
            [
                mock.call('dev/v1/raw_crash/0bba929f-8721-460c-dead-a43c20071027'),
                mock.call('dev/v1/dump_names/0bba929f-8721-460c-dead-a43c20071027'),
                mock.call('dev/v1/dump/0bba929f-8721-460c-dead-a43c20071027'),
                mock.call('dev/v1/flash_dump/0bba929f-8721-460c-dead-a43c20071027'),
            ],
            any_order=True,
        )

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            4
        )
        storage_key_mock.set_contents_from_string.assert_has_calls(
            [
                mock.call(
                    '{"submitted_timestamp": '
                    '"2013-01-09T22:21:18.646733+00:00"}'
                ),
                mock.call('["flash_dump", "dump"]'),
                mock.call('fake dump'),
                mock.call('fake flash dump'),
            ],
            any_order=True,
        )

    def test_save_processed(self):
        boto_s3_store = self.setup_mocked_s3_storage()

        # the tested call
        boto_s3_store.save_processed({
            "uuid": "0bba929f-8721-460c-dead-a43c20071027",
            "completeddatetime": "2012-04-08 10:56:50.902884",
            "signature": 'now_this_is_a_signature'
        })

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        bucket_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 1)
        bucket_mock.new_key.assert_has_calls(
            [
                mock.call(
                    'dev/v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027'
                ),
            ],
        )

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            1
        )
        storage_key_mock.set_contents_from_string.assert_has_calls(
            [
                mock.call(
                    '{"signature": "now_this_is_a_signature", "uuid": '
                    '"0bba929f-8721-460c-dead-a43c20071027", "completed'
                    'datetime": "2012-04-08 10:56:50.902884"}'
                ),
            ],
            any_order=True,
        )

    def test_save_processed_support_reason(self):
        boto_s3_store = self.setup_mocked_s3_storage(
            storage_class='SupportReasonAPIStorage'
        )

        # the tested call
        report = {
            'uuid': '3c61f81e-ea2b-4d24-a3ce-6bb9d2140915',
            'classifications': {
                'support': {
                    'classification': 'SIGSEGV'
                }
            }
        }
        boto_s3_store.save_processed(report)

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'mozilla-support-reason'
        )

        bucket_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 1)
        bucket_mock.new_key.assert_has_calls(
            [
                mock.call(
                    'dev/v1/support_reason/3c61f81e-ea2b-4d24-a3ce-6bb9d2140915'
                ),
            ],
        )

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            1
        )

        storage_key_mock.set_contents_from_string.assert_has_calls(
            [
                mock.call(
                    '{"reasons": ["SIGSEGV"],'
                    ' "crash_id": "3c61f81e-ea2b-4d24-a3ce-6bb9d2140915"}'
                ),
            ],
            any_order=True,
        )

    def test_save_processed_support_reason_bad_classification(self):
        boto_s3_store = self.setup_mocked_s3_storage(
            storage_class='SupportReasonAPIStorage'
        )

        # the tested call
        report = {
            'uuid': '3c61f81e-ea2b-4d24-a3ce-6bb9d2140915',
            'classifications': {
                'support': {
                    'not_a_thing': 'blah'
                }
            }
        }
        boto_s3_store.save_processed(report)

        # this should be entirely rejected
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 0)

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 0)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            0
        )

        bucket_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 0)

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            0
        )

    def test_save_raw_and_processed(self):
        boto_s3_store = self.setup_mocked_s3_storage()

        # the tested call
        boto_s3_store.save_raw_and_processed(
            {
                "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
            },
            None,
            {
                "uuid": "0bba929f-8721-460c-dead-a43c20071027",
                "completeddatetime": "2012-04-08 10:56:50.902884",
                "signature": 'now_this_is_a_signature'
            },
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        bucket_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 1)
        bucket_mock.new_key.assert_has_calls(
            [
                mock.call(
                    'dev/v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027'
                ),
            ],
        )

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            1
        )
        storage_key_mock.set_contents_from_string.assert_has_calls(
            [
                mock.call(
                    '{"signature": "now_this_is_a_signature", "uuid": '
                    '"0bba929f-8721-460c-dead-a43c20071027", "completed'
                    'datetime": "2012-04-08 10:56:50.902884"}'
                ),
            ],
            any_order=True,
        )

    def test_get_raw_crash(self):
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            boto_s3_store.connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [
            a_raw_crash_as_string
        ]

        # the tested call
        result = boto_s3_store.get_raw_crash(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        self.assertTrue(isinstance(result, DotDict))

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        self.assertEqual(mocked_get_contents_as_string.call_count, 1)
        mocked_get_contents_as_string.assert_has_calls(
            [
                mock.call(),
            ],
        )

        self.assertEqual(result, a_raw_crash)

    def test_get_unredacted_processed_crash_with_consistency_trouble(self):
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage(
            executor_for_gets=TransactionExecutorWithLimitedBackoff
        )

        actions = [
            self._fake_unredacted_processed_crash_as_string(),
            ConditionallyABadDeal('second-hit: not found, no value returned'),
            ConditionallyABadDeal('first hit: not found, no value returned'),
        ]

        def temp_failure_fn(*args):
            action = actions.pop()
            if isinstance(action, Exception):
                raise action
            return action

        boto_s3_store.connection_source.fetch_from_boto_s3 = mock.Mock()
        boto_s3_store.connection_source.fetch_from_boto_s3 \
            .side_effect = temp_failure_fn

        # the tested call
        result = boto_s3_store.get_raw_crash(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source.fetch_from_boto_s3.call_count, 3)
        boto_s3_store.connection_source.fetch_from_boto_s3.has_calls([
            mock.call("936ce666-ff3b-4c7a-9674-367fe2120408", "raw_crash"),
            mock.call("936ce666-ff3b-4c7a-9674-367fe2120408", "raw_crash"),
            mock.call("936ce666-ff3b-4c7a-9674-367fe2120408", "raw_crash"),
        ])

        self.assertEqual(result, self._fake_unredacted_processed_crash())

    def test_get_unredacted_processed_crash_with_consistency_trouble_no_recover(self):
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage(
            executor_for_gets=TransactionExecutorWithLimitedBackoff
        )

        actions = [
            ConditionallyABadDeal('third-hit: not found, no value returned'),
            ConditionallyABadDeal('second-hit: not found, no value returned'),
            ConditionallyABadDeal('first hit: not found, no value returned'),
        ]

        def temp_failure_fn(*args):
            action = actions.pop()
            if isinstance(action, Exception):
                raise action
            return action

        boto_s3_store.connection_source.fetch_from_boto_s3 = mock.Mock()
        boto_s3_store.connection_source.fetch_from_boto_s3 \
            .side_effect = temp_failure_fn

        # the tested call
        self.assertRaises(
            ConditionallyABadDeal,
            boto_s3_store.get_raw_crash,
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source.fetch_from_boto_s3.call_count, 3)
        boto_s3_store.connection_source.fetch_from_boto_s3.has_calls([
            mock.call("936ce666-ff3b-4c7a-9674-367fe2120408", "raw_crash"),
            mock.call("936ce666-ff3b-4c7a-9674-367fe2120408", "raw_crash"),
            mock.call("936ce666-ff3b-4c7a-9674-367fe2120408", "raw_crash"),
        ])

    def test_get_raw_dump(self):
        """test fetching the raw dump without naming it"""
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            boto_s3_store.connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [
            'this is a raw dump'
        ]

        # the tested call
        result = boto_s3_store.get_raw_dump(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        boto_s3_store.connection_source._mocked_connection.get_bucket.return_value.get_key \
            .assert_called_with(
                'dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408'
            )
        key_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value.get_key.return_value
        self.assertEqual(key_mock.get_contents_as_string.call_count, 1)
        key_mock.get_contents_as_string.assert_has_calls(
            [
                mock.call(),
            ],
        )

        self.assertEqual(result, 'this is a raw dump')

    def test_get_raw_dump_upload_file_minidump(self):
        """test fetching the raw dump, naming it 'upload_file_minidump'"""
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            boto_s3_store.connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [
            'this is a raw dump'
        ]

        # the tested call
        result = boto_s3_store.get_raw_dump(
            "936ce666-ff3b-4c7a-9674-367fe2120408",
            name='upload_file_minidump'
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        boto_s3_store.connection_source._mocked_connection.get_bucket.return_value.get_key \
            .assert_called_with(
                'dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408'
            )
        key_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value.get_key.return_value
        self.assertEqual(key_mock.get_contents_as_string.call_count, 1)
        key_mock.get_contents_as_string.assert_has_calls(
            [
                mock.call(),
            ],
        )

        self.assertEqual(result, 'this is a raw dump')

    def test_get_raw_dump_empty_string(self):
        """test fetching the raw dump, naming it with empty string"""
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            boto_s3_store.connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [
            'this is a raw dump'
        ]

        # the tested call
        result = boto_s3_store.get_raw_dump(
            "936ce666-ff3b-4c7a-9674-367fe2120408",
            name=''
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        boto_s3_store.connection_source._mocked_connection.get_bucket.return_value.get_key \
            .assert_called_with(
                'dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408'
            )
        key_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value.get_key.return_value
        self.assertEqual(key_mock.get_contents_as_string.call_count, 1)
        key_mock.get_contents_as_string.assert_has_calls(
            [
                mock.call(),
            ],
        )

        self.assertEqual(result, 'this is a raw dump')

    def test_get_raw_dumps(self):
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            boto_s3_store.connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [
            '["dump", "flash_dump", "city_dump"]',
            'this is "dump", the first one',
            'this is "flash_dump", the second one',
            'this is "city_dump", the last one',
        ]

        # the tested call
        result = boto_s3_store.get_raw_dumps(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        mocked_get_contents_as_string.assert_has_calls(
            [mock.call(), mock.call(), mock.call(), mock.call(), ]
        )

        self.assertEqual(
            result,
            {
                "dump": 'this is "dump", the first one',
                "flash_dump": 'this is "flash_dump", the second one',
                "city_dump": 'this is "city_dump", the last one',
            }
        )

    def test_get_raw_dumps_as_files(self):
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage()
        files = [
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
        ]
        boto_s3_store.connection_source._open.return_value = mock.MagicMock(
            side_effect=files
        )
        mocked_get_contents_as_string = (
            boto_s3_store.connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [
            '["dump", "flash_dump", "city_dump"]',
            'this is "dump", the first one',
            'this is "flash_dump", the second one',
            'this is "city_dump", the last one',
        ]

        # the tested call
        result = boto_s3_store.get_raw_dumps_as_files(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # we don't care much about the mocked internals as the bulk of that
        # function is tested elsewhere.
        # we just need to be concerned about the file writing worked
        self.assertEqual(
            result,
            {
                'flash_dump': join(
                    self.TEMPDIR,
                    '936ce666-ff3b-4c7a-9674-367fe2120408.flash_dump'
                        '.TEMPORARY.dump'
                ),
                'city_dump': join(
                    self.TEMPDIR,
                    '936ce666-ff3b-4c7a-9674-367fe2120408.city_dump'
                        '.TEMPORARY.dump'
                ),
                'upload_file_minidump': join(
                    self.TEMPDIR,
                    '936ce666-ff3b-4c7a-9674-367fe2120408'
                        '.upload_file_minidump.TEMPORARY.dump'
                )
            }
        )

    def test_get_unredacted_processed(self):
    # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            boto_s3_store.connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [
            self._fake_unredacted_processed_crash_as_string()
        ]

        # the tested call
        result = boto_s3_store.get_unredacted_processed(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 1)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket.assert_called_with(
            'crash_storage'
        )

        key_mock = boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value.get_key.return_value
        self.assertEqual(key_mock.get_contents_as_string.call_count, 1)
        key_mock.get_contents_as_string.assert_has_calls([mock.call(), ])

        self.assertEqual(result, self._fake_unredacted_processed_crash())

    def test_get_undredacted_processed_with_trouble(self):
        # setup some internal behaviors and fake outs
        boto_s3_store = self.setup_mocked_s3_storage(
            executor_for_gets=TransactionExecutorWithLimitedBackoff
        )
        mocked_bucket = boto_s3_store.connection_source._connect_to_endpoint.return_value \
            .get_bucket.return_value
        mocked_key = mocked_bucket.get_key.return_value
        mocked_key.get_contents_as_string \
            .side_effect = [
                self._fake_unredacted_processed_crash_as_string()
            ]
        actions = [
            mocked_bucket,
            ABadDeal('second-hit'),
            ABadDeal('first hit'),
        ]

        def temp_failure_fn(key):
            self.assertEqual(key, 'crash_storage')
            action = actions.pop()
            if isinstance(action, Exception):
                raise action
            return action

        boto_s3_store.connection_source._connect_to_endpoint.return_value.get_bucket \
            .side_effect = (
                temp_failure_fn
            )
        # the tested call
        result = boto_s3_store.get_unredacted_processed(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # what should have happened internally
        self.assertEqual(boto_s3_store.connection_source._calling_format.call_count, 3)
        boto_s3_store.connection_source._calling_format.assert_called_with()

        self.assertEqual(boto_s3_store.connection_source._connect_to_endpoint.call_count, 3)
        self.assert_s3_connection_parameters(boto_s3_store)

        self.assertEqual(
            boto_s3_store.connection_source._mocked_connection.get_bucket.call_count,
            3
        )
        boto_s3_store.connection_source._mocked_connection.get_bucket \
            .assert_has_calls(
                [
                    mock.call('crash_storage'),
                    mock.call('crash_storage'),
                    mock.call('crash_storage'),
                ],
            )

        self.assertEqual(mocked_key.get_contents_as_string.call_count, 1)
        mocked_key.get_contents_as_string.assert_has_calls(
            [mock.call(), ],
        )

        self.assertEqual(result, self._fake_unredacted_processed_crash())

    def test_not_found(self):
        boto_s3_store = self.setup_mocked_s3_storage()
        get_contents_as_string_mocked = (
            boto_s3_store.connection_source._mocked_connection.get_bucket
            .return_value.get_key.return_value.get_contents_as_string
        )
        get_contents_as_string_mocked.side_effect = \
            boto.exception.StorageResponseError(
                status="you're in trouble",
                reason="I said so"
            )
        self.assertRaises(
            CrashIDNotFound,
            boto_s3_store.get_raw_crash,
            '0bba929f-dead-dead-dead-a43c20071027'
        )

    def test_not_found_get_key_returns_none(self):
        boto_s3_store = self.setup_mocked_s3_storage()
        boto_s3_store.connection_source._mocked_connection.get_bucket \
            .return_value.get_key.return_value = None
        self.assertRaises(
            CrashIDNotFound,
            boto_s3_store.get_raw_crash,
            '0bba929f-dead-dead-dead-a43c20071027'
        )


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

a_thing = {
    'a': 'some a',
    'b': 'some b',
    'c':  16,
    'd': {
        'da': 'some da',
        'db': 'same db',
    },
}
thing_as_str = json.dumps(a_thing)

class TestCase(socorro.unittest.testbase.TestCase):

    def setup_mocked_s3_storage(
        self,
        executor=TransactionExecutor,
        executor_for_gets=TransactionExecutor,
        storage_class='BotoS3CrashStorage',
        host='',
        port=0
    ):
        config = DotDict({
            'resource_class': ConnectionContext,
            'logger': mock.Mock(),
            'host': host,
            'port': port,
            'access_key': 'this is the access key',
            'secret_access_key': 'secrets',
            'bucket_name': 'silliness',
            'prefix': 'dev',
            'calling_format': mock.Mock()
        })
        s3_conn = ConnectionContext(config)
        s3_conn._connect_to_endpoint = mock.Mock()
        s3_conn._mocked_connection = s3_conn._connect_to_endpoint.return_value
        s3_conn._calling_format.return_value = mock.Mock()
        s3_conn._CreateError = mock.Mock()
        s3_conn._S3ResponseError = mock.Mock()
        s3_conn._open = mock.MagicMock()

        return s3_conn

    def assert_s3_connection_parameters(self, connection_source, host='', port=0):
        kwargs = {
            "aws_access_key_id": connection_source.config.access_key,
            "aws_secret_access_key": connection_source.config.secret_access_key,
            "is_secure": True,
            "calling_format": connection_source._calling_format.return_value
        }
        if host:
            kwargs['host'] = host
        if port:
            kwargs['port'] = port
        connection_source._connect_to_endpoint.assert_called_with(**kwargs)

    def test_connect_with_host_port(self):
        connection = self.setup_mocked_s3_storage(
            host='somewhere.sometime.someone',
            port=666,
        )
        c =  connection._connect()
        self.assert_s3_connection_parameters(
            connection,
            host='somewhere.sometime.someone',
            port=666,
        )

    def test_s3_dir_builder(self):
        connection_source = self.setup_mocked_s3_storage()
        prefix = 'dev'
        name_of_thing = 'dump'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        good = connection_source.build_s3_dirs(prefix, name_of_thing, crash_id)
        self.assertEqual("dev/v1/dump/fff13cf0-5671-4496-ab89-47a922141114", good)

    def test_submit_to_boto_s3(self):
        connection_source = self.setup_mocked_s3_storage()

        # the call to be tested
        connection_source.submit_to_boto_s3(
            'this_is_an_id',
            'name_of_thing',
            thing_as_str
        )

        # this should have happened
        self.assert_s3_connection_parameters(connection_source)
        self.assertEqual(connection_source._calling_format.call_count, 1)
        connection_source._calling_format.assert_called_with()

        self.assertEqual(connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(connection_source)

        self.assertEqual(
            connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        connection_source._mocked_connection.get_bucket.assert_called_with(
            'silliness'
        )

        bucket_mock = connection_source._mocked_connection.get_bucket \
            .return_value
        self.assertEqual(bucket_mock.new_key.call_count, 1)
        bucket_mock.new_key.called_once_with(
            'dev/v1/name_of_thing/this_is_an_id'
        )

        storage_key_mock = bucket_mock.new_key.return_value
        self.assertEqual(
            storage_key_mock.set_contents_from_string.call_count,
            1
        )
        storage_key_mock.set_contents_from_string.called_once_with(
            '{"a": "some a", "c": 16, "b": "some b", "d": '
            '{"db": "same db", "da": "some da"}}'
        )

    def test_get_fetch_from_boto(self):
        # setup some internal behaviors and fake outs
        connection_source = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [ thing_as_str ]

        # the tested call
        result = connection_source.fetch_from_boto_s3(
            'name_of_thing',
            'this_is_an_id'
        )

        # what should have happened internally
        self.assertEqual(connection_source._calling_format.call_count, 1)
        connection_source._calling_format.assert_called_with()

        self.assertEqual(connection_source._connect_to_endpoint.call_count, 1)
        self.assert_s3_connection_parameters(connection_source)

        self.assertEqual(
            connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        connection_source._mocked_connection.get_bucket.assert_called_with(
            'silliness'
        )

        self.assertEqual(mocked_get_contents_as_string.call_count, 1)
        mocked_get_contents_as_string.assert_has_calls(
            [
                mock.call(),
            ],
        )

        self.assertEqual(result, thing_as_str)

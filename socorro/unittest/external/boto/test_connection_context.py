# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

import mock

from socorrolib.lib.util import DotDict
from socorro.external.boto.connection_context import (
    DatePrefixKeyBuilder,
    KeyBuilderBase,
    KeyNotFound,
    S3ConnectionContext,
    RegionalS3ConnectionContext,
)
from socorro.database.transaction_executor import (
    TransactionExecutor,
)
import socorro.unittest.testbase


a_raw_crash = {
    "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
}
a_raw_crash_as_string = json.dumps(a_raw_crash)


class ABadDeal(Exception):
    pass


class ConditionallyABadDeal(Exception):
    pass


S3ConnectionContext.operational_exceptions = (ABadDeal,)
S3ConnectionContext.conditional_exceptions = (ConditionallyABadDeal,)

a_thing = {
    'a': 'some a',
    'b': 'some b',
    'c': 16,
    'd': {
        'da': 'some da',
        'db': 'same db',
    },
}
thing_as_str = json.dumps(a_thing)


class ConnectionContextTestCase(socorro.unittest.testbase.TestCase):
    def setup_mocked_s3_storage(
        self,
        executor=TransactionExecutor,
        executor_for_gets=TransactionExecutor,
        storage_class='BotoS3CrashStorage',
        host='',
        port=0,
        resource_class=S3ConnectionContext,
        **extra
    ):
        config = DotDict({
            'resource_class': resource_class,
            'logger': mock.Mock(),
            'host': host,
            'port': port,
            'access_key': 'this is the access key',
            'secret_access_key': 'secrets',
            'bucket_name': 'silliness',
            'keybuilder_class': KeyBuilderBase,
            'prefix': 'dev',
            'calling_format': mock.Mock()
        })
        config.update(extra)
        s3_conn = resource_class(config)
        s3_conn._connect_to_endpoint = mock.Mock()
        s3_conn._mocked_connection = s3_conn._connect_to_endpoint.return_value
        s3_conn._calling_format.return_value = mock.Mock()
        s3_conn._CreateError = mock.Mock()
        s3_conn.ResponseError = mock.Mock()
        s3_conn._open = mock.MagicMock()

        return s3_conn

    def assert_s3_connection_parameters(self, connection_source):
        kwargs = {
            "aws_access_key_id": connection_source.config.access_key,
            "aws_secret_access_key": (
                connection_source.config.secret_access_key
            ),
            "is_secure": True,
            "calling_format": connection_source._calling_format.return_value
        }
        connection_source._connect_to_endpoint.assert_called_with(**kwargs)

    def test_dir_builder(self):
        connection_source = self.setup_mocked_s3_storage()
        prefix = 'dev'
        name_of_thing = 'dump'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        all_keys = connection_source.build_keys(prefix, name_of_thing, crash_id)

        # This uses the default key builder which should produce a single
        # key--so we verify that there's only one key and that it's the one
        # we're looking for.
        self.assertEqual(len(all_keys), 1)
        self.assertEqual(
            all_keys[0],
            'dev/v1/dump/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_submit(self):
        connection_source = self.setup_mocked_s3_storage()

        # the call to be tested
        connection_source.submit(
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

    def test_fetch(self):
        # setup some internal behaviors and fake outs
        connection_source = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            connection_source._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [thing_as_str]

        # the tested call
        result = connection_source.fetch(
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

    def assert_regional_s3_connection_parameters(
        self,
        region,
        connection_source
    ):
        kwargs = {
            "aws_access_key_id": connection_source.config.access_key,
            "aws_secret_access_key": (
                connection_source.config.secret_access_key
            ),
            "is_secure": True,
            "calling_format": connection_source._calling_format.return_value
        }
        args = (region,)
        connection_source._connect_to_endpoint.assert_called_with(
            *args,
            **kwargs
        )

    def test_fetch_with_regional_s3connection_context(self):
        # setup some internal behaviors and fake outs
        connection_source = self.setup_mocked_s3_storage(
            resource_class=RegionalS3ConnectionContext,
            region='us-south-3'
        )
        connection_source.fetch(
            'name_of_thing',
            'this_is_an_id'
        )
        self.assert_regional_s3_connection_parameters(
            'us-south-3',
            connection_source
        )



class MultiplePathsBase(socorro.unittest.testbase.TestCase):
    """Sets up mocked s3 storage using DatePrefixKeyBuilder"""
    def setup_mocked_s3_storage(
        self,
        executor=TransactionExecutor,
        executor_for_gets=TransactionExecutor,
        storage_class='BotoS3CrashStorage',
        host='',
        port=0,
        resource_class=S3ConnectionContext,
        **extra
    ):
        config = DotDict({
            'resource_class': resource_class,
            'logger': mock.Mock(),
            'host': host,
            'port': port,
            'access_key': 'this is the access key',
            'secret_access_key': 'secrets',
            'bucket_name': 'silliness',
            'keybuilder_class': DatePrefixKeyBuilder,
            'prefix': 'dev',
            'calling_format': mock.Mock()
        })
        config.update(extra)
        s3_conn = resource_class(config)
        s3_conn._connect_to_endpoint = mock.Mock()
        s3_conn._mocked_connection = s3_conn._connect_to_endpoint.return_value
        s3_conn._calling_format.return_value = mock.Mock()
        s3_conn._CreateError = mock.Mock()
        s3_conn.ResponseError = mock.Mock()
        s3_conn._open = mock.MagicMock()

        return s3_conn


class DatePrefixKeyBuilderTestCase(MultiplePathsBase):
    """Tests the DatePrefixKeyBuilder with different crash types"""
    def test_dir_builder_with_dump(self):
        connection_source = self.setup_mocked_s3_storage()
        prefix = 'dev'
        name_of_thing = 'dump'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        all_keys = connection_source.build_keys(prefix, name_of_thing, crash_id)

        # Only the old-style key is returned
        self.assertEqual(len(all_keys), 1)
        self.assertEqual(
            all_keys[0],
            'dev/v1/dump/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_dir_builder_with_raw_crash(self):
        connection_source = self.setup_mocked_s3_storage()
        prefix = 'dev'
        name_of_thing = 'raw_crash'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        all_keys = connection_source.build_keys(prefix, name_of_thing, crash_id)

        # The new- and old-style keys are returned
        self.assertEqual(len(all_keys), 2)
        self.assertEqual(
            all_keys[0],
            'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-ab89-47a922141114'
        )
        self.assertEqual(
            all_keys[1],
            'dev/v1/raw_crash/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_dir_builder_with_raw_crash_no_date(self):
        connection_source = self.setup_mocked_s3_storage()
        prefix = 'dev'
        name_of_thing = 'raw_crash'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922xxxxxx'
        all_keys = connection_source.build_keys(prefix, name_of_thing, crash_id)

        # The suffix is not a date, so only the old-style key is returned
        self.assertEqual(len(all_keys), 1)
        self.assertEqual(
            all_keys[0],
            'dev/v1/raw_crash/fff13cf0-5671-4496-ab89-47a922xxxxxx'
        )


class MultiplePathsTestCase(MultiplePathsBase):
    """Tests crash storage when multiple keys are involved

    ``.submit()`` should always use the first key from a keybuilder.

    ``.fetch()`` should try the keys in order.

    """
    def test_submit_with_dump(self):
        connection_source = self.setup_mocked_s3_storage()

        # the call to be tested
        connection_source.submit(
            'fff13cf0-5671-4496-ab89-47a922141114',
            'dump',
            thing_as_str
        )

        bucket_mock = (
            connection_source
            ._mocked_connection
            .get_bucket
            .return_value
        )
        self.assertEqual(bucket_mock.new_key.call_count, 1)
        bucket_mock.new_key.called_once_with(
            'dev/v1/dump/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_submit_with_raw_crash(self):
        """Verify that .submit() only uses the first key if there are multiple

        """
        connection_source = self.setup_mocked_s3_storage()

        # the call to be tested
        connection_source.submit(
            'fff13cf0-5671-4496-ab89-47a922141114',
            'raw_crash',
            thing_as_str
        )

        bucket_mock = (
            connection_source
            ._mocked_connection
            .get_bucket
            .return_value
        )
        self.assertEqual(bucket_mock.new_key.call_count, 1)
        bucket_mock.new_key.called_once_with(
            'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_fetch_with_raw_crash_at_new_style_path(self):
        """Verifies that .fetch() works correctly if the first key works."""
        connection_source = self.setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            connection_source
            ._connect_to_endpoint
            .return_value
            .get_bucket
            .return_value
            .get_key
            .return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [thing_as_str]

        result = connection_source.fetch(
            'fff13cf0-5671-4496-ab89-47a922141114',
            'raw_crash'
        )

        self.assertEqual(
            connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        self.assertEqual(
            (
                connection_source
                ._mocked_connection
                .get_bucket
                .return_value
                .get_key
                .call_count
            ),
            1
        )
        (
            connection_source
            ._mocked_connection
            .get_bucket
            .return_value
            .get_key
            .assert_called_with(
                'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-ab89-47a922141114'
            )
        )

    def test_fetch_with_raw_crash_at_old_style_path(self):
        """Verifies that .fetch() will try to retrieve the object with the
        new-style key, fail, then try to retrieve the object with the old-style
        key.

        """
        connection_source = self.setup_mocked_s3_storage()
        mocked_get_key = (
            connection_source
            ._connect_to_endpoint
            .return_value
            .get_bucket
            .return_value
            .get_key
        )
        # First time get_key() is called, it returns None which causes fetch to
        # call it again with the next key. We have to swap side-effect handling
        # functions so that the second time get_key() is called, it returns an
        # object which simulates the situation we're looking for.
        capture_args = []
        def get_key_first_call(*args, **kwargs):
            capture_args.append((args, kwargs))
            # First time
            def get_key_second_call(*args, **kwargs):
                capture_args.append((args, kwargs))
                # Second time
                get_key_return = mock.Mock()
                get_key_return.return_value.get_contents_as_string = [thing_as_str]
                return get_key_return

            mocked_get_key.side_effect = get_key_second_call
            return None

        mocked_get_key.side_effect = get_key_first_call

        connection_source.fetch(
            'fff13cf0-5671-4496-ab89-47a922141114',
            'raw_crash'
        )

        self.assertEqual(
            connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        self.assertEqual(
            (
                connection_source
                ._mocked_connection
                .get_bucket
                .return_value
                .get_key
                .call_count
            ),
            2
        )

        # The first time, it's called with a new-style path
        self.assertEqual(
            capture_args[0][0][0],
            'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-ab89-47a922141114'
        )
        # The second time, it's called with the old-style path
        self.assertEqual(
            capture_args[1][0][0],
            'dev/v1/raw_crash/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_fetch_with_raw_crash_not_there(self):
        """Verifies that .fetch() tries to get the object twice--once with each
        key--and then raises a KeyNotFound exception because the object is not
        there.

        """
        connection_source = self.setup_mocked_s3_storage()
        mocked_get_key = (
            connection_source
            ._connect_to_endpoint
            .return_value
            .get_bucket
            .return_value
            .get_key
        )
        mocked_get_key.return_value = None

        with self.assertRaises(KeyNotFound):
            connection_source.fetch(
                'fff13cf0-5671-4496-ab89-47a922141114',
                'raw_crash'
            )
        self.assertEqual(
            connection_source._mocked_connection.get_bucket.call_count,
            1
        )
        self.assertEqual(
            (
                connection_source
                ._mocked_connection
                .get_bucket
                .return_value
                .get_key
                .call_count
            ),
            2
        )

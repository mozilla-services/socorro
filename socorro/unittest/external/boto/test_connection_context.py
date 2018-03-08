# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json

import mock
import pytest

from socorro.external.boto.connection_context import (
    DatePrefixKeyBuilder,
    SimpleDatePrefixKeyBuilder,
    KeyNotFound,
    S3ConnectionContext,
    RegionalS3ConnectionContext,
    HostPortS3ConnectionContext,
)
from socorro.unittest.external.boto import get_config


a_raw_crash = {
    'submitted_timestamp': '2013-01-09T22:21:18.646733+00:00'
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


def setup_mocked_s3_storage(cls=S3ConnectionContext, **extra):
    values_source = {
        'bucket_name': 'silliness',
        'prefix': 'dev',
        'calling_format': mock.Mock()
    }
    values_source.update(extra)

    config = get_config(
        cls=cls,
        values_source=values_source
    )

    s3_conn = cls(config)
    s3_conn._connect_to_endpoint = mock.Mock()
    s3_conn._mocked_connection = s3_conn._connect_to_endpoint.return_value
    s3_conn._calling_format.return_value = mock.Mock()
    s3_conn._CreateError = mock.Mock()
    s3_conn.ResponseError = mock.Mock()
    s3_conn._open = mock.MagicMock()

    return s3_conn


class TestConnectionContext:
    def assert_s3_connection_parameters(self, connection_source):
        kwargs = {
            'aws_access_key_id': connection_source.config.access_key,
            'aws_secret_access_key': (
                connection_source.config.secret_access_key
            ),
            'is_secure': True,
            'calling_format': connection_source._calling_format.return_value
        }
        connection_source._connect_to_endpoint.assert_called_with(**kwargs)

    def test_dir_builder(self):
        conn = setup_mocked_s3_storage()
        prefix = 'dev'
        name_of_thing = 'dump'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        all_keys = conn.build_keys(prefix, name_of_thing, crash_id)

        # This uses the default key builder which should produce a single
        # key--so we verify that there's only one key and that it's the one
        # we're looking for.
        assert len(all_keys) == 1
        assert all_keys[0] == 'dev/v1/dump/fff13cf0-5671-4496-ab89-47a922141114'

    def test_submit(self):
        conn = setup_mocked_s3_storage()

        # the call to be tested
        conn.submit(
            'this_is_an_id',
            'name_of_thing',
            thing_as_str
        )

        # this should have happened
        self.assert_s3_connection_parameters(conn)
        assert conn._calling_format.call_count == 1
        conn._calling_format.assert_called_with()

        assert conn._connect_to_endpoint.call_count == 1
        self.assert_s3_connection_parameters(conn)

        assert conn._mocked_connection.get_bucket.call_count == 1
        conn._mocked_connection.get_bucket.assert_called_with('silliness')

        bucket_mock = conn._mocked_connection.get_bucket.return_value
        assert bucket_mock.new_key.call_count == 1
        bucket_mock.new_key.called_once_with(
            'dev/v1/name_of_thing/this_is_an_id'
        )

        storage_key_mock = bucket_mock.new_key.return_value
        assert storage_key_mock.set_contents_from_string.call_count == 1
        storage_key_mock.set_contents_from_string.called_once_with(
            '{"a": "some a", "c": 16, "b": "some b", "d": '
            '{"db": "same db", "da": "some da"}}'
        )

    def test_fetch(self):
        # setup some internal behaviors and fake outs
        conn = setup_mocked_s3_storage()
        mocked_get_contents_as_string = (
            conn._connect_to_endpoint.return_value
            .get_bucket.return_value.get_key.return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [thing_as_str]

        # the tested call
        result = conn.fetch(
            'name_of_thing',
            'this_is_an_id'
        )

        # what should have happened internally
        assert conn._calling_format.call_count == 1
        conn._calling_format.assert_called_with()

        assert conn._connect_to_endpoint.call_count == 1
        self.assert_s3_connection_parameters(conn)

        assert conn._mocked_connection.get_bucket.call_count == 1
        conn._mocked_connection.get_bucket.assert_called_with('silliness')

        assert mocked_get_contents_as_string.call_count == 1
        mocked_get_contents_as_string.assert_has_calls(
            [
                mock.call(),
            ],
        )

        assert result == thing_as_str

    def assert_regional_s3_connection_parameters(
        self,
        region,
        conn
    ):
        kwargs = {
            'aws_access_key_id': conn.config.access_key,
            'aws_secret_access_key': (
                conn.config.secret_access_key
            ),
            'is_secure': True,
            'calling_format': conn._calling_format.return_value
        }
        args = (region,)
        conn._connect_to_endpoint.assert_called_with(
            *args,
            **kwargs
        )

    def test_fetch_with_regional_s3connection_context(self):
        # setup some internal behaviors and fake outs
        conn = setup_mocked_s3_storage(
            cls=RegionalS3ConnectionContext,
            region='us-south-3'
        )
        conn.fetch(
            'name_of_thing',
            'this_is_an_id'
        )
        self.assert_regional_s3_connection_parameters(
            'us-south-3',
            conn
        )

    def test_create_bucket_with_regional_s3connection_context(self):
        conn = setup_mocked_s3_storage(
            cls=RegionalS3ConnectionContext,
            region='us-south-3'
        )

        # by overriding, we can set any type of exception here
        conn.ResponseError = (NameError,)

        def mocked_get_bucket(bucket_name):
            assert bucket_name == 'name-of-bucket'
            raise NameError('nope!')

        conn._mocked_connection.get_bucket.side_effect = mocked_get_bucket

        conn._get_or_create_bucket(
            conn._mocked_connection,
            'name-of-bucket'
        )
        conn._mocked_connection.create_bucket.assert_called_with(
            'name-of-bucket',
            location='us-south-3'
        )

    def test_HostPortS3ConnectionContext_host_port_secure(self):
        # Test with secure=True
        conn = setup_mocked_s3_storage(
            cls=HostPortS3ConnectionContext,
            host='localhost',
            port=4569,
            secure=True,
        )
        conn.fetch(
            'name_of_thing',
            'this_is_an_id'
        )
        kwargs = {
            'aws_access_key_id': conn.config.access_key,
            'aws_secret_access_key': conn.config.secret_access_key,
            'calling_format': conn._calling_format.return_value,
            'host': 'localhost',
            'port': 4569,
            'is_secure': True,
        }
        conn._connect_to_endpoint.assert_called_with(**kwargs)

        # Test with secure=False
        conn = setup_mocked_s3_storage(
            cls=HostPortS3ConnectionContext,
            host='localhost',
            port=4569,
            secure=False,
        )
        conn.fetch(
            'name_of_thing',
            'this_is_an_id'
        )
        kwargs = {
            'aws_access_key_id': conn.config.access_key,
            'aws_secret_access_key': conn.config.secret_access_key,
            'calling_format': conn._calling_format.return_value,
            'host': 'localhost',
            'port': 4569,
            'is_secure': False,
        }
        conn._connect_to_endpoint.assert_called_with(**kwargs)


class TestDatePrefixKeyBuilder:
    """Tests the DatePrefixKeyBuilder with different crash types"""
    def test_dir_builder_with_dump(self):
        conn = setup_mocked_s3_storage(
            keybuilder_class=DatePrefixKeyBuilder,
        )
        prefix = 'dev'
        name_of_thing = 'dump'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        all_keys = conn.build_keys(prefix, name_of_thing, crash_id)

        # Only the old-style key is returned
        assert len(all_keys) == 1
        assert all_keys[0] == 'dev/v1/dump/fff13cf0-5671-4496-ab89-47a922141114'

    def test_dir_builder_with_raw_crash(self):
        conn = setup_mocked_s3_storage(
            keybuilder_class=DatePrefixKeyBuilder,
        )
        prefix = 'dev'
        name_of_thing = 'raw_crash'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        all_keys = conn.build_keys(prefix, name_of_thing, crash_id)

        # The new- and old-style keys are returned
        assert len(all_keys) == 2
        assert all_keys[0] == 'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-ab89-47a922141114'
        assert all_keys[1] == 'dev/v1/raw_crash/fff13cf0-5671-4496-ab89-47a922141114'

    def test_dir_builder_with_raw_crash_no_date(self):
        conn = setup_mocked_s3_storage(
            keybuilder_class=DatePrefixKeyBuilder,
        )
        prefix = 'dev'
        name_of_thing = 'raw_crash'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922xxxxxx'
        all_keys = conn.build_keys(prefix, name_of_thing, crash_id)

        # The suffix is not a date, so only the old-style key is returned
        assert len(all_keys) == 1
        assert all_keys[0] == 'dev/v1/raw_crash/fff13cf0-5671-4496-ab89-47a922xxxxxx'


class TestSimpleDatePrefixKeyBuilder:
    """Tests the SimpleDatePrefixKeyBuilder with different crash types"""

    def test_dir_builder(self):
        connection_source = setup_mocked_s3_storage(
            keybuilder_class=SimpleDatePrefixKeyBuilder
        )
        prefix = 'dev'
        name_of_thing = 'crash'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922141114'
        all_keys = connection_source.build_keys(
            prefix, name_of_thing, crash_id
        )

        # The new- and old-style keys are returned
        assert len(all_keys) == 1
        assert all_keys[0] == 'dev/v1/crash/20141114/fff13cf0-5671-4496-ab89-47a922141114'

    def test_dir_builder_with_no_date(self):
        connection_source = setup_mocked_s3_storage(
            keybuilder_class=SimpleDatePrefixKeyBuilder
        )
        prefix = 'dev'
        name_of_thing = 'crash'
        crash_id = 'fff13cf0-5671-4496-ab89-47a922xxxxxx'
        all_keys = connection_source.build_keys(
            prefix, name_of_thing, crash_id
        )

        # The suffix is not a date, so only the old-style key is returned
        assert len(all_keys) == 1
        now = datetime.datetime.utcnow()
        expected = 'dev/v1/crash/{}/fff13cf0-5671-4496-ab89-47a922xxxxxx'.format(
            now.strftime('%Y%m%d')
        )
        assert all_keys[0] == expected


class TestMultiplePaths:
    """Tests crash storage when multiple keys are involved

    ``.submit()`` should always use the first key from a keybuilder.

    ``.fetch()`` should try the keys in order.

    """
    def test_submit_with_dump(self):
        conn = setup_mocked_s3_storage(
            keybuilder_class=DatePrefixKeyBuilder
        )

        # the call to be tested
        conn.submit(
            'fff13cf0-5671-4496-ab89-47a922141114',
            'dump',
            thing_as_str
        )

        bucket_mock = (
            conn
            ._mocked_connection
            .get_bucket
            .return_value
        )
        assert bucket_mock.new_key.call_count == 1
        bucket_mock.new_key.called_once_with(
            'dev/v1/dump/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_submit_with_raw_crash(self):
        """Verify that .submit() only uses the first key if there are multiple

        """
        conn = setup_mocked_s3_storage()

        # the call to be tested
        conn.submit(
            'fff13cf0-5671-4496-ab89-47a922141114',
            'raw_crash',
            thing_as_str
        )

        bucket_mock = (
            conn
            ._mocked_connection
            .get_bucket
            .return_value
        )
        assert bucket_mock.new_key.call_count == 1
        bucket_mock.new_key.called_once_with(
            'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-'
            'ab89-47a922141114'
        )

    def test_fetch_with_raw_crash_at_new_style_path(self):
        """Verifies that .fetch() works correctly if the first key works."""
        conn = setup_mocked_s3_storage(
            keybuilder_class=DatePrefixKeyBuilder
        )
        mocked_get_contents_as_string = (
            conn
            ._connect_to_endpoint
            .return_value
            .get_bucket
            .return_value
            .get_key
            .return_value
            .get_contents_as_string
        )
        mocked_get_contents_as_string.side_effect = [thing_as_str]

        conn.fetch('fff13cf0-5671-4496-ab89-47a922141114', 'raw_crash')

        assert conn._mocked_connection.get_bucket.call_count == 1
        assert conn._mocked_connection.get_bucket.return_value.get_key.call_count == 1
        conn._mocked_connection.get_bucket.return_value.get_key.assert_called_with(
            'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-ab89-47a922141114'
        )

    def test_fetch_with_raw_crash_at_old_style_path(self):
        """Verifies that .fetch() will try to retrieve the object with the
        new-style key, fail, then try to retrieve the object with the old-style
        key.

        """
        conn = setup_mocked_s3_storage(
            keybuilder_class=DatePrefixKeyBuilder
        )
        mocked_get_key = (
            conn
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
                get_key_return.return_value.get_contents_as_string = [
                    thing_as_str
                ]
                return get_key_return

            mocked_get_key.side_effect = get_key_second_call
            return None

        mocked_get_key.side_effect = get_key_first_call

        conn.fetch('fff13cf0-5671-4496-ab89-47a922141114', 'raw_crash')

        assert conn._mocked_connection.get_bucket.call_count == 1
        assert conn._mocked_connection.get_bucket.return_value.get_key.call_count == 2

        # The first time, it's called with a new-style path
        expected = 'dev/v2/raw_crash/fff/20141114/fff13cf0-5671-4496-ab89-47a922141114'
        assert capture_args[0][0][0] == expected

        # The second time, it's called with the old-style path
        expected = 'dev/v1/raw_crash/fff13cf0-5671-4496-ab89-47a922141114'
        assert capture_args[1][0][0] == expected

    def test_fetch_with_raw_crash_not_there(self):
        """Verifies that .fetch() tries to get the object twice--once with each
        key--and then raises a KeyNotFound exception because the object is not
        there.

        """
        conn = setup_mocked_s3_storage(
            keybuilder_class=DatePrefixKeyBuilder
        )
        mocked_get_key = (
            conn
            ._connect_to_endpoint
            .return_value
            .get_bucket
            .return_value
            .get_key
        )
        mocked_get_key.return_value = None

        with pytest.raises(KeyNotFound):
            conn.fetch('fff13cf0-5671-4496-ab89-47a922141114', 'raw_crash')
        assert conn._mocked_connection.get_bucket.call_count == 1
        assert conn._mocked_connection.get_bucket.return_value.get_key.call_count == 2

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

import mock
import pytest

from markus.testing import MetricsMock

from socorro.external.boto.connection_context import (
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

    s3_conn = cls(config, namespace='processor.s3')
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
            'fff13cf0-5671-4496-ab89-47a922141114',
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
            'dev/v1/name_of_thing/fff13cf0-5671-4496-ab89-47a922141114'
        )

        storage_key_mock = bucket_mock.new_key.return_value
        assert storage_key_mock.set_contents_from_string.call_count == 1
        storage_key_mock.set_contents_from_string.called_once_with(
            '{"a": "some a", "c": 16, "b": "some b", "d": '
            '{"db": "same db", "da": "some da"}}'
        )

    def test_submit_data_capture(self):
        with MetricsMock() as mm:
            conn = setup_mocked_s3_storage()

            # Do a successful submit
            conn.submit(
                'fff13cf0-5671-4496-ab89-47a922141114',
                'name_of_thing',
                thing_as_str
            )
            # Do a failed submit
            conn._connect = mock.Mock()
            conn._connect.side_effect = Exception
            with pytest.raises(Exception):
                conn.submit(
                    'fff13cf0-5671-4496-ab89-47a922141114',
                    'name_of_thing',
                    thing_as_str
                )

            assert len(mm.filter_records(stat='processor.s3.submit',
                                         tags=['kind:name_of_thing', 'outcome:successful'])) == 1
            assert len(mm.filter_records(stat='processor.s3.submit',
                                         tags=['kind:name_of_thing', 'outcome:failed'])) == 1

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
            'fff13cf0-5671-4496-ab89-47a922141114',
            'name_of_thing'
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
            'fff13cf0-5671-4496-ab89-47a922141114',
            'name_of_thing'
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
            'fff13cf0-5671-4496-ab89-47a922141114',
            'name_of_thing'
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
            'fff13cf0-5671-4496-ab89-47a922141114',
            'name_of_thing'
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

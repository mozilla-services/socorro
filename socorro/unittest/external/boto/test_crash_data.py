import json

import mock
from nose.tools import eq_, assert_raises
from boto.exception import StorageResponseError

from configman import ConfigurationManager

from socorrolib.lib import MissingArgumentError
from socorro.external.boto.crash_data import SimplifiedCrashData
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.unittest.testbase import TestCase


class TestSimplifiedCrashData(TestCase):

    def _get_config(self, sources, extra_values=None):
        self.mock_logging = mock.Mock()

        config_definitions = []
        for source in sources:
            conf = source.get_required_config()
            conf.add_option('logger', default=self.mock_logging)
            config_definitions.append(conf)

        values_source = {'logger': self.mock_logging}

        config_manager = ConfigurationManager(
            config_definitions,
            app_name='testapp',
            app_version='1.0',
            app_description='',
            values_source_list=[values_source],
            argv_source=[],
        )

        return config_manager.get_config()

    def get_s3_store(self):
        s3 = SimplifiedCrashData(
            config=self._get_config([SimplifiedCrashData])
        )
        s3_conn = s3.connection_source
        s3_conn._connect_to_endpoint = mock.Mock()
        return s3

    def test_get_basic_processed(self):
        boto_s3_store = self.get_s3_store()
        mocked_connection = (
            boto_s3_store.connection_source._connect_to_endpoint()
        )

        def mocked_get_contents_as_string():
            return json.dumps({'foo': 'bar'})

        mocked_connection.get_bucket().get_key().get_contents_as_string = (
            mocked_get_contents_as_string
        )
        result = boto_s3_store.get(
            uuid='0bba929f-8721-460c-dead-a43c20071027',
            datatype='processed'
        )
        eq_(result, {'foo': 'bar'})

    def test_get_not_found_processed(self):
        boto_s3_store = self.get_s3_store()
        mocked_connection = (
            boto_s3_store.connection_source._connect_to_endpoint()
        )

        def mocked_get_key(key):
            assert '/processed_crash/' in key
            assert '0bba929f-8721-460c-dead-a43c20071027' in key
            raise StorageResponseError(404, 'not found')

        mocked_connection.get_bucket().get_key = (
            mocked_get_key
        )
        assert_raises(
            CrashIDNotFound,
            boto_s3_store.get,
            uuid='0bba929f-8721-460c-dead-a43c20071027',
            datatype='processed'
        )

    def test_get_basic_raw_dump(self):
        boto_s3_store = self.get_s3_store()
        mocked_connection = (
            boto_s3_store.connection_source._connect_to_endpoint()
        )

        def mocked_get_contents_as_string():
            return '\xa0'

        mocked_connection.get_bucket().get_key().get_contents_as_string = (
            mocked_get_contents_as_string
        )
        result = boto_s3_store.get(
            uuid='0bba929f-8721-460c-dead-a43c20071027',
            datatype='raw',
        )
        eq_(result, '\xa0')

    def test_get_not_found_raw_dump(self):
        boto_s3_store = self.get_s3_store()
        mocked_connection = (
            boto_s3_store.connection_source._connect_to_endpoint()
        )

        def mocked_get_key(key):
            assert '/dump/' in key
            assert '0bba929f-8721-460c-dead-a43c20071027' in key
            raise StorageResponseError(404, 'not found')

        mocked_connection.get_bucket().get_key = (
            mocked_get_key
        )
        assert_raises(
            CrashIDNotFound,
            boto_s3_store.get,
            uuid='0bba929f-8721-460c-dead-a43c20071027',
            datatype='raw'
        )

    def test_get_not_found_raw_crash(self):
        boto_s3_store = self.get_s3_store()
        mocked_connection = (
            boto_s3_store.connection_source._connect_to_endpoint()
        )

        def mocked_get_key(key):
            assert '/raw_crash/' in key
            assert '0bba929f-8721-460c-dead-a43c20071027' in key
            raise StorageResponseError(404, 'not found')

        mocked_connection.get_bucket().get_key = (
            mocked_get_key
        )
        assert_raises(
            CrashIDNotFound,
            boto_s3_store.get,
            uuid='0bba929f-8721-460c-dead-a43c20071027',
            datatype='meta'
        )

    def test_bad_arguments(self):
        boto_s3_store = self.get_s3_store()
        assert_raises(
            MissingArgumentError,
            boto_s3_store.get
        )
        assert_raises(
            MissingArgumentError,
            boto_s3_store.get,
            uuid='0bba929f-8721-460c-dead-a43c20071027',
        )

import boto
from boto.exception import StorageResponseError
import pytest


class BotoHelper(object):
    def get_or_create_bucket(self, bucket):
        """Gets or creates the crashstats bucket"""
        conn = boto.connect_s3()
        try:
            bucket = conn.get_bucket('crashstats')
        except StorageResponseError:
            conn.create_bucket('crashstats')
            bucket = conn.get_bucket('crashstats')
        return bucket

    def put_object(self, key, value):
        """Puts an object into the crashstats bucket"""
        bucket = self.get_or_create_bucket('crashstats')
        key_object = bucket.new_key(key)
        key_object.set_contents_from_string(value)


@pytest.fixture
def boto_helper():
    return BotoHelper()

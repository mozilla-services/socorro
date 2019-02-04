# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import boto
from boto.exception import StorageResponseError
import pytest


class BotoHelper(object):
    """Helper class inspired by Boto's S3 API

    The goal here is to automate repetitive things in a convenient way, but
    be inspired by the existing Boto S3 API.

    """
    def get_or_create_bucket(self, bucket_name):
        """Gets or creates the crashstats bucket"""
        conn = boto.connect_s3()
        try:
            bucket = conn.get_bucket(bucket_name)
        except StorageResponseError:
            conn.create_bucket(bucket_name)
            bucket = conn.get_bucket(bucket_name)
        return bucket

    def set_contents_from_string(self, bucket_name, key, value):
        """Puts an object into the specified bucket"""
        bucket = self.get_or_create_bucket(bucket_name)
        key_object = bucket.new_key(key)
        key_object.set_contents_from_string(value)

    def get_contents_as_string(self, bucket_name, key):
        """Fetches an object from the specified bucket"""
        bucket = self.get_or_create_bucket(bucket_name)
        key_object = bucket.get_key(key)
        if key_object is None:
            return None
        return key_object.get_contents_as_string()

    def list(self, bucket_name):
        """Lists contents of bucket and returns keys as strings"""
        bucket = self.get_or_create_bucket(bucket_name)
        return [key.key for key in bucket.list()]


@pytest.fixture
def boto_helper():
    """BotoHelper() for automating repetitive tasks in S3 setup

    Provides:

    * ``get_or_create_bucket(bucket_name)``
    * ``set_contents_from_string(bucket_name, key, value)``
    * ``get_contents_as_string(bucket_name, key)``
    * ``list(bucket_name)``

    """
    return BotoHelper()

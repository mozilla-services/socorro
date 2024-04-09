# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os

import pytest

from socorro.external.boto.connection_context import KeyNotFound
from socorro.libclass import build_instance_from_settings


S3_SETTINGS = {
    "class": "socorro.external.boto.connection_context.S3Connection",
    "options": {
        "region": os.environ["CRASHSTORAGE_S3_REGION"],
        "access_key": os.environ["CRASHSTORAGE_S3_ACCESS_KEY"],
        "secret_access_key": os.environ["CRASHSTORAGE_S3_SECRET_ACCESS_KEY"],
        "endpoint_url": os.environ["LOCAL_DEV_AWS_ENDPOINT_URL"],
    },
}


class TestS3ConnectionContext:
    def test_save_file(self, s3_helper):
        """Test saving a file and make sure it's there."""
        conn = build_instance_from_settings(S3_SETTINGS)

        bucket = s3_helper.get_crashstorage_bucket()
        path = "/test/testfile.txt"
        file_data = b"test file contents"

        s3_helper.create_bucket(bucket)
        conn.save_file(bucket=bucket, path=path, data=file_data)

        objects = s3_helper.list(bucket)
        assert objects == ["/test/testfile.txt"]
        assert s3_helper.download(bucket, path) == file_data

        # Stomp on that file with a new one
        file_data2 = b"test file contents 2"
        conn.save_file(bucket=bucket, path=path, data=file_data2)
        assert s3_helper.download(bucket, path) == file_data2

    def test_load_file_doesnt_exist(self, s3_helper):
        """Test loading a file that isn't there."""
        conn = build_instance_from_settings(S3_SETTINGS)

        bucket = s3_helper.get_crashstorage_bucket()
        path = "/test/testfile.txt"

        s3_helper.create_bucket(bucket)
        with pytest.raises(KeyNotFound):
            conn.load_file(bucket=bucket, path=path)

    def test_load_file(self, s3_helper):
        """Test loading a file that isn't there."""
        conn = build_instance_from_settings(S3_SETTINGS)

        bucket = s3_helper.get_crashstorage_bucket()
        path = "/test/testfile.txt"
        file_data = b"test file contents"

        s3_helper.create_bucket(bucket)
        s3_helper.upload(bucket, path, file_data)
        data = conn.load_file(bucket=bucket, path=path)
        assert data == file_data

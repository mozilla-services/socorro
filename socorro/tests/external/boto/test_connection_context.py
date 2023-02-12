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
        "endpoint_url": os.environ["AWS_ENDPOINT_URL"],
    },
}


class TestS3ConnectionContext:
    def test_save_file(self, boto_helper):
        """Test saving a file and make sure it's there."""
        conn = build_instance_from_settings(S3_SETTINGS)

        bucket = os.environ["CRASHSTORAGE_S3_BUCKET"]
        path = "/test/testfile.txt"
        file_data = b"test file contents"

        boto_helper.create_bucket(bucket)
        conn.save_file(bucket=bucket, path=path, data=file_data)

        objects = boto_helper.list(bucket)
        assert objects == ["/test/testfile.txt"]
        assert boto_helper.download_fileobj(bucket, path) == file_data

        # Stomp on that file with a new one
        file_data2 = b"test file contents 2"
        conn.save_file(bucket=bucket, path=path, data=file_data2)
        assert boto_helper.download_fileobj(bucket, path) == file_data2

    def test_load_file_doesnt_exist(self, boto_helper):
        """Test loading a file that isn't there."""
        conn = build_instance_from_settings(S3_SETTINGS)

        bucket = os.environ["CRASHSTORAGE_S3_BUCKET"]
        path = "/test/testfile.txt"

        boto_helper.create_bucket(bucket)
        with pytest.raises(KeyNotFound):
            conn.load_file(bucket=bucket, path=path)

    def test_load_file(self, boto_helper):
        """Test loading a file that isn't there."""
        conn = build_instance_from_settings(S3_SETTINGS)

        bucket = os.environ["CRASHSTORAGE_S3_BUCKET"]
        path = "/test/testfile.txt"
        file_data = b"test file contents"

        boto_helper.create_bucket(bucket)
        boto_helper.upload_fileobj(bucket, path, file_data)
        data = conn.load_file(bucket=bucket, path=path)
        assert data == file_data

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.external.boto.connection_context import S3Connection, KeyNotFound
from socorro.tests.external.boto import get_config


class TestS3ConnectionContext:
    def test_save_file(self, boto_helper):
        """Test saving a file and make sure it's there."""
        config = get_config(cls=S3Connection)
        conn = S3Connection(config)

        bucket = conn.config.bucket_name
        path = "/test/testfile.txt"
        file_data = b"test file contents"

        boto_helper.create_bucket(bucket)
        conn.save_file(path, file_data)

        objects = boto_helper.list(bucket)
        assert objects == ["/test/testfile.txt"]
        assert boto_helper.download_fileobj(bucket, path) == file_data

        # Stomp on that file with a new one
        file_data2 = b"test file contents 2"
        conn.save_file(path, file_data2)
        assert boto_helper.download_fileobj(bucket, path) == file_data2

    def test_load_file_doesnt_exist(self, boto_helper):
        """Test loading a file that isn't there."""
        config = get_config(cls=S3Connection)
        conn = S3Connection(config)

        bucket = conn.config.bucket_name
        path = "/test/testfile.txt"

        boto_helper.create_bucket(bucket)
        with pytest.raises(KeyNotFound):
            conn.load_file(path)

    def test_load_file(self, boto_helper):
        """Test loading a file that isn't there."""
        config = get_config(cls=S3Connection)
        conn = S3Connection(config)

        bucket = conn.config.bucket_name
        path = "/test/testfile.txt"
        file_data = b"test file contents"

        boto_helper.create_bucket(bucket)
        boto_helper.upload_fileobj(bucket, path, file_data)
        data = conn.load_file(path)
        assert data == file_data

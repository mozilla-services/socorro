# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

import pytest

from socorro.external.boto.crash_data import SimplifiedCrashData, TelemetryCrashData
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import MissingArgumentError, BadArgumentError
from socorro.unittest.external.boto import get_config


class TestSimplifiedCrashData:
    def get_s3_store(self):
        return SimplifiedCrashData(config=get_config(SimplifiedCrashData))

    def test_get_processed(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027",
            data=json.dumps({"foo": "bar"}).encode("utf-8"),
        )

        result = boto_s3_store.get(
            uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="processed"
        )
        assert result == {"foo": "bar"}

    def test_get_processed_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get(
                uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="processed"
            )

    def test_get_raw_dump(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/0bba929f-8721-460c-dead-a43c20071027",
            data=b"\xa0",
        )

        result = boto_s3_store.get(
            uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="raw"
        )
        assert result == b"\xa0"

    def test_get_raw_dump_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get(
                uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="raw"
            )

    def test_get_raw_crash_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get(
                uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="meta"
            )

    def test_bad_arguments(self):
        boto_s3_store = self.get_s3_store()

        with pytest.raises(MissingArgumentError):
            boto_s3_store.get()

        with pytest.raises(MissingArgumentError):
            boto_s3_store.get(uuid="0bba929f-8721-460c-dead-a43c20071027")

        with pytest.raises(BadArgumentError):
            boto_s3_store.get(
                uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="junk"
            )


class TestTelemetryCrashData:
    def get_s3_store(self):
        return TelemetryCrashData(config=get_config(TelemetryCrashData))

    def test_get_data(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/crash_report/20071027/0bba929f-8721-460c-dead-a43c20071027",
            data=json.dumps({"foo": "bar"}).encode("utf-8"),
        )

        result = boto_s3_store.get(uuid="0bba929f-8721-460c-dead-a43c20071027")
        assert result == {"foo": "bar"}

    def test_get_data_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get(uuid="0bba929f-8721-460c-dead-a43c20071027")

    def test_bad_arguments(self):
        boto_s3_store = self.get_s3_store()
        with pytest.raises(MissingArgumentError):
            boto_s3_store.get()

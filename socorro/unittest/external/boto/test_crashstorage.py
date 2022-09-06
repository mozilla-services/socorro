# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os.path

from configman.dotdict import DotDict
import pytest

from socorro.external.boto.crashstorage import (
    BotoS3CrashStorage,
    build_keys,
    dict_to_str,
    TelemetryBotoS3CrashStorage,
)
from socorro.external.crashstorage_base import CrashIDNotFound, MemoryDumpsMapping
from socorro.unittest.external.boto import get_config


@pytest.mark.parametrize(
    "kind, crashid, expected",
    [
        (
            "raw_crash",
            "0bba929f-8721-460c-dead-a43c20071027",
            [
                "v1/raw_crash/20071027/0bba929f-8721-460c-dead-a43c20071027",
                "v2/raw_crash/0bb/20071027/0bba929f-8721-460c-dead-a43c20071027",
            ],
        ),
        (
            "dump_names",
            "0bba929f-8721-460c-dead-a43c20071027",
            [
                "v1/dump_names/0bba929f-8721-460c-dead-a43c20071027",
            ],
        ),
        (
            "processed_crash",
            "0bba929f-8721-460c-dead-a43c20071027",
            [
                "v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027",
            ],
        ),
        # For telemetry
        (
            "crash_report",
            "0bba929f-8721-460c-dead-a43c20071027",
            [
                "v1/crash_report/20071027/0bba929f-8721-460c-dead-a43c20071027",
            ],
        ),
    ],
)
def test_build_keys(kind, crashid, expected):
    assert build_keys(kind, crashid) == expected


class TestBotoS3CrashStorage:
    def get_s3_store(self, tmpdir=None):
        values_source = {}
        if tmpdir is not None:
            values_source["temporary_file_system_storage_path"] = tmpdir
        return BotoS3CrashStorage(config=get_config(BotoS3CrashStorage, values_source))

    def test_save_raw_crash_no_dumps(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        # Run save_raw_crash
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            # This is an empty set of dumps--no dumps!
            MemoryDumpsMapping(),
            "0bba929f-8721-460c-dead-a43c20071027",
        )

        # Verify the raw_crash made it to the right place and has the right
        # contents
        raw_crash = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/raw_crash/20071027/0bba929f-8721-460c-dead-a43c20071027",
        )

        assert json.loads(raw_crash) == {
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
        }

        # Verify dump_names made it to the right place and has the right
        # contents
        dump_names = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert json.loads(dump_names) == []

    def test_save_raw_crash_with_dumps(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        # Run save_raw_crash
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            MemoryDumpsMapping(
                {"dump": b"fake dump", "flash_dump": b"fake flash dump"}
            ),
            "0bba929f-8721-460c-dead-a43c20071027",
        )

        # Verify the raw_crash made it to the right place and has the right contents
        raw_crash = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/raw_crash/20071027/0bba929f-8721-460c-dead-a43c20071027",
        )

        assert json.loads(raw_crash) == {
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
        }

        # Verify dump_names made it to the right place and has the right
        # contents
        dump_names = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert sorted(json.loads(dump_names)) == ["dump", "flash_dump"]

        # Verify dumps
        dump = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/dump/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert dump == b"fake dump"

        flash_dump = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/flash_dump/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert flash_dump == b"fake flash dump"

    def test_save_processed_crash(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_s3_store.save_processed_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            {
                "uuid": "0bba929f-8721-460c-dead-a43c20071027",
                "completed_datetime": "2012-04-08 10:56:50.902884",
                "signature": "now_this_is_a_signature",
            },
        )

        # Verify processed crash is saved
        processed_crash = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert json.loads(processed_crash) == {
            "signature": "now_this_is_a_signature",
            "uuid": "0bba929f-8721-460c-dead-a43c20071027",
            "completed_datetime": "2012-04-08 10:56:50.902884",
        }
        # Verify nothing else got saved
        assert boto_helper.list(bucket_name=bucket) == [
            "v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027"
        ]

    def test_get_raw_crash(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        raw_crash = {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"}

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/raw_crash/20120408/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=dict_to_str(raw_crash).encode("utf-8"),
        )

        result = boto_s3_store.get_raw_crash("936ce666-ff3b-4c7a-9674-367fe2120408")
        assert result == raw_crash

    def test_get_raw_crash_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_raw_crash("0bba929f-dead-dead-dead-a43c20071027")

    def test_get_raw_dump(self, boto_helper):
        """test fetching the raw dump without naming it"""
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b"this is a raw dump",
        )

        result = boto_s3_store.get_raw_dump("936ce666-ff3b-4c7a-9674-367fe2120408")
        assert result == b"this is a raw dump"

    def test_get_raw_dump_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_raw_dump("0bba929f-dead-dead-dead-a43c20071027")

    def test_get_raw_dump_upload_file_minidump(self, boto_helper):
        """test fetching the raw dump, naming it 'upload_file_minidump'"""
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b"this is a raw dump",
        )

        result = boto_s3_store.get_raw_dump(
            "936ce666-ff3b-4c7a-9674-367fe2120408", name="upload_file_minidump"
        )
        assert result == b"this is a raw dump"

    def test_get_raw_dump_empty_string(self, boto_helper):
        """test fetching the raw dump, naming it with empty string"""
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b"this is a raw dump",
        )

        result = boto_s3_store.get_raw_dump(
            "936ce666-ff3b-4c7a-9674-367fe2120408", name=""
        )
        assert result == b"this is a raw dump"

    def test_get_dumps(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'["dump", "flash_dump", "city_dump"]',
        )
        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "dump", the first one',
        )
        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/flash_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "flash_dump", the second one',
        )
        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/city_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "city_dump", the last one',
        )

        result = boto_s3_store.get_dumps("936ce666-ff3b-4c7a-9674-367fe2120408")
        assert result == {
            "dump": b'this is "dump", the first one',
            "flash_dump": b'this is "flash_dump", the second one',
            "city_dump": b'this is "city_dump", the last one',
        }

    def test_get_dumps_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_dumps("0bba929f-dead-dead-dead-a43c20071027")

    def test_get_dumps_as_files(self, boto_helper, tmpdir):
        boto_s3_store = self.get_s3_store(tmpdir=tmpdir)
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'["dump", "flash_dump", "city_dump"]',
        )
        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "dump", the first one',
        )
        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/flash_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "flash_dump", the second one',
        )
        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/city_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "city_dump", the last one',
        )

        result = boto_s3_store.get_dumps_as_files(
            "936ce666-ff3b-4c7a-9674-367fe2120408"
        )

        # We don't care much about the mocked internals as the bulk of that
        # function is tested elsewhere.
        # We just need to be concerned about the file writing worked.
        expected = {
            "flash_dump": os.path.join(
                str(tmpdir),
                "936ce666-ff3b-4c7a-9674-367fe2120408.flash_dump.TEMPORARY.dump",
            ),
            "city_dump": os.path.join(
                str(tmpdir),
                "936ce666-ff3b-4c7a-9674-367fe2120408.city_dump.TEMPORARY.dump",
            ),
            "upload_file_minidump": os.path.join(
                str(tmpdir),
                "936ce666-ff3b-4c7a-9674-367fe2120408.upload_file_minidump.TEMPORARY.dump",
            ),
        }
        assert result == expected

    def test_get_processed(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        processed_crash = DotDict(
            {
                "a": {"b": {"c": 11}},
                "sensitive": {"x": 2},
                "not_url": "not a url",
                # These keys do not survive redaction
                "url": "http://example.com",
                "json_dump": {"sensitive": 22},
            }
        )

        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/processed_crash/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=dict_to_str(processed_crash).encode("utf-8"),
        )

        result = boto_s3_store.get_processed("936ce666-ff3b-4c7a-9674-367fe2120408")
        assert result == processed_crash

    def test_get_processed_not_found(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_processed("0bba929f-dead-dead-dead-a43c20071027")


class TestTelemetryBotoS3CrashStorage:
    def get_s3_store(self):
        return TelemetryBotoS3CrashStorage(
            config=get_config(TelemetryBotoS3CrashStorage)
        )

    def test_save_processed_crash(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        # Run save_processed_crash
        boto_s3_store.save_processed_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            {
                "uuid": "0bba929f-8721-460c-dead-a43c20071027",
                "completed_datetime": "2012-04-08 10:56:50.902884",
                "signature": "now_this_is_a_signature",
                "os_name": "Linux",
                "some_random_key": "should not appear",
                "json_dump": {
                    "crash_info": {
                        "address": "0x6357737b",
                        "some_random_key": "should not appear",
                    },
                    "crashing_thread": {
                        "frames": [
                            {
                                "frame": 0,
                                "module": "xul.dll",
                                "function": None,
                                "some_random_key": "should not appear",
                            },
                        ],
                    },
                },
            },
        )

        # Get the crash data we just saved from the bucket and verify it's
        # contents
        crash_data = boto_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/crash_report/20071027/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert json.loads(crash_data) == {
            "platform": "Linux",
            "signature": "now_this_is_a_signature",
            "uuid": "0bba929f-8721-460c-dead-a43c20071027",
            "json_dump": {
                "crash_info": {
                    "address": "0x6357737b",
                },
                "crashing_thread": {
                    "frames": [
                        {
                            "frame": 0,
                            "function": None,
                            "module": "xul.dll",
                        },
                    ],
                },
            },
        }

    def test_get_processed(self, boto_helper):
        boto_s3_store = self.get_s3_store()
        bucket = boto_s3_store.conn.bucket
        boto_helper.create_bucket(bucket)

        crash_data = {
            "platform": "Linux",
            "signature": "now_this_is_a_signature",
            "uuid": "0bba929f-8721-460c-dead-a43c20071027",
        }

        # Save the data to S3 so we have something to get
        boto_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/crash_report/20071027/0bba929f-8721-460c-dead-a43c20071027",
            data=json.dumps(crash_data).encode("utf-8"),
        )

        # Get the crash and assert it's the same data
        data = boto_s3_store.get_processed(
            crash_id="0bba929f-8721-460c-dead-a43c20071027"
        )
        assert data == crash_data

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os.path
import os

import pytest

from socorro.external.boto.crashstorage import build_keys, dict_to_str
from socorro.external.crashstorage_base import CrashIDNotFound, MemoryDumpsMapping
from socorro.libclass import build_instance_from_settings


CRASHSTORAGE_SETTINGS = {
    "class": "socorro.external.boto.crashstorage.BotoS3CrashStorage",
    "options": {
        "bucket": os.environ["CRASHSTORAGE_S3_BUCKET"],
        "region": os.environ["CRASHSTORAGE_S3_REGION"],
        "access_key": os.environ["CRASHSTORAGE_S3_ACCESS_KEY"],
        "secret_access_key": os.environ["CRASHSTORAGE_S3_SECRET_ACCESS_KEY"],
        "endpoint_url": os.environ["AWS_ENDPOINT_URL"],
    },
}


TELEMETRY_SETTINGS = {
    "class": "socorro.external.boto.crashstorage.TelemetryBotoS3CrashStorage",
    "options": {
        "bucket": os.environ["CRASHSTORAGE_S3_BUCKET"],
        "region": os.environ["CRASHSTORAGE_S3_REGION"],
        "access_key": os.environ["CRASHSTORAGE_S3_ACCESS_KEY"],
        "secret_access_key": os.environ["CRASHSTORAGE_S3_SECRET_ACCESS_KEY"],
        "endpoint_url": os.environ["AWS_ENDPOINT_URL"],
    },
}


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
    def test_save_raw_crash_no_dumps(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        # Run save_raw_crash
        crashstorage.save_raw_crash(
            raw_crash={"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            # This is an empty set of dumps--no dumps!
            dumps=MemoryDumpsMapping(),
            crash_id="0bba929f-8721-460c-dead-a43c20071027",
        )

        # Verify the raw_crash made it to the right place and has the right
        # contents
        raw_crash = s3_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/raw_crash/20071027/0bba929f-8721-460c-dead-a43c20071027",
        )

        assert json.loads(raw_crash) == {
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
        }

        # Verify dump_names made it to the right place and has the right
        # contents
        dump_names = s3_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert json.loads(dump_names) == []

    def test_save_raw_crash_with_dumps(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        # Run save_raw_crash
        crashstorage.save_raw_crash(
            raw_crash={"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            dumps=MemoryDumpsMapping(
                {"dump": b"fake dump", "content_dump": b"fake content dump"}
            ),
            crash_id="0bba929f-8721-460c-dead-a43c20071027",
        )

        # Verify the raw_crash made it to the right place and has the right contents
        raw_crash = s3_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/raw_crash/20071027/0bba929f-8721-460c-dead-a43c20071027",
        )

        assert json.loads(raw_crash) == {
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
        }

        # Verify dump_names made it to the right place and has the right
        # contents
        dump_names = s3_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert sorted(json.loads(dump_names)) == ["content_dump", "dump"]

        # Verify dumps
        dump = s3_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/dump/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert dump == b"fake dump"

        content_dump = s3_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/content_dump/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert content_dump == b"fake content dump"

    def test_save_processed_crash(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        crashstorage.save_processed_crash(
            raw_crash={"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            processed_crash={
                "uuid": "0bba929f-8721-460c-dead-a43c20071027",
                "completed_datetime": "2012-04-08 10:56:50.902884",
                "signature": "now_this_is_a_signature",
            },
        )

        # Verify processed crash is saved
        processed_crash = s3_helper.download_fileobj(
            bucket_name=bucket,
            key="v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027",
        )
        assert json.loads(processed_crash) == {
            "signature": "now_this_is_a_signature",
            "uuid": "0bba929f-8721-460c-dead-a43c20071027",
            "completed_datetime": "2012-04-08 10:56:50.902884",
        }
        # Verify nothing else got saved
        assert s3_helper.list(bucket_name=bucket) == [
            "v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027"
        ]

    def test_get_raw_crash(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        raw_crash = {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"}

        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/raw_crash/20120408/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=dict_to_str(raw_crash).encode("utf-8"),
        )

        result = crashstorage.get_raw_crash("936ce666-ff3b-4c7a-9674-367fe2120408")
        expected = {
            "metadata": {
                "collector_notes": [],
                "dump_checksums": {},
                "migrated_from_version_1": True,
                "payload": "unknown",
                "payload_compressed": "0",
            },
            "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00",
            "version": 2,
        }
        assert result == expected

    def test_get_raw_crash_not_found(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            crashstorage.get_raw_crash("0bba929f-dead-dead-dead-a43c20071027")

    def test_get_raw_dump(self, s3_helper):
        """test fetching the raw dump without naming it"""
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b"this is a raw dump",
        )

        result = crashstorage.get_raw_dump("936ce666-ff3b-4c7a-9674-367fe2120408")
        assert result == b"this is a raw dump"

    def test_get_raw_dump_not_found(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            crashstorage.get_raw_dump("0bba929f-dead-dead-dead-a43c20071027")

    def test_get_raw_dump_upload_file_minidump(self, s3_helper):
        """test fetching the raw dump, naming it 'upload_file_minidump'"""
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b"this is a raw dump",
        )

        result = crashstorage.get_raw_dump(
            "936ce666-ff3b-4c7a-9674-367fe2120408", name="upload_file_minidump"
        )
        assert result == b"this is a raw dump"

    def test_get_raw_dump_empty_string(self, s3_helper):
        """test fetching the raw dump, naming it with empty string"""
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b"this is a raw dump",
        )

        result = crashstorage.get_raw_dump(
            "936ce666-ff3b-4c7a-9674-367fe2120408", name=""
        )
        assert result == b"this is a raw dump"

    def test_get_dumps(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'["dump", "content_dump", "city_dump"]',
        )
        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "dump", the first one',
        )
        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/content_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "content_dump", the second one',
        )
        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/city_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "city_dump", the last one',
        )

        result = crashstorage.get_dumps("936ce666-ff3b-4c7a-9674-367fe2120408")
        assert result == {
            "dump": b'this is "dump", the first one',
            "content_dump": b'this is "content_dump", the second one',
            "city_dump": b'this is "city_dump", the last one',
        }

    def test_get_dumps_not_found(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            crashstorage.get_dumps("0bba929f-dead-dead-dead-a43c20071027")

    def test_get_dumps_as_files(self, s3_helper, tmp_path):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump_names/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'["dump", "content_dump", "city_dump"]',
        )
        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "dump", the first one',
        )
        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/content_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "content_dump", the second one',
        )
        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key="v1/city_dump/936ce666-ff3b-4c7a-9674-367fe2120408",
            data=b'this is "city_dump", the last one',
        )

        result = crashstorage.get_dumps_as_files(
            crash_id="936ce666-ff3b-4c7a-9674-367fe2120408",
            tmpdir=str(tmp_path),
        )

        # We don't care much about the mocked internals as the bulk of that function is
        # tested elsewhere. We just need to be concerned about the file writing worked.
        expected = {
            "content_dump": os.path.join(
                str(tmp_path),
                "936ce666-ff3b-4c7a-9674-367fe2120408.content_dump.TEMPORARY.dump",
            ),
            "city_dump": os.path.join(
                str(tmp_path),
                "936ce666-ff3b-4c7a-9674-367fe2120408.city_dump.TEMPORARY.dump",
            ),
            "upload_file_minidump": os.path.join(
                str(tmp_path),
                "936ce666-ff3b-4c7a-9674-367fe2120408.upload_file_minidump.TEMPORARY.dump",
            ),
        }
        assert result == expected

    def test_get_processed_crash(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        crash_id = "936ce666-ff3b-4c7a-9674-367fe2120408"
        s3_helper.create_bucket(bucket)

        processed_crash = {
            "a": {"b": {"c": 11}},
            "sensitive": {"x": 2},
            "not_url": "not a url",
            # These keys do not survive redaction
            "url": "http://example.com",
            "json_dump": {"sensitive": 22},
        }

        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key=f"v1/processed_crash/{crash_id}",
            data=dict_to_str(processed_crash).encode("utf-8"),
        )

        result = crashstorage.get_processed_crash(crash_id)
        assert result == processed_crash

    def test_get_processed_not_found(self, s3_helper):
        crashstorage = build_instance_from_settings(CRASHSTORAGE_SETTINGS)
        bucket = CRASHSTORAGE_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            crashstorage.get_processed_crash("0bba929f-dead-dead-dead-a43c20071027")


class TestTelemetryBotoS3CrashStorage:
    def test_save_processed_crash(self, s3_helper):
        crashstorage = build_instance_from_settings(TELEMETRY_SETTINGS)
        bucket = TELEMETRY_SETTINGS["options"]["bucket"]
        s3_helper.create_bucket(bucket)

        # Run save_processed_crash
        crashstorage.save_processed_crash(
            raw_crash={"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            processed_crash={
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

        # Get the crash data we just saved from the bucket and verify it's contents
        crash_data = s3_helper.download_fileobj(
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

    def test_get_processed_crash(self, s3_helper):
        crashstorage = build_instance_from_settings(TELEMETRY_SETTINGS)
        bucket = TELEMETRY_SETTINGS["options"]["bucket"]
        crash_id = "0bba929f-8721-460c-dead-a43c20071027"
        s3_helper.create_bucket(bucket)

        crash_data = {
            "platform": "Linux",
            "signature": "now_this_is_a_signature",
            "uuid": "0bba929f-8721-460c-dead-a43c20071027",
        }

        # Save the data to S3 so we have something to get
        s3_helper.upload_fileobj(
            bucket_name=bucket,
            key=f"v1/crash_report/20{crash_id[-6:]}/{crash_id}",
            data=json.dumps(crash_data).encode("utf-8"),
        )

        # Get the crash and assert it's the same data
        data = crashstorage.get_processed_crash(crash_id=crash_id)
        assert data == crash_data

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os

import pytest

from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import MissingArgumentError, BadArgumentError
from socorro.libclass import build_instance_from_settings
from socorro.lib.libooid import create_new_ooid


CRASHDATA_SETTINGS = {
    "class": "socorro.external.boto.crash_data.SimplifiedCrashData",
    "options": {
        "bucket": os.environ["CRASHSTORAGE_S3_BUCKET"],
        "region": os.environ["CRASHSTORAGE_S3_REGION"],
        "access_key": os.environ["CRASHSTORAGE_S3_ACCESS_KEY"],
        "secret_access_key": os.environ["CRASHSTORAGE_S3_SECRET_ACCESS_KEY"],
        "endpoint_url": os.environ["LOCAL_DEV_AWS_ENDPOINT_URL"],
    },
}

TELEMETRY_SETTINGS = {
    "class": "socorro.external.boto.crash_data.TelemetryCrashData",
    "options": {
        "bucket": os.environ["TELEMETRY_S3_BUCKET"],
        "region": os.environ["TELEMETRY_S3_REGION"],
        "access_key": os.environ["TELEMETRY_S3_ACCESS_KEY"],
        "secret_access_key": os.environ["TELEMETRY_S3_SECRET_ACCESS_KEY"],
        "endpoint_url": os.environ["LOCAL_DEV_AWS_ENDPOINT_URL"],
    },
}


class TestSimplifiedCrashData:
    def test_get_processed(self, s3_helper):
        crashdata = build_instance_from_settings(CRASHDATA_SETTINGS)

        bucket = CRASHDATA_SETTINGS["options"]["bucket"]
        crash_id = create_new_ooid()
        s3_helper.create_bucket(bucket)

        s3_helper.upload(
            bucket_name=bucket,
            key=f"v1/processed_crash/{crash_id}",
            data=json.dumps({"foo": "bar"}).encode("utf-8"),
        )

        result = crashdata.get(uuid=crash_id, datatype="processed")
        assert result == {"foo": "bar"}

    def test_get_processed_not_found(self, s3_helper):
        crashdata = build_instance_from_settings(CRASHDATA_SETTINGS)

        bucket = CRASHDATA_SETTINGS["options"]["bucket"]
        crash_id = create_new_ooid()
        s3_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            crashdata.get(uuid=crash_id, datatype="processed")

    def test_get_raw_dump(self, s3_helper):
        crashdata = build_instance_from_settings(CRASHDATA_SETTINGS)

        bucket = CRASHDATA_SETTINGS["options"]["bucket"]
        crash_id = create_new_ooid()
        s3_helper.create_bucket(bucket)

        s3_helper.upload(
            bucket_name=bucket,
            key=f"v1/dump/{crash_id}",
            data=b"\xa0",
        )

        result = crashdata.get(uuid=crash_id, datatype="raw")
        assert result == b"\xa0"

    def test_get_raw_dump_not_found(self, s3_helper):
        crashdata = build_instance_from_settings(CRASHDATA_SETTINGS)

        bucket = CRASHDATA_SETTINGS["options"]["bucket"]
        crash_id = create_new_ooid()
        s3_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            crashdata.get(uuid=crash_id, datatype="raw")

    def test_get_raw_crash_not_found(self, s3_helper):
        crashdata = build_instance_from_settings(CRASHDATA_SETTINGS)

        bucket = CRASHDATA_SETTINGS["options"]["bucket"]
        crash_id = create_new_ooid()
        s3_helper.create_bucket(bucket)

        with pytest.raises(CrashIDNotFound):
            crashdata.get(uuid=crash_id, datatype="meta")

    def test_bad_arguments(self):
        crashdata = build_instance_from_settings(CRASHDATA_SETTINGS)

        crash_id = create_new_ooid()

        with pytest.raises(MissingArgumentError):
            crashdata.get()

        with pytest.raises(MissingArgumentError):
            crashdata.get(uuid=crash_id)

        with pytest.raises(BadArgumentError):
            crashdata.get(uuid=crash_id, datatype="junk")


class TestTelemetryCrashData:
    def test_get_data(self, s3_helper):
        crashdata = build_instance_from_settings(TELEMETRY_SETTINGS)

        bucket = TELEMETRY_SETTINGS["options"]["bucket"]
        crash_id = create_new_ooid()

        s3_helper.create_bucket(bucket)
        s3_helper.upload(
            bucket_name=bucket,
            key=f"v1/crash_report/20{crash_id[-6:]}/{crash_id}",
            data=json.dumps({"foo": "bar"}).encode("utf-8"),
        )

        result = crashdata.get(uuid=crash_id)
        assert result == {"foo": "bar"}

    def test_get_data_not_found(self, s3_helper):
        crashdata = build_instance_from_settings(TELEMETRY_SETTINGS)

        bucket = TELEMETRY_SETTINGS["options"]["bucket"]
        crash_id = create_new_ooid()

        s3_helper.create_bucket(bucket)
        with pytest.raises(CrashIDNotFound):
            crashdata.get(uuid=crash_id)

    def test_bad_arguments(self):
        crashdata = build_instance_from_settings(TELEMETRY_SETTINGS)

        with pytest.raises(MissingArgumentError):
            crashdata.get()

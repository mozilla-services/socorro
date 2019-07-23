# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

import mock
from moto import mock_s3_deprecated
import pytest

from socorro.external.boto.crash_data import SimplifiedCrashData, TelemetryCrashData
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import MissingArgumentError, BadArgumentError
from socorro.unittest.external.boto import get_config


class TestSimplifiedCrashData(object):
    def get_s3_store(self):
        return SimplifiedCrashData(config=get_config(SimplifiedCrashData))

    @mock_s3_deprecated
    def test_get_processed(self, boto_helper):
        boto_helper.set_contents_from_string(
            bucket_name="crashstats",
            key="/v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027",
            value=json.dumps({"foo": "bar"}),
        )

        boto_s3_store = self.get_s3_store()

        result = boto_s3_store.get(
            uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="processed"
        )
        assert result == {"foo": "bar"}

    @mock_s3_deprecated
    def test_get_processed_not_found(self, boto_helper):
        with mock.patch("socorro.lib.transaction.BACKOFF_TIMES", [0]):
            boto_helper.get_or_create_bucket("crashstats")

            boto_s3_store = self.get_s3_store()
            with pytest.raises(CrashIDNotFound):
                boto_s3_store.get(
                    uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="processed"
                )

    @mock_s3_deprecated
    def test_get_raw_dump(self, boto_helper):
        boto_helper.set_contents_from_string(
            bucket_name="crashstats",
            key="/v1/dump/0bba929f-8721-460c-dead-a43c20071027",
            value=b"\xa0",
        )

        boto_s3_store = self.get_s3_store()

        result = boto_s3_store.get(
            uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="raw"
        )
        assert result == b"\xa0"

    @mock_s3_deprecated
    def test_get_raw_dump_not_found(self, boto_helper):
        with mock.patch("socorro.lib.transaction.BACKOFF_TIMES", [0]):
            boto_helper.get_or_create_bucket("crashstats")

            boto_s3_store = self.get_s3_store()

            with pytest.raises(CrashIDNotFound):
                boto_s3_store.get(
                    uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="raw"
                )

    @mock_s3_deprecated
    def test_get_raw_crash_not_found(self, boto_helper):
        with mock.patch("socorro.lib.transaction.BACKOFF_TIMES", [0]):
            boto_helper.get_or_create_bucket("crashstats")

            boto_s3_store = self.get_s3_store()

            with pytest.raises(CrashIDNotFound):
                boto_s3_store.get(
                    uuid="0bba929f-8721-460c-dead-a43c20071027", datatype="meta"
                )

    @mock_s3_deprecated
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


class TestTelemetryCrashData(object):
    def get_s3_store(self):
        config = get_config(
            cls=TelemetryCrashData, values_source={"bucket_name": "telemetry-bucket"}
        )

        return TelemetryCrashData(config)

    @mock_s3_deprecated
    def test_get_data(self, boto_helper):
        boto_helper.set_contents_from_string(
            bucket_name="telemetry-bucket",
            key="/v1/crash_report/20071027/0bba929f-8721-460c-dead-a43c20071027",
            value=json.dumps({"foo": "bar"}),
        )

        boto_s3_store = self.get_s3_store()

        result = boto_s3_store.get(uuid="0bba929f-8721-460c-dead-a43c20071027")
        assert result == {"foo": "bar"}

    @mock_s3_deprecated
    def test_get_data_not_found(self, boto_helper):
        boto_helper.get_or_create_bucket("crashstats")

        boto_s3_store = self.get_s3_store()
        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get(uuid="0bba929f-8721-460c-dead-a43c20071027")

    @mock_s3_deprecated
    def test_bad_arguments(self):
        boto_s3_store = self.get_s3_store()
        with pytest.raises(MissingArgumentError):
            boto_s3_store.get()

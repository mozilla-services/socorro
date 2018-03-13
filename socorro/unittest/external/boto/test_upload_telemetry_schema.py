# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from moto import mock_s3_deprecated
import pytest

from socorro.external.boto.upload_telemetry_schema import UploadTelemetrySchema
from socorro.unittest.external.boto import get_config


class TestUploadTelemetrySchema:
    @mock_s3_deprecated
    def test_bucket_not_found(self):
        # If the bucket isn't found, the script should tell the user and return
        # a non-zero exit code
        config = get_config(UploadTelemetrySchema)
        app = UploadTelemetrySchema(config)

        assert app.main() == 1
        app.config.logger.error.assert_called_once_with(
            'Failure: The %s S3 bucket must be created first.',
            'crashstats'
        )

    @mock_s3_deprecated
    def test_upload_worked(self, boto_helper):
        boto_helper.get_or_create_bucket('crashstats')
        config = get_config(UploadTelemetrySchema)
        app = UploadTelemetrySchema(config)

        assert app.main() == 0
        app.config.logger.info.assert_called_once_with(
            'Success: Schema uploaded!'
        )

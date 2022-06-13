# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro.external.boto.upload_telemetry_schema import UploadTelemetrySchema
from socorro.unittest.external.boto import get_config


class TestUploadTelemetrySchema:
    def test_upload_worked(self, boto_helper, caplogpp):
        caplogpp.set_level("DEBUG")
        config = get_config(UploadTelemetrySchema)
        app = UploadTelemetrySchema(config)
        boto_helper.create_bucket(app.config.telemetry.bucket_name)

        assert app.main() == 0
        recs = [rec.message for rec in caplogpp.records]
        assert "Success: Schema uploaded!" in recs

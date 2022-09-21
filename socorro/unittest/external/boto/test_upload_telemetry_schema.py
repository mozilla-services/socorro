# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro.external.boto.upload_telemetry_schema import UploadTelemetrySchema
from socorro.unittest.external.boto import get_config


class TestUploadTelemetrySchema:
    def test_upload_worked(self, boto_helper, caplogpp, monkeypatch):
        # NOTE(willkg): configman apps look at sys.argv for command line arguments, so
        # we monkey patch sys.argv so it doesn't pick up pytest arguments and errors
        # out
        monkeypatch.setattr("sys.argv", ["upload_telemetry_schema.py"])
        caplogpp.set_level("DEBUG")
        config = get_config(UploadTelemetrySchema)
        app = UploadTelemetrySchema(config)
        boto_helper.create_bucket(app.config.telemetry.bucket_name)

        assert app.run() == 0
        recs = [rec.message for rec in caplogpp.records]
        assert "Success: Schema uploaded!" in recs

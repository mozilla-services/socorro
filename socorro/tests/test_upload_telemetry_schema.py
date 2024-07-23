# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os

from click.testing import CliRunner

from upload_telemetry_schema import upload


TELEMETRY_BUCKET = os.environ["TELEMETRY_GCS_BUCKET"]


def test_it_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(upload, ["--help"])
    assert result.exit_code == 0


def test_upload(gcs_helper):
    """Tests whether the file is uploaded and has the right properites"""
    gcs_helper.create_bucket(TELEMETRY_BUCKET)

    runner = CliRunner()
    result = runner.invoke(upload)

    assert result.exit_code == 0

    # Get the crash data we just saved from the bucket and verify it's contents
    crash_data = gcs_helper.download(
        bucket_name=TELEMETRY_BUCKET,
        key="telemetry_socorro_crash.json",
    )
    schema = json.loads(crash_data)
    assert "definitions" in schema

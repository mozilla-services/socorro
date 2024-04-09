# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from click.testing import CliRunner

from upload_telemetry_schema import upload


def test_it_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(upload, ["--help"])
    assert result.exit_code == 0


def test_upload(storage_helper):
    """Tests whether the file is uploaded and has the right properites"""
    telemetry_bucket = storage_helper.get_telemetry_bucket()
    storage_helper.create_bucket(telemetry_bucket)

    runner = CliRunner()
    result = runner.invoke(upload)

    assert result.exit_code == 0

    # Get the crash data we just saved from the bucket and verify it's contents
    crash_data = storage_helper.download(
        bucket_name=telemetry_bucket,
        key="telemetry_socorro_crash.json",
    )
    schema = json.loads(crash_data)
    assert "definitions" in schema

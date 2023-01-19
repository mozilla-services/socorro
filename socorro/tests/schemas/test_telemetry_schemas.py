# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from click.testing import CliRunner
import jsonschema

from socorro.schemas import get_file_content
from socorro.schemas.validate_telemetry_socorro_crash import validate_and_test


def test_validate_telemetry_crash_schema():
    """Validate the telemetry_crash.json schema is valid jsonschema"""
    schema = get_file_content("telemetry_socorro_crash.json")
    jsonschema.Draft4Validator.check_schema(schema)


def test_validate_telemetry_socorro_crash_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(validate_and_test, ["--help"])
    assert result.exit_code == 0

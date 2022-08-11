# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from click.testing import CliRunner

from socorro.schemas.validate_processed_crash import validate_and_test


def test_it_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(validate_and_test, ["--help"])
    assert result.exit_code == 0

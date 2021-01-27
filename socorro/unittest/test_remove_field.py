# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

from click.testing import CliRunner

# Have to include the scripts/ directory so it imports
sys.path.insert(0, os.path.join(os.getcwd(), "bin"))

from remove_field import cmd_remove_field  # noqa


def test_it_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(cmd_remove_field, ["--help"])
    assert result.exit_code == 0

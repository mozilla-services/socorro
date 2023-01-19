# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from click.testing import CliRunner

# Have to include the scripts/ directory so it imports
sys.path.insert(0, os.path.join(os.getcwd(), "bin"))

from find_crashes_with_field import cmd_list_crashids  # noqa


def test_it_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(cmd_list_crashids, ["--help"])
    assert result.exit_code == 0

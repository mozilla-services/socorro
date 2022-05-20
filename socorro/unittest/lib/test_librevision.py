# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from pathlib import Path

from socorro.lib.librevision import get_version_info


def test_get_version_info(tmpdir):
    version_info = {"commit": "abcde"}
    version_json = tmpdir / "version.json"
    version_json.write(json.dumps(version_info))

    # Test with str path
    tmpdir = str(tmpdir)
    assert get_version_info(tmpdir) == version_info

    # Test with Path path
    tmpdir = Path(tmpdir)
    assert get_version_info(tmpdir) == version_info


def test_version_info_malformed(tmpdir):
    """Return {} if version.json is malformed"""
    version_info = "{abc"
    version_json = tmpdir / "version.json"
    version_json.write(version_info)

    # Test with str path
    tmpdir = str(tmpdir)
    assert get_version_info(tmpdir) == {}

    # Test with Path path
    tmpdir = Path(tmpdir)
    assert get_version_info(tmpdir) == {}


def test_get_version_info_no_file(tmpdir):
    """Return {} if there is no version.json"""
    # Test with str path
    tmpdir = str(tmpdir)
    assert get_version_info(tmpdir) == {}

    # Test with Path path
    tmpdir = Path(tmpdir)
    assert get_version_info(tmpdir) == {}

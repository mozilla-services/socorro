# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from pathlib import Path

from socorro.lib.libdockerflow import get_version_info


def test_get_version_info(tmp_path):
    version_info = {"commit": "abcde"}
    version_json = tmp_path / "version.json"
    version_json.write_text(json.dumps(version_info))

    # Test with str path
    tmp_path = str(tmp_path)
    assert get_version_info(tmp_path) == version_info

    # Test with Path path
    tmp_path = Path(tmp_path)
    assert get_version_info(tmp_path) == version_info


def test_version_info_malformed(tmp_path):
    """Return {} if version.json is malformed"""
    version_info = "{abc"
    version_json = tmp_path / "version.json"
    version_json.write_text(version_info)

    # Test with str path
    tmp_path = str(tmp_path)
    assert get_version_info(tmp_path) == {}

    # Test with Path path
    tmp_path = Path(tmp_path)
    assert get_version_info(tmp_path) == {}


def test_get_version_info_no_file(tmp_path):
    """Return {} if there is no version.json"""
    # Test with str path
    tmp_path = str(tmp_path)
    assert get_version_info(tmp_path) == {}

    # Test with Path path
    tmp_path = Path(tmp_path)
    assert get_version_info(tmp_path) == {}

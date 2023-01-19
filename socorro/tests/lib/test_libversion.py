# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib.libversion import generate_semver, VersionParseError


@pytest.mark.parametrize(
    "version, expected",
    [
        # Firefox nightly variations
        ("62.0a1", (62, 0, 0, "alpha.1.rc.999", None)),
        # Firefox beta variations
        ("63.0b9", (63, 0, 0, "beta.9.rc.999", None)),
        ("63.0b9rc1", (63, 0, 0, "beta.9.rc.1", None)),
        # Firefox release variations
        ("62.0", (62, 0, 0, "release.rc.999", None)),
        ("62.0.1", (62, 0, 1, "release.rc.999", None)),
        ("62.0.2", (62, 0, 2, "release.rc.999", None)),
        ("62.0.2rc1", (62, 0, 2, "release.rc.1", None)),
        # Firefox ESR
        ("62.0.2esr", (62, 0, 2, "xsr.rc.999", None)),
        ("62.0.2esrrc1", (62, 0, 2, "xsr.rc.1", None)),
        ("62.0.2esrrc2", (62, 0, 2, "xsr.rc.2", None)),
        # Fenix alpha
        ("0.0a1", (0, 0, 0, "alpha.1.rc.999", None)),
        # Fenix Beta--this is the only truly semver one, so we don't tweak it
        ("75.0.0-beta.2b0", (75, 0, 0, "beta.2b0", None)),
    ],
)
def test_generate_semver(version, expected):
    assert generate_semver(version).to_tuple() == expected


@pytest.mark.parametrize("version", [None, "", "N/A", "42p"])
def test_junk(version):
    with pytest.raises(VersionParseError):
        generate_semver(version)


def test_generate_semver_sorted():
    """Test whether the result sorts correctly"""
    versions = [
        "62.0.2a1",
        "62.0.2b1",
        "62.0.2b5rc1",
        "62.0.2b5",
        "62.0.2rc1",
        "62.0.2",
        "62.0.2esrrc1",
        "62.0.2esr",
    ]

    sorted_versions = sorted(versions, key=lambda v: generate_semver(v))
    assert sorted_versions == versions

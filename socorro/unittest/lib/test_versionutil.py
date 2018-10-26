# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from socorro.lib.versionutil import (
    generate_version_key,
    VersionParseError
)


@pytest.mark.parametrize('version, expected', [
    # Nightly variations
    ('62.0a1', '062000000a001999'),

    # Aurora versions
    ('3.7a5pre', '003007000a001001'),

    # Beta variations
    ('63.0b9', '063000000b009999'),
    ('63.0b9rc1', '063000000b009001'),
    ('4.0b2pre', '004000000b002001'),

    # Release variations
    ('62.0', '062000000r000999'),
    ('62.0.1', '062000001r000999'),
    ('62.0.2', '062000002r000999'),
    ('62.0.2rc1', '062000002r000001'),

    # ESR
    ('62.0.2esr', '062000002x000999'),
    ('62.0.2esrrc1', '062000002x000001'),
    ('62.0.2esrrc2', '062000002x000002'),
])
def test_generate_version_key(version, expected):
    assert generate_version_key(version) == expected


@pytest.mark.parametrize('version', [
    None,
    '',
    '42p',
])
def test_junk(version):
    with pytest.raises(VersionParseError):
        generate_version_key(version)


def test_generate_version_key_sorted():
    """Test whether the result sorts correctly"""
    versions = [
        '62.0.2a1',
        '62.0.2b1',
        '62.0.2b5rc1',
        '62.0.2b5',
        '62.0.2rc1',
        '62.0.2',
        '62.0.2esrrc1',
        '62.0.2esr',
    ]

    sorted_versions = sorted(
        versions,
        key=lambda v: generate_version_key(v)
    )
    assert sorted_versions == versions

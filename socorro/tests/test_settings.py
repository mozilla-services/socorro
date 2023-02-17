# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro import Settings


KEY1 = "123"

KEY2 = {
    "subkey1": "abc",
    "subkey2": [5, 6, 7],
}


def test_settings():
    settings = Settings("socorro.tests.test_settings")
    assert settings.KEY1 == "123"
    assert settings.KEY2 == {"subkey1": "abc", "subkey2": [5, 6, 7]}


def test_settings_override():
    settings = Settings("socorro.tests.test_settings")
    with settings.override(KEY1="456"):
        with settings.override(KEY1="789"):
            assert settings.KEY1 == "789"
        assert settings.KEY1 == "456"

    assert settings.KEY1 == "123"
    assert settings.KEY2 == {"subkey1": "abc", "subkey2": [5, 6, 7]}


def test_settings_override_deep():
    settings = Settings("socorro.tests.test_settings")
    with settings.override(
        **{
            "KEY2.subkey1": "def",
            # KEY2["subkey2"][1]
            "KEY2.subkey2.1": 9,
        }
    ):
        assert settings.KEY2 == {"subkey1": "def", "subkey2": [5, 9, 7]}

    assert settings.KEY1 == "123"
    assert settings.KEY2 == {"subkey1": "abc", "subkey2": [5, 6, 7]}

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import importlib
from pathlib import Path

import pytest


# NOTE(willkg): We do this so that we can extract signature generation into its
# own namespace as an external library. This allows the tests to run if it's in
# "siggen" or "socorro.signature".
base_module = ".".join(__name__.split(".")[:-2])
siglists_utils = importlib.import_module(base_module + ".siglists_utils")


class TestSigLists:
    def test_loading_files(self):
        signature_lists = (
            "irrelevant_signature_re",
            "prefix_signature_re",
            "signature_sentinels",
            "signatures_with_line_numbers_re",
        )

        for name in signature_lists:
            content = siglists_utils.get_signature_list_content(name)
            assert len(content) > 0

            for line in content:
                assert len(line) > 0
                # Some items can be tuples; for the str lines, make sure they don't
                # start with a #
                if isinstance(line, str):
                    assert not line.startswith("#")

    def test_valid_entries(self):
        source = Path(__file__).parent / "siglists"
        expected = ("fooBarStuff", "moz::.*", "@0x[0-9a-fA-F]{2,}")
        content = siglists_utils.get_signature_list_content(
            "test-valid-sig-list", source=source
        )
        assert content == expected

    def test_invalid_entry(self):
        source = Path(__file__).parent / "siglists"

        with pytest.raises(siglists_utils.BadRegularExpressionLineError) as exc_info:
            siglists_utils.get_signature_list_content(
                "test-invalid-sig-list", source=source
            )

        msg = exc_info.exconly()
        assert "BadRegularExpressionLineError: Regex error: " in msg
        assert msg.endswith("at line 3")
        assert "test-invalid-sig-list.txt" in msg

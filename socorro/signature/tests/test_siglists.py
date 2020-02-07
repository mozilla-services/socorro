# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import importlib
from unittest import mock

from pkg_resources import resource_stream
import pytest

# NOTE(willkg): We do this so that we can extract signature generation into its
# own namespace as an external library. This allows the tests to run if it's in
# "siggen" or "socorro.signature".
base_module = ".".join(__name__.split(".")[:-2])
siglists_utils = importlib.import_module(base_module + ".siglists_utils")


def _fake_stream(pkg, filepath):
    return resource_stream(__name__, filepath)


class TestSigLists:
    def test_loading_files(self):
        all_lists = (
            "IRRELEVANT_SIGNATURE_RE",
            "PREFIX_SIGNATURE_RE",
            "SIGNATURE_SENTINELS",
            "SIGNATURES_WITH_LINE_NUMBERS_RE",
        )

        for list_name in all_lists:
            content = getattr(siglists_utils, list_name)
            assert content

            for line in content:
                assert line
                # Some items can be tuples; for the str lines, make sure they
                # don't start with a #
                if isinstance(line, str):
                    assert not line.startswith("#")

    @mock.patch(base_module + ".siglists_utils.resource_stream")
    def test_valid_entries(self, mocked_stream):
        mocked_stream.side_effect = _fake_stream

        expected = ("fooBarStuff", "moz::.*", "@0x[0-9a-fA-F]{2,}")
        content = siglists_utils._get_file_content("test-valid-sig-list")
        assert content == expected

    @mock.patch(base_module + ".siglists_utils.resource_stream")
    def test_invalid_entry(self, mocked_stream):
        mocked_stream.side_effect = _fake_stream

        with pytest.raises(siglists_utils.BadRegularExpressionLineError) as exc_info:
            siglists_utils._get_file_content("test-invalid-sig-list")

        msg = exc_info.exconly()
        assert "BadRegularExpressionLineError: Regex error: " in msg
        assert msg.endswith("at line 3")
        assert "test-invalid-sig-list.txt" in msg

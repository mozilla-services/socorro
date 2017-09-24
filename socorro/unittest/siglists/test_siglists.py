# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
from pkg_resources import resource_stream
import pytest

from socorro import siglists
from socorro.unittest.testbase import TestCase


def _fake_stream(pkg, filepath):
    return resource_stream(__name__, filepath)


class TestSigLists(TestCase):
    def test_loading_files(self):
        all_lists = (
            'IRRELEVANT_SIGNATURE_RE',
            'PREFIX_SIGNATURE_RE',
            'SIGNATURE_SENTINELS',
            'SIGNATURES_WITH_LINE_NUMBERS_RE',
        )

        for list_name in all_lists:
            content = getattr(siglists, list_name)
            assert content

            for line in content:
                assert line
                if isinstance(line, basestring):
                    assert not line.startswith('#')

    @mock.patch('socorro.siglists.resource_stream')
    def test_valid_entries(self, mocked_stream):
        mocked_stream.side_effect = _fake_stream

        expected = (
            'fooBarStuff',
            'moz::.*',
            '@0x[0-9a-fA-F]{2,}',
        )
        content = siglists._get_file_content('test-valid-sig-list')
        assert content == expected

    @mock.patch('socorro.siglists.resource_stream')
    def test_invalid_entry(self, mocked_stream):
        mocked_stream.side_effect = _fake_stream

        with pytest.raises(siglists.BadRegularExpressionLineError) as exc_info:
            siglists._get_file_content('test-invalid-sig-list')

        msg = exc_info.exconly()
        assert msg.startswith('BadRegularExpressionLineError: Regex error: ')
        assert msg.endswith('at line 3')
        assert 'test-invalid-sig-list.txt' in msg

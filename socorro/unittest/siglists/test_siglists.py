# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import os
from nose.tools import assert_raises, eq_, ok_

from socorro import siglists
from socorro.unittest.testbase import TestCase


TEST_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


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
            ok_(content, list_name)

            for line in content:
                ok_(line)
                if isinstance(line, basestring):
                    ok_(not line.startswith('#'))

    @mock.patch('socorro.siglists._DIRECTORY', TEST_DIRECTORY)
    def test_valid_entries(self):
        expected = (
            'fooBarStuff',
            'moz::.*',
            '@0x[0-9a-fA-F]{2,}',
        )
        content = siglists._get_file_content('test-valid-sig-list')
        eq_(content, expected)

    @mock.patch('socorro.siglists._DIRECTORY', TEST_DIRECTORY)
    def test_invalid_entry(self):
        with assert_raises(siglists.BadRegularExpressionLineError) as cm:
            siglists._get_file_content('test-invalid-sig-list')

        ok_(cm.exception.message.startswith('Regex error: '))
        ok_(cm.exception.message.endswith('at line 3'))
        ok_('test-invalid-sig-list.txt' in cm.exception.message)

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
import mock
import pytest
import requests_mock

from socorro.lib.ooid import create_new_ooid
from socorro.submitter.breakpad_submitter_utilities import BreakpadPOSTDestination, parse_urls


@pytest.mark.parametrize('data, expected', [
    ('', []),
    ('http://example.com/', ['http://example.com/']),
    (
        'http://example.com/ , http://2.example.com/',
        ['http://example.com/', 'http://2.example.com/']
    ),
])
def test_parse_urls(data, expected):
    assert parse_urls(data) == expected


class TestBreakpadPOSTDestination:
    @requests_mock.mock()
    def test_post(self, req_mock):
        config = DotDict({
            'urls': 'http://example.com/submit,http://2.example.com/submit',

            'logger': mock.MagicMock(),
            'redactor_class': mock.MagicMock(),
        })
        bpd = BreakpadPOSTDestination(config)

        raw_crash = DotDict({
            'Product': 'Firefox'
        })
        dumps = {}
        crash_id = create_new_ooid()

        # Set up the request mock to return what Antenna returns
        response_text = 'CrashID=bp-%s\n' % crash_id
        req_mock.post('http://example.com/submit', text=response_text)
        req_mock.post('http://2.example.com/submit', text=response_text)

        # Run the method in question
        bpd.save_raw_crash_with_file_dumps(raw_crash, dumps, crash_id)

        # Verify what happened with requests.post
        assert req_mock.call_count == 2
        req_history = req_mock.request_history
        assert req_history[0].method == 'POST'
        assert req_history[0].url == 'http://example.com/submit'

        assert req_history[1].method == 'POST'
        assert req_history[1].url == 'http://2.example.com/submit'

        # Generating the paylod involves some random-string bits in poster, so
        # we can't do a string compare. So it's hard to verify the data that
        # got posted was correct. Instead, we check to see if some strings
        # made it and assume that's probably good.
        history_0_text = str(req_history[0].text)
        assert 'Content-Disposition: form-data; name="Product"' in history_0_text
        assert 'Firefox' in history_0_text

        # Assert the same stuff was sent to both urls
        history_1_text = str(req_history[1].text)
        assert history_0_text == history_1_text

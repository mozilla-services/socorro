# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import contextmanager

import requests_mock
import pytest


class FakeCollector:
    """Fakes a collector that the submitter submits to

    :attribute payloads: the list of payloads that was received since this was
        created or the last time ``.clear()`` was called

    """

    def __init__(self):
        self.payloads = []

    def clear(self):
        self.payloads = []

    def handle_post(self, request, context):
        self.payloads.append(request)
        context.status = 200
        # FIXME(willkg): this should return the same crash id that it got--but
        # that requires parsing the payload. :(
        crashid = "xxx"
        return "CrashID=bp-%s" % crashid

    @contextmanager
    def setup_mock(self):
        with requests_mock.mock(real_http=True) as rm:
            rm.post("//antenna:8000/submit", text=self.handle_post)
            rm.post("//antenna_2:8000/submit", text=self.handle_post)
            yield self


@pytest.fixture
def mock_collector():
    """Creates a mock collector that lets you observe posted payloads"""
    with FakeCollector().setup_mock() as fm:
        yield fm

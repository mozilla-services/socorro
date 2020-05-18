# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django import http
from django.utils.encoding import smart_text

from crashstats.crashstats import decorators


class TestCheckDays:
    def test_basics(self, rf):
        @decorators.check_days_parameter([1, 2], 2)
        def view(request, days=None, **kwargs):
            return http.HttpResponse(str(10000 + days))

        request = rf.get("/")
        response = view(request)
        assert smart_text(response.content) == "10002"  # default

        request = rf.get("/", {"days": "1"})
        response = view(request)
        assert smart_text(response.content) == "10001"

        # not a number
        request = rf.get("/", {"days": "xxx"})
        response = view(request)
        assert response.status_code == 400

        # out of range
        request = rf.get("/", {"days": 3})
        response = view(request)
        assert response.status_code == 400

    def test_no_default(self, rf):
        # if no default is passed, it has to be one of list of days

        @decorators.check_days_parameter([1, 2])
        def view(request, days=None, **kwargs):
            return http.HttpResponse(str(10000 + days))

        request = rf.get("/", {"days": 1})
        response = view(request)
        assert smart_text(response.content) == "10001"

        request = rf.get("/")
        response = view(request)
        assert response.status_code == 400

    def test_none_default(self, rf):
        @decorators.check_days_parameter([1, 2], default=None)
        def view(request, days=None, **kwargs):
            return http.HttpResponse(str(days))

        request = rf.get("/")
        response = view(request)
        assert smart_text(response.content) == "None"

    def test_using_possible_days(self, rf):
        @decorators.check_days_parameter([1, 2], 2)
        def view(request, days=None, possible_days=None):
            return http.HttpResponse(str(possible_days))

        request = rf.get("/")
        response = view(request)
        assert smart_text(response.content) == str([1, 2])

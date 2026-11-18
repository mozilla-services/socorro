# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pyquery
import pytest

from crashstats.api.templatetags.jinja_helpers import make_test_input, pluralize


class TestMakeTestInput:
    @pytest.mark.parametrize(
        "value", ["!ping", "ping", "with spaces", '"><script>alert("x")</script>&']
    )
    def test_default_value(self, value):
        parameter = {"name": "submission_type", "type": str, "required": False}
        html = make_test_input(parameter, {"submission_type": value})
        doc = pyquery.PyQuery(html)

        assert doc("input").attr("value") == value
        assert set(doc("input")[0].attrib) == {"type", "name", "value"}
        assert not doc("script")


class TestPluralize:
    def test_basics(self):
        assert pluralize(0) == "s"
        assert pluralize(1) == ""
        assert pluralize(59) == "s"

    def test_overide_s(self):
        assert pluralize(59, "ies") == "ies"

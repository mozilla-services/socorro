# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crashstats.api.templatetags.jinja_helpers import pluralize


class TestPluralize:
    def test_basics(self):
        assert pluralize(0) == "s"
        assert pluralize(1) == ""
        assert pluralize(59) == "s"

    def test_overide_s(self):
        assert pluralize(59, "ies") == "ies"

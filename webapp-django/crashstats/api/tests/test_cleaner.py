# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from unittest import mock

from crashstats.api.cleaner import Cleaner, SmartAllowlistMatcher


class TestCleaner:
    def test_simplest_case(self):
        allowlist = {"hits": ("foo", "bar")}
        data = {
            "hits": [{"foo": 1, "bar": 2, "baz": 3}, {"foo": 4, "bar": 5, "baz": 6}]
        }
        cleaner = Cleaner(allowlist)
        cleaner.start(data)
        expect = {"hits": [{"foo": 1, "bar": 2}, {"foo": 4, "bar": 5}]}
        assert data == expect

    @mock.patch("warnings.warn")
    def test_simplest_case_with_warning(self, p_warn):
        allowlist = {"hits": ("foo", "bar")}
        data = {
            "hits": [{"foo": 1, "bar": 2, "baz": 3}, {"foo": 4, "bar": 5, "baz": 6}]
        }
        cleaner = Cleaner(allowlist, debug=True)
        cleaner.start(data)
        p_warn.assert_called_with("Skipping 'baz'")

    def test_all_dict_data(self):
        allowlist = {Cleaner.ANY: ("foo", "bar")}
        data = {
            "WaterWolf": {"foo": 1, "bar": 2, "baz": 3},
            "NightTrain": {"foo": 7, "bar": 8, "baz": 9},
        }
        cleaner = Cleaner(allowlist)
        cleaner.start(data)
        expect = {"WaterWolf": {"foo": 1, "bar": 2}, "NightTrain": {"foo": 7, "bar": 8}}
        assert data == expect

    def test_simple_list(self):
        allowlist = ("foo", "bar")
        data = [{"foo": 1, "bar": 2, "baz": 3}, {"foo": 7, "bar": 8, "baz": 9}]
        cleaner = Cleaner(allowlist)
        cleaner.start(data)
        expect = [{"foo": 1, "bar": 2}, {"foo": 7, "bar": 8}]
        assert data == expect

    def test_plain_dict(self):
        allowlist = ("foo", "bar")
        data = {"foo": 1, "bar": 2, "baz": 3}
        cleaner = Cleaner(allowlist)
        cleaner.start(data)
        expect = {"foo": 1, "bar": 2}
        assert data == expect

    def test_dict_data_with_lists(self):
        allowlist = {"hits": {Cleaner.ANY: ("foo", "bar")}}
        data = {
            "hits": {
                "WaterWolf": [
                    {"foo": 1, "bar": 2, "baz": 3},
                    {"foo": 4, "bar": 5, "baz": 6},
                ],
                "NightTrain": [
                    {"foo": 7, "bar": 8, "baz": 9},
                    {"foo": 10, "bar": 11, "baz": 12},
                ],
            }
        }
        cleaner = Cleaner(allowlist)
        cleaner.start(data)
        expect = {
            "hits": {
                "WaterWolf": [{"foo": 1, "bar": 2}, {"foo": 4, "bar": 5}],
                "NightTrain": [{"foo": 7, "bar": 8}, {"foo": 10, "bar": 11}],
            }
        }
        assert data == expect

    def test_all_dict_data_deeper(self):
        allowlist = {Cleaner.ANY: {Cleaner.ANY: ("foo", "bar")}}
        data = {
            "WaterWolf": {
                "2012": {"foo": 1, "bar": 2, "baz": 3},
                "2013": {"foo": 4, "bar": 5, "baz": 6},
            },
            "NightTrain": {
                "2012": {"foo": 7, "bar": 8, "baz": 9},
                "2013": {"foo": 10, "bar": 11, "baz": 12},
            },
        }
        cleaner = Cleaner(allowlist)
        cleaner.start(data)
        expect = {
            "WaterWolf": {"2012": {"foo": 1, "bar": 2}, "2013": {"foo": 4, "bar": 5}},
            "NightTrain": {
                "2012": {"foo": 7, "bar": 8},
                "2013": {"foo": 10, "bar": 11},
            },
        }
        assert data == expect


class TestSmartAllowlistMatcher:
    def test_basic_in(self):
        allowlist = ["some", "thing*"]
        matcher = SmartAllowlistMatcher(allowlist)
        assert "some" in matcher
        assert "something" not in matcher
        assert "awesome" not in matcher
        assert "thing" in matcher
        assert "things" in matcher
        assert "nothing" not in matcher

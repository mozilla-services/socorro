# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crashstats.crashstats import forms


class TestForms:
    def setup_method(self):
        self.active_versions = {
            "WaterWolf": [
                {"version": "20.0", "build_type": "Beta"},
                {"version": "21.0a1", "build_type": "Nightly"},
            ],
            "NightTrain": [{"version": "20.0", "build_type": "Beta"}],
            "SeaMonkey": [{"version": "9.5", "build_type": "Beta"}],
        }

        self.current_channels = ("release", "beta", "aurora", "nightly", "esr")

    def test_buginfoform(self):
        def get_new_form(data):
            return forms.BugInfoForm(data)

        form = get_new_form({})
        # missing bug_ids
        assert not form.is_valid()

        form = get_new_form({"bug_ids": "456, not a bug"})
        # invalid bug_ids
        assert not form.is_valid()

        form = get_new_form({"bug_ids": "123 , 345 ,, 100"})
        assert form.is_valid()
        assert form.cleaned_data["bug_ids"] == ["123", "345", "100"]

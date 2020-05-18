# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crashstats.supersearch import forms
from socorro.external.es.super_search_fields import FIELDS


class TestForms:
    def setup_method(self):
        self.products = ["WaterWolf", "NightTrain", "SeaMonkey", "Tinkerbell"]
        self.product_versions = ["20.0", "21.0a1", "20.0", "9.5"]
        self.platforms = ["Windows", "Mac OS X", "Linux"]
        self.all_fields = FIELDS

    def test_search_form(self):
        def get_new_form(data):
            class User:
                def has_perm(self, permission):
                    return {
                        "crashstats.view_pii": False,
                        "crashstats.view_exploitability": False,
                    }.get(permission, False)

            return forms.SearchForm(
                self.all_fields,
                self.products,
                self.product_versions,
                self.platforms,
                User(),
                data,
            )

        form = get_new_form({"product": "WaterWolf"})
        # expect values as lists
        assert not form.is_valid()

        form = get_new_form({"date": "2012-01-16 12:23:34324234"})
        # invalid datetime
        assert not form.is_valid()

        # Test all valid data
        form = get_new_form(
            {
                "signature": ["~sig"],
                "product": ["WaterWolf", "SeaMonkey", "NightTrain"],
                "version": ["20.0"],
                "platform": ["Linux", "Mac OS X"],
                "date": [">2012-01-16 12:23:34", "<=2013-01-16 12:23:34"],
                "reason": ["some reason"],
                "build_id": "<20200101344556",
            }
        )
        assert form.is_valid()

        # Verify admin restricted fields are not accepted
        form = get_new_form({"email": "something", "exploitability": "high"})
        assert form.is_valid()
        assert "email" not in form.fields
        assert "exploitability" not in form.fields

    def test_search_form_with_admin_mode(self):
        def get_new_form(data):
            class User:
                def has_perm(self, permission):
                    return {
                        "crashstats.view_pii": True,
                        "crashstats.view_exploitability": True,
                    }.get(permission, False)

            return forms.SearchForm(
                self.all_fields,
                self.products,
                self.product_versions,
                self.platforms,
                User(),
                data,
            )

        form = get_new_form({"product": "WaterWolf"})
        # expect values as lists
        assert not form.is_valid()

        form = get_new_form({"date": "2012-01-16 12:23:34324234"})
        # invalid datetime
        assert not form.is_valid()

        # Test all valid data
        form = get_new_form(
            {
                "signature": ["~sig"],
                "product": ["WaterWolf", "SeaMonkey", "NightTrain"],
                "version": ["20.0"],
                "platform": ["Linux", "Mac OS X"],
                "date": [">2012-01-16 12:23:34", "<=2013-01-16 12:23:34"],
                "reason": ["some reason"],
                "build_id": "<20200101344556",
                "email": ["^mail.com"],
                "url": ["$http://"],
                "exploitability": ["high", "medium"],
            }
        )
        assert form.is_valid()

        # Verify admin restricted fields are accepted
        assert "email" in form.fields
        assert "url" in form.fields
        assert "exploitability" in form.fields

    def test_get_fields_list(self):
        def get_new_form(data):
            class User:
                def has_perm(self, permission):
                    permissions = {
                        "crashstats.view_pii": False,
                        "crashstats.view_exploitability": False,
                    }
                    return permissions.get(permission, False)

            return forms.SearchForm(
                self.all_fields,
                self.products,
                self.product_versions,
                self.platforms,
                User(),
                data,
            )

        form = get_new_form({})
        assert form.is_valid()

        fields = form.get_fields_list()
        assert "version" in fields

        # Verify there's only one occurence of the version.
        assert fields["version"]["values"].count("20.0") == 1

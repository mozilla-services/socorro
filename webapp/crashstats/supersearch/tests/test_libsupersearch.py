# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from crashstats.supersearch.libsupersearch import convert_permissions


def test_convert_permissions():
    fields = {
        "build": {
            "permissions_needed": [],
        },
        "product": {
            "permissions_needed": ["public"],
        },
        "version": {
            "permissions_needed": ["protected"],
        },
    }

    expected = {
        "build": {
            # No permission -> no required permissions
            "permissions_needed": [],
            "webapp_permissions_needed": [],
        },
        "product": {
            # "public" -> no required permissions
            "permissions_needed": ["public"],
            "webapp_permissions_needed": [],
        },
        "version": {
            # "protected" -> "crashstats.view_pii"
            "permissions_needed": ["protected"],
            "webapp_permissions_needed": ["crashstats.view_pii"],
        },
    }

    assert convert_permissions(fields) == expected

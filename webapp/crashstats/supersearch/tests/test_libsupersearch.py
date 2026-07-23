# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import pytest
from crashstats.supersearch.libsupersearch import (
    convert_permissions,
    get_allowed_fields,
    sanitize_params,
)


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


MINIMAL_SUPERSEARCH_FIELDS_FIXTURE = {
    "signature": {
        "name": "signature",
        "is_exposed": True,
        "webapp_permissions_needed": [],
    },
    "product": {
        "name": "product",
        "is_exposed": True,
        "webapp_permissions_needed": [],
    },
    "user_comments": {
        "name": "user_comments",
        "is_exposed": True,
        "webapp_permissions_needed": ["crashstats.view_pii"],
    },
    "url": {
        "name": "url",
        "is_exposed": True,
        "webapp_permissions_needed": ["crashstats.view_pii"],
    },
    "_unexposed": {
        "name": "_unexposed",
        "is_exposed": False,
        "webapp_permissions_needed": [],
    },
}


@pytest.mark.parametrize(
    "user_type, included, excluded",
    [
        # No user passed -> public fields only
        (
            "none",
            {"signature", "product"},
            {"user_comments", "url", "_unexposed"},
        ),
        # Authorized user (view_pii via the Hackers group) -> public + protected fields
        (
            "authorized",
            {"signature", "product", "user_comments", "url"},
            {"_unexposed"},
        ),
        # Authenticated user without view_pii -> public fields only
        (
            "unauthorized",
            {"signature", "product"},
            {"user_comments", "url", "_unexposed"},
        ),
    ],
)
def test_get_allowed_fields(
    db, user_helper, monkeypatch, user_type, included, excluded
):
    monkeypatch.setattr(
        "crashstats.supersearch.libsupersearch.get_supersearch_fields",
        lambda: MINIMAL_SUPERSEARCH_FIELDS_FIXTURE,
    )

    if user_type == "none":
        user = None
    elif user_type == "authorized":
        user = user_helper.create_protected_user()
    else:
        user = user_helper.create_user()

    result = set(get_allowed_fields(user=user))

    assert included.issubset(result)
    assert excluded.isdisjoint(result)


@pytest.mark.parametrize(
    "param_name, input_values, allowed, expected",
    [
        # _sort is the only param with a possible prefix
        # Without - prefix on disallowed field is stripped
        ("_sort", ["signature", "user_comments"], {"signature"}, ["signature"]),
        # With - prefix on disallowed field is stripped
        ("_sort", ["-signature", "-user_comments"], {"signature"}, ["-signature"]),
        # With prefix on allowed field remains
        ("_sort", ["-signature"], {"signature"}, ["-signature"]),
        # Both with and without prefix on allowed field remains
        (
            "_sort",
            ["signature", "-signature"],
            {"signature"},
            ["signature", "-signature"],
        ),
        # All disallowed fields with and without prefix -> empty list
        ("_sort", ["user_comments", "-user_comments"], {"signature"}, []),
        # Empty input -> empty output
        ("_sort", [], {"signature"}, []),
        # _facets / _columns / _aggs.* / _histogram.* all work identically.
        ("_facets", ["signature", "user_comments"], {"signature"}, ["signature"]),
        ("_columns", ["signature", "url"], {"signature"}, ["signature"]),
        (
            "_aggs.product",
            ["version", "user_comments"],
            {"product", "version"},
            ["version"],
        ),
        ("_histogram.date", ["product", "url"], {"date", "product"}, ["product"]),
        # `-` prefix is not a sort directive on non-_sort params, so the value is rejected.
        ("_columns", ["-signature"], {"signature"}, []),
    ],
)
def test_sanitize_params_list_of_fields_values(
    param_name, input_values, allowed, expected
):
    """Params dict with list-of-fields have their values sanitized appropriately."""
    params = {param_name: input_values}
    sanitize_params(
        params,
        allowed_fields=allowed,
        all_fields={},
        list_of_fields_params=(param_name,),
    )
    assert params[param_name] == expected


def test_sanitize_params_handles_missing_keys_for_list_of_fields_values():
    """Empty params dict results in empty default list-of-fields values."""
    params = {}
    sanitize_params(
        params,
        allowed_fields={"signature"},
        all_fields={},
        list_of_fields_params=("_sort", "_facets", "_columns"),
    )
    assert params == {"_sort": [], "_facets": [], "_columns": []}


def test_sanitize_params_drops_disallowed_filters_and_agg_names():
    """
    Params dict with direct filters, _aggs, _histograms parameter names containing
    disallowed fields are sanitized.
    """
    params = {
        "url": ["example.com"],  # filter on a disallowed field
        "signature": ["abc"],  # filter on an allowed field
        "_aggs.url": ["signature"],  # aggregation on a disallowed field
        "_aggs.signature": ["signature"],  # aggregation on an allowed field
        "_histogram.url": ["signature"],  # histogram on a disallowed field
        "_histogram.signature": ["signature"],  # histogram on an allowed field
        "_results_number": 10,  # meta param, not a field
    }
    sanitize_params(
        params,
        allowed_fields={"signature"},
        all_fields={"url", "signature"},
        list_of_fields_params=(),
    )
    assert "url" not in params
    assert params["signature"] == ["abc"]
    assert "_aggs.url" not in params
    assert "_aggs.signature" in params
    assert "_histogram.url" not in params
    assert "_histogram.signature" in params
    assert params["_results_number"] == 10


def test_sanitize_params_agg_name_checks_all_dotted_segments():
    """Params dict with subaggregations on disallowed fields are sanitized."""
    params = {
        "_aggs.product.version": ["signature"],  # all segments allowed
        "_aggs.product.url": ["signature"],  # a later segment is disallowed
    }
    sanitize_params(
        params,
        allowed_fields={"product", "version", "signature"},
        all_fields={"product", "version", "url", "signature"},
        list_of_fields_params=(),
    )
    assert "_aggs.product.version" in params
    assert "_aggs.product.url" not in params

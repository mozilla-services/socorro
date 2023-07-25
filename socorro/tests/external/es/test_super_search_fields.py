# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import json

import pytest

from socorro.external.es.super_search_fields import (
    add_doc_values,
    build_mapping,
    FIELDS,
    is_doc_values_friendly,
    get_fields_by_item,
)


def get_fields():
    return copy.deepcopy(FIELDS)


class Test_get_fields_by_item:
    @pytest.mark.parametrize(
        "fields",
        [
            # No fields
            {},
            # No storage_mapping
            {"key": {"in_database_name": "key"}},
            # Wrong or missing analyzer
            {"key": {"in_database_name": "key", "storage_mapping": {"type": "string"}}},
            {
                "key": {
                    "in_database_name": "key",
                    "storage_mapping": {
                        "analyzer": "semicolon_keywords",
                        "type": "string",
                    },
                }
            },
        ],
    )
    def test_no_match(self, fields):
        assert get_fields_by_item(fields, "analyzer", "keyword") == []

    def test_match(self):
        fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }
        assert get_fields_by_item(fields, "analyzer", "keyword") == [fields["key"]]

    def test_match_by_type(self):
        fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }
        assert get_fields_by_item(fields, "type", "string") == [fields["key"]]

    def test_caching(self):
        # Verify caching works
        fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }
        result = get_fields_by_item(fields, "analyzer", "keyword")
        second_result = get_fields_by_item(fields, "analyzer", "keyword")
        assert id(result) == id(second_result)

        # This is the same data as fields, but a different dict, so it has a
        # different id and we won't get the cached version
        second_fields = {
            "key": {
                "in_database_name": "key",
                "storage_mapping": {"analyzer": "keyword", "type": "string"},
            }
        }
        third_result = get_fields_by_item(second_fields, "analyzer", "keyword")
        assert id(result) != id(third_result)


class Test_build_mapping:
    """Test build_mapping with an elasticsearch database containing fake data"""

    def test_get_mapping(self, es_helper):
        doctype = es_helper.get_doctype()
        mapping = build_mapping(doctype=doctype, fields=get_fields())

        assert doctype in mapping
        properties = mapping[doctype]["properties"]

        print(json.dumps(properties, indent=4, sort_keys=True))
        assert "raw_crash" not in properties
        assert "processed_crash" in properties

        processed_crash = properties["processed_crash"]["properties"]

        # Check in_database_name is used.
        assert "os_name" in processed_crash
        assert "platform" not in processed_crash

        # Those fields have a `storage_mapping`.
        assert processed_crash["release_channel"] == {
            "analyzer": "keyword",
            "type": "string",
        }

        # Test nested objects.
        assert processed_crash["json_dump"]["properties"]["system_info"]["properties"][
            "cpu_count"
        ] == {
            "type": "short",
            "doc_values": True,
        }


@pytest.mark.parametrize("name, properties", FIELDS.items())
def test_validate_super_search_fields(name, properties):
    """Validates the contents of socorro.external.es.super_search_fields.FIELDS"""

    # FIXME(willkg): When we start doing schema stuff in Python, we should switch this
    # to a schema validation.

    required_property_keys = {
        "data_validation_type",
        "description",
        "form_field_choices",
        "has_full_version",
        "in_database_name",
        "is_exposed",
        "is_returned",
        "name",
        "namespace",
        "permissions_needed",
        "query_type",
        "storage_mapping",
    }

    all_property_keys = required_property_keys | {
        "destination_keys",
        "search_key",
        "source_key",
    }

    # Assert it has all the required keys
    assert required_property_keys - set(properties.keys()) == set()

    # Assert it doesn't have bad keys
    assert set(properties.keys()) - all_property_keys == set()

    # Assert boolean fields have boolean values
    for key in ["has_full_version", "is_exposed", "is_returned"]:
        assert properties[key] in (True, False)

    # Assert data_validation_type has a valid value
    assert properties["data_validation_type"] in (
        "bool",
        "datetime",
        "enum",
        "int",
        "float",
        "str",
    )

    # Assert query_type has a valid value
    assert properties["query_type"] in (
        "bool",
        "date",
        "enum",
        "flag",
        "integer",
        "float",
        "string",
    )

    # The name in the mapping should be the same as the name in properties
    assert properties["name"] == name

    # If is_exposed and is_returned are both False, then we should remove this field
    assert properties["is_exposed"] or properties["is_returned"]

    # If stroage_mapping is None, then is_exposed must be False
    if properties["storage_mapping"] is None:
        assert properties["is_exposed"] is False

    # We occasionally do multi-step migrations that change data types where we need to
    # accumulate data in a new field and specify it in a way that otherwise breaks
    # super_search_fields validation.
    #
    # If the field name has "_future" at the end, it's one of these cases, so ignore
    # these checks.
    #
    # If the field has "json_dump" in the source_key, then it's another special case
    # where we're moving it from a nested location in the processed_crash to a top-level
    # location.
    #
    # If the field has "collector_metadata" in the source key, then we want to pull a
    # value from a nested place--this isn't a migration kind of thing.
    if (
        not properties["name"].endswith("_future")
        and "json_dump" not in properties.get("source_key", "")
        and "collector_metadata" not in properties.get("source_key", "")
    ):
        if properties["is_exposed"] is False:
            assert properties["storage_mapping"] is None

        # Make sure the source_key is processed_crash + name
        if properties.get("source_key"):
            assert properties["source_key"] == f"processed_crash.{properties['name']}"

        if properties.get("destination_keys"):
            for key in properties["destination_keys"]:
                possible_keys = [
                    # Old keys we're probably migrating from
                    f"raw_crash.{properties['in_database_name']}",
                    f"processed_crash.{properties['in_database_name']}",
                    # New key we're probably migrating to
                    f"processed_crash.{properties['name']}",
                ]
                assert key in possible_keys


@pytest.mark.parametrize(
    "value, expected",
    [
        # No type -> False
        ({}, False),
        # object -> False
        ({"type": "object"}, False),
        # Analyzed string -> False
        ({"type": "string"}, False),
        ({"type": "string", "analyzer": "keyword"}, False),
        # Unanalyzed string -> True
        ({"type": "string", "index": "not_analyzed"}, True),
        # Anything else -> True
        ({"type": "long"}, True),
    ],
)
def test_is_doc_values_friendly(value, expected):
    assert is_doc_values_friendly(value) == expected


def test_add_doc_values():
    storage_mapping = {"type": "short"}
    add_doc_values(storage_mapping)
    assert storage_mapping == {"type": "short", "doc_values": True}

    storage_mapping = {
        "fields": {
            "AsyncShutdownTimeout": {
                "analyzer": "standard",
                "index": "analyzed",
                "type": "string",
            },
            "full": {"index": "not_analyzed", "type": "string"},
        },
        "type": "multi_field",
    }
    add_doc_values(storage_mapping)
    assert storage_mapping == {
        "fields": {
            "AsyncShutdownTimeout": {
                "analyzer": "standard",
                "index": "analyzed",
                "type": "string",
            },
            "full": {"index": "not_analyzed", "type": "string", "doc_values": True},
        },
        "type": "multi_field",
    }

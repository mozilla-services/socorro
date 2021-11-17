# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
from datetime import timedelta

import pytest

from socorro.lib import BadArgumentError
from socorro.external.es.super_search_fields import (
    add_doc_values,
    build_mapping,
    FIELDS,
    is_doc_values_friendly,
    get_fields_by_item,
    SuperSearchFieldsModel,
)
from socorro.lib import datetimeutil
from socorro.unittest.external.es.base import ElasticsearchTestCase


# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


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


class Test_build_mapping(ElasticsearchTestCase):
    """Test build_mapping with an elasticsearch database containing fake data"""

    def setup_method(self):
        super().setup_method()

        config = self.get_base_config(cls=SuperSearchFieldsModel)
        self.api = SuperSearchFieldsModel(config=config)
        self.api.get_fields = lambda: copy.deepcopy(FIELDS)

    def test_get_mapping(self):
        doctype = self.es_context.get_doctype()
        mapping = build_mapping(doctype=doctype, fields=self.api.get_fields())

        assert doctype in mapping
        properties = mapping[doctype]["properties"]

        assert "processed_crash" in properties
        assert "raw_crash" in properties

        processed_crash = properties["processed_crash"]["properties"]

        # Check in_database_name is used.
        assert "os_name" in processed_crash
        assert "platform" not in processed_crash

        # Those fields have no `storage_mapping`.
        assert "fake_field" not in properties["raw_crash"]["properties"]

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


class TestIntegrationSuperSearchFields(ElasticsearchTestCase):
    """Test SuperSearchFields with an elasticsearch database containing fake data"""

    def setup_method(self):
        super().setup_method()

        config = self.get_base_config(cls=SuperSearchFieldsModel)
        self.api = SuperSearchFieldsModel(config=config)
        self.api.get_fields = lambda: copy.deepcopy(FIELDS)

    def test_get_fields(self):
        results = self.api.get_fields()
        assert results == FIELDS

    def test_get_missing_fields(self):
        config = self.get_base_config(cls=SuperSearchFieldsModel)
        api = SuperSearchFieldsModel(config=config)

        fake_mapping_1 = {
            config.elasticsearch_doctype: {
                "properties": {
                    # Add a bunch of unknown fields.
                    "field_z": {"type": "string"},
                    "namespace1": {
                        "type": "object",
                        "properties": {
                            "field_a": {"type": "string"},
                            "field_b": {"type": "long"},
                        },
                    },
                    "namespace2": {
                        "type": "object",
                        "properties": {
                            "subspace1": {
                                "type": "object",
                                "properties": {"field_b": {"type": "long"}},
                            }
                        },
                    },
                    # Add a few known fields that should not appear.
                    "processed_crash": {
                        "type": "object",
                        "properties": {
                            "signature": {"type": "string"},
                            "product": {"type": "string"},
                        },
                    },
                }
            }
        }

        fake_mapping_2 = {
            config.elasticsearch_doctype: {
                "properties": {
                    "namespace1": {
                        "type": "object",
                        "properties": {
                            "subspace1": {
                                "type": "object",
                                "properties": {"field_d": {"type": "long"}},
                            }
                        },
                    }
                }
            }
        }

        # Refresh and then delete existing indices so we can rebuild the mappings
        # in order to diff them
        self.es_context.refresh()
        self.es_context.health_check()
        for index_name in self.es_context.get_indices():
            self.es_context.delete_index(index_name)

        # Refresh ES to wait for indices to delete
        self.es_context.refresh()
        self.es_context.health_check()

        now = datetimeutil.utc_now()
        template = api.context.get_index_template()

        # Create an index for now
        index_name = now.strftime(template)
        mapping = fake_mapping_1
        api.context.create_index(index_name, mappings=mapping)

        # Create an index for 7 days ago
        index_name = (now - timedelta(days=7)).strftime(template)
        mapping = fake_mapping_2
        api.context.create_index(index_name, mappings=mapping)

        # Refresh ES to wait for indices to be created
        self.es_context.refresh()
        self.es_context.health_check()

        api = SuperSearchFieldsModel(config=config)
        missing_fields = api.get_missing_fields()
        expected = [
            "field_z",
            "namespace1.field_a",
            "namespace1.field_b",
            "namespace1.subspace1.field_d",
            "namespace2.subspace1.field_b",
        ]

        assert missing_fields["hits"] == expected
        assert missing_fields["total"] == 5

    def test_test_mapping(self):
        """Much test. So meta. Wow test_test_."""
        # First test a valid mapping.
        doctype = self.api.context.get_doctype()
        mapping = build_mapping(doctype=doctype)
        assert self.api.test_mapping(mapping) is None

        # Insert an invalid storage mapping.
        fields = {
            "fake_field": {
                "name": "fake_field",
                "namespace": "raw_crash",
                "in_database_name": "fake_field",
                "storage_mapping": {"type": "unkwown"},
            }
        }
        mapping = build_mapping(doctype=doctype, fields=fields)
        with pytest.raises(BadArgumentError):
            self.api.test_mapping(mapping)

        # Test with a correct mapping, but changes the storage (long) for a field
        # that's indexed as a string so test_mapping throws an error because those
        # are incompatible types
        self.index_crash(
            {"date_processed": datetimeutil.utc_now(), "product": "WaterWolf"}
        )
        self.es_context.refresh()
        fields = {
            "product": {
                "name": "product",
                "namespace": "processed_crash",
                "in_database_name": "product",
                "storage_mapping": {"type": "long"},
            }
        }
        mapping = build_mapping(doctype=doctype, fields=fields)
        with pytest.raises(BadArgumentError):
            self.api.test_mapping(mapping)


def get_fields():
    return FIELDS.items()


@pytest.mark.parametrize("name, properties", get_fields())
def test_validate_super_search_fields(name, properties):
    """Validates the contents of socorro.external.es.super_search_fields.FIELDS"""

    # FIXME(willkg): When we start doing schema stuff in Python, we should switch this
    # to a schema validation.

    property_keys = [
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
    ]

    # Assert it has all the keys
    assert sorted(properties.keys()) == sorted(property_keys)

    # Assert boolean fields have boolean values
    for key in ["has_full_version", "is_exposed", "is_returned"]:
        assert properties[key] in (True, False)

    # Assert data_validation_type has a valid value
    assert properties["data_validation_type"] in (
        "bool",
        "datetime",
        "enum",
        "int",
        "str",
    )

    # Assert query_type has a valid value
    assert properties["query_type"] in (
        "bool",
        "date",
        "enum",
        "flag",
        "number",
        "string",
    )

    # The name in the mapping should be the same as the name in properties
    assert properties["name"] == name

    # If stroage_mapping is None, then is_exposed must be False
    if properties["storage_mapping"] is None:
        assert properties["is_exposed"] is False

    if properties["is_exposed"] is False:
        assert properties["storage_mapping"] is None

    # If is_exposed and is_returned are both False, then we should remove this field
    assert properties["is_exposed"] or properties["is_returned"]


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
    data = {"type": "short"}
    add_doc_values(data)
    assert data == {"type": "short", "doc_values": True}

    data = {
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
    add_doc_values(data)
    assert data == {
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

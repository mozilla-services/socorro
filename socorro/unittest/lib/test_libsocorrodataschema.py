# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import jsonschema
import pytest

from socorro.lib.libsocorrodataschema import (
    FlattenKeys,
    InvalidDocumentError,
    InvalidSchemaError,
    permissions_transform_function,
    resolve_references,
    SocorroDataReducer,
    transform_schema,
)
from socorro.schemas import get_file_content


@pytest.mark.parametrize(
    "schema, expected",
    [
        ({}, {}),
        # Schemas with no references are returned as is
        (
            {"properties": {"color": {"type": "string"}}, "type": "object"},
            {"properties": {"color": {"type": "string"}}, "type": "object"},
        ),
        (
            {
                "properties": {
                    "color": {
                        "properties": {
                            "name": {"type": "string"},
                            "hex": {"type": "string"},
                        },
                        "type": "object",
                    },
                },
                "type": "object",
            },
            {
                "properties": {
                    "color": {
                        "properties": {
                            "name": {"type": "string"},
                            "hex": {"type": "string"},
                        },
                        "type": "object",
                    },
                },
                "type": "object",
            },
        ),
        (
            {"items": {"type": "string"}, "type": "array"},
            {"items": {"type": "string"}, "type": "array"},
        ),
        # Expand references in objects
        (
            {
                "definitions": {
                    "color_name": {
                        "type": "string",
                        "description": "color name",
                    },
                    "color": {
                        # Note: This gets stomped on
                        "description": "ignored",
                        "properties": {
                            "name": {
                                "$ref": "#/definitions/color_name",
                                "permissions": ["public"],
                            },
                            "cost": {
                                "permissions": ["protected"],
                                "type": "integer",
                            },
                        },
                        "permissions": ["ignored"],
                        "type": "object",
                    },
                },
                "properties": {
                    "color": {
                        "description": "the color used here",
                        "$ref": "#/definitions/color",
                        "permissions": ["protected"],
                    },
                },
                "type": "object",
            },
            {
                "properties": {
                    "color": {
                        "description": "the color used here",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "color name",
                                "permissions": ["public"],
                            },
                            "cost": {
                                "type": "integer",
                                "permissions": ["protected"],
                            },
                        },
                        "permissions": ["protected"],
                        "type": "object",
                    },
                },
                "type": "object",
            },
        ),
        # Expand references in arrays
        (
            {
                "definitions": {
                    "color": {
                        "description": "ignored",
                        "type": "string",
                        "permissions": ["ignored"],
                    },
                },
                "properties": {
                    "colors": {
                        "description": "list of colors",
                        "items": {
                            "description": "a single color",
                            "$ref": "#/definitions/color",
                            "permissions": ["public"],
                        },
                        "permissions": ["public"],
                        "type": "array",
                    },
                },
                "type": "object",
            },
            {
                "properties": {
                    "colors": {
                        "description": "list of colors",
                        "items": {
                            "description": "a single color",
                            "permissions": ["public"],
                            "type": "string",
                        },
                        "permissions": ["public"],
                        "type": "array",
                    },
                },
                "type": "object",
            },
        ),
    ],
)
def test_resolve_references(schema, expected):
    original_schema = copy.deepcopy(schema)
    assert resolve_references(schema) == expected

    # resolve_references should never modify the original schema argument
    assert original_schema == schema


class TestSocorroDataReducer:
    def validate_schema(self, schema):
        socorro_data_schema = get_file_content("socorro-data-1-0-0.schema.yaml")
        return jsonschema.validate(instance=schema, schema=socorro_data_schema)

    def schema_reduce(self, schema, document):
        reducer = SocorroDataReducer(schema=schema)
        return reducer.traverse(document=document)

    def test_multiple_types_and_null(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "years": {"type": ["integer", "null"]},
            },
        }
        self.validate_schema(schema)

        document = {"years": 10}
        assert self.schema_reduce(schema, document) == document

        document = {"years": None}
        assert self.schema_reduce(schema, document) == document

        document = {}
        assert self.schema_reduce(schema, document) == document

    @pytest.mark.parametrize("number", [-10, 10])
    def test_integer(self, number):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "years": {"type": "integer"},
            },
        }
        self.validate_schema(schema)

        document = {"years": number}
        assert self.schema_reduce(schema, document) == document

    def test_invalid_integer(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "years": {"type": "integer"},
            },
        }
        self.validate_schema(schema)

        document = {"years": "10"}
        msg_pattern = r"invalid: .years: type string not in \['integer'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert self.schema_reduce(schema, document) == document

    @pytest.mark.parametrize("number", [-10.5, 10.5])
    def test_number(self, number):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "length": {"type": "number"},
            },
        }
        self.validate_schema(schema)

        document = {"length": number}
        assert self.schema_reduce(schema, document) == document

    def test_invalid_number(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "years": {"type": "number"},
            },
        }
        self.validate_schema(schema)

        document = {"years": "10"}
        msg_pattern = r"invalid: .years: type string not in \['number'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert self.schema_reduce(schema, document) == document

    def test_string(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        self.validate_schema(schema)

        document = {"name": "Joe"}
        assert self.schema_reduce(schema, document) == document

    def test_object_properties(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "favorites": {
                            "type": "object",
                            "properties": {
                                "color": {"type": "string"},
                                "ice_cream": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }
        self.validate_schema(schema)

        document = {
            "person": {
                "name": "Janet",
                "favorites": {
                    "color": "blue",
                    "ice_cream": "chocolate",
                    "hobby": "napping",
                },
            }
        }
        expected_document = {
            "person": {
                "name": "Janet",
                "favorites": {
                    "color": "blue",
                    "ice_cream": "chocolate",
                },
            }
        }
        assert self.schema_reduce(schema, document) == expected_document

    def test_object_pattern_properties(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "registers": {
                    "type": "object",
                    "pattern_properties": {
                        # Only register names that start with "r"
                        r"^r.*$": {"type": "string"},
                    },
                },
            },
        }
        self.validate_schema(schema)

        document = {
            "registers": {
                "r10": "0x00007ffbd6a20000",
                "r8": "0x000000b95ebfdd54",
                "rsi": "0x000000000000002d",
                "rsp": "0x000000b95ebfdaf0",
                # This one doesn't start with "r"
                "pc": "0x000000b95ebfdaf0",
            },
        }
        expected_document = {
            "registers": {
                "r10": "0x00007ffbd6a20000",
                "r8": "0x000000b95ebfdd54",
                "rsi": "0x000000000000002d",
                "rsp": "0x000000b95ebfdaf0",
            },
        }
        assert self.schema_reduce(schema, document) == expected_document

    def test_object_properties_and_pattern_properties(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "registers": {
                    "type": "object",
                    "properties": {
                        "pc": {"type": "string"},
                    },
                    "pattern_properties": {
                        # Only register names that start with "r"
                        r"^r.*$": {"type": "string"},
                    },
                },
            },
        }
        self.validate_schema(schema)

        document = {
            "registers": {
                "r10": "0x00007ffbd6a20000",
                "r8": "0x000000b95ebfdd54",
                "rsi": "0x000000000000002d",
                "rsp": "0x000000b95ebfdaf0",
                # This one doesn't start with "r", but it's in properties
                "pc": "0x000000b95ebfdaf0",
                # This one doesn't start with "r" and isn't in properties
                "fc": "0x000000b95ebfdaf0",
            },
        }
        expected_document = {
            "registers": {
                "r10": "0x00007ffbd6a20000",
                "r8": "0x000000b95ebfdd54",
                "rsi": "0x000000000000002d",
                "rsp": "0x000000b95ebfdaf0",
                "pc": "0x000000b95ebfdaf0",
            },
        }
        assert self.schema_reduce(schema, document) == expected_document

    def test_array(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            },
        }
        self.validate_schema(schema)

        document = {"numbers": [1, 5, 10]}
        assert self.schema_reduce(schema, document) == document

    def test_array_invalid(self):
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            },
        }
        self.validate_schema(schema)

        document = {"numbers": [5, "Janice", 10]}
        msg_pattern = r"invalid: .numbers.\[1\]: type string not in \['integer'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert self.schema_reduce(schema, document) == document

    def test_array_reference(self):
        # NOTE(willkg): the SocorroDataReducer resolves references before reducing, so
        # this tests resolve_references, too
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "definitions": {
                "some_number": {"type": "integer"},
            },
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/some_number"},
                }
            },
        }
        self.validate_schema(schema)

        document = {"numbers": [1, 5, 10]}
        assert self.schema_reduce(schema, document) == document

    def test_references(self):
        """Verify references are traversed."""
        # NOTE(willkg): the SocorroDataReducer resolves references before reducing, so
        # this tests resolve_references, too
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "definitions": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": ["string", "null"],
                        }
                    },
                }
            },
            "properties": {
                "company": {
                    "type": "object",
                    "properties": {
                        "employees": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/person"},
                        },
                    },
                },
            },
        }
        self.validate_schema(schema)

        document = {
            "company": {
                "employees": [
                    {"name": "Fred", "desk": "front"},
                    {"name": "Jim", "favorite_color": "red"},
                ],
            }
        }
        expected_document = {
            "company": {
                "employees": [
                    {"name": "Fred"},
                    {"name": "Jim"},
                ],
            }
        }
        assert self.schema_reduce(schema, document) == expected_document

    def test_invalid_ref(self):
        """Reducer only support json pointers to things in the schema"""
        # NOTE(willkg): the SocorroDataReducer resolves references before reducing, so
        # this tests resolve_references, too
        schema = {
            "$schema": "moz://mozilla.org/schemas/socorro/socorro-data/1-0-0",
            "type": "object",
            "definitions": {},
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"$ref": "http://example.com/schema"},
                }
            },
        }
        self.validate_schema(schema)

        document = {"numbers": [1, 5, 10]}
        with pytest.raises(InvalidSchemaError):
            assert self.schema_reduce(schema, document) == document


@pytest.mark.parametrize(
    "schema, keys",
    [
        # Object traversal with properties
        (
            {
                "type": "object",
                "properties": {
                    "key1": {
                        "type": "string",
                    },
                    "key2": {
                        "type": "integer",
                    },
                },
            },
            ["key1", "key2"],
        ),
        # Object traversal with pattern_properties
        (
            {
                "type": "object",
                "pattern_properties": {
                    r"^r.+$": {
                        "type": "string",
                    },
                    r"^c.+$": {
                        "type": "string",
                    },
                },
            },
            ["(re:^r.+$)", "(re:^c.+$)"],
        ),
        # Array traversal with items as non-list
        (
            {
                "type": "object",
                "properties": {
                    "colors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            ["colors.[]"],
        ),
        # Array traversal with items as list indicating records
        (
            {
                "type": "object",
                "properties": {
                    "person": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
            },
            ["person.[]"],
        ),
        # Expands references
        (
            {
                "definitions": {
                    "color": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "hex": {"type": "string"},
                        },
                    },
                },
                "type": "object",
                "properties": {
                    "colors": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/color"},
                    },
                },
            },
            ["colors.[]", "colors.[].name", "colors.[].hex"],
        ),
        # Expands references with complex types
        (
            {
                "definitions": {
                    "color": {
                        "type": ["object", "null"],
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "hex": {"type": "string"},
                        },
                    },
                },
                "type": "object",
                "properties": {
                    "colors": {
                        "type": ["array", "null"],
                        "items": {
                            "$ref": "#/definitions/color",
                            "type": ["object", "null"],
                        },
                    },
                },
            },
            ["colors.[]", "colors.[].name", "colors.[].hex"],
        ),
    ],
)
def test_transform_schema(schema, keys):
    flattener = FlattenKeys()
    transform_schema(schema=schema, transform_function=flattener.flatten)
    assert flattener.keys == keys


def test_permissions_transform_function():
    schema = {
        "definitions": {
            "color": {
                "type": "object",
                "properties": {
                    "name": {
                        "description": "color name",
                        "type": ["string", "null"],
                        "permissions": ["public"],
                    },
                    "hex": {
                        "description": "RGB hex of color",
                        "type": "string",
                        "permissions": ["public"],
                    },
                    "cost": {
                        "description": "cost of the paint color",
                        "type": ["number", "null"],
                        "permissions": ["protected"],
                    },
                },
                # These are overridden by the referer
                "permissions": ["protected"],
                "description": "overridden",
            },
        },
        "type": "object",
        "properties": {
            "colors": {
                "description": "list of colors",
                "type": ["array", "null"],
                "items": {
                    "description": "a color",
                    "$ref": "#/definitions/color",
                    "type": "object",
                    "permissions": ["public"],
                },
                "permissions": ["public"],
            },
        },
    }

    # Verify our schema is valid socorro-data schema
    socorro_data_schema = get_file_content("socorro-data-1-0-0.schema.yaml")
    jsonschema.validate(instance=schema, schema=socorro_data_schema)

    # Create a public-only transform
    public_only = permissions_transform_function(permissions_have=["public"])

    # Transform the schema using the public-only transform
    public_schema = transform_schema(schema=schema, transform_function=public_only)

    # Assert the new schema is correct and has no protected bits in it
    assert public_schema == {
        "properties": {
            "colors": {
                "description": "list of colors",
                "items": {
                    "description": "a color",
                    "properties": {
                        "hex": {
                            "description": "RGB hex of color",
                            "permissions": ["public"],
                            "type": "string",
                        },
                        "name": {
                            "description": "color name",
                            "permissions": ["public"],
                            "type": ["string", "null"],
                        },
                    },
                    "type": "object",
                    "permissions": ["public"],
                },
                "permissions": ["public"],
                "type": ["array", "null"],
            },
        },
        "type": "object",
    }

    # Create a public/protected transform
    all_permissions = permissions_transform_function(
        permissions_have=["public", "protected"]
    )

    # Transform the schema using the public-only transform
    all_schema = transform_schema(schema=schema, transform_function=all_permissions)

    # Assert the new schema is correct and has no protected bits in it
    assert all_schema == {
        "properties": {
            "colors": {
                "description": "list of colors",
                "items": {
                    "description": "a color",
                    "properties": {
                        "hex": {
                            "description": "RGB hex of color",
                            "permissions": ["public"],
                            "type": "string",
                        },
                        "name": {
                            "description": "color name",
                            "permissions": ["public"],
                            "type": ["string", "null"],
                        },
                        "cost": {
                            "description": "cost of the paint color",
                            "type": ["number", "null"],
                            "permissions": ["protected"],
                        },
                    },
                    "type": "object",
                    "permissions": ["public"],
                },
                "permissions": ["public"],
                "type": ["array", "null"],
            },
        },
        "type": "object",
    }

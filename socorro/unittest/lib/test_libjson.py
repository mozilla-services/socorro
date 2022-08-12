# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import jsonschema
import pytest

from socorro.lib.libjson import (
    InvalidDocumentError,
    InvalidSchemaError,
    Reducer,
    permissions_predicate,
    schema_reduce,
    traverse_schema,
)


class Test_schema_reduce:
    def test_multiple_types_and_null(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": ["integer", "null"]},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"years": 10}
        assert schema_reduce(schema, document) == document

        document = {"years": None}
        assert schema_reduce(schema, document) == document

        document = {}
        assert schema_reduce(schema, document) == document

    @pytest.mark.parametrize("number", [-10, 10])
    def test_integer(self, number):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": "integer"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"years": number}
        assert schema_reduce(schema, document) == document

    def test_invalid_integer(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": "integer"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"years": "10"}
        msg_pattern = r"invalid: .years: type not in \['integer'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert schema_reduce(schema, document) == document

    @pytest.mark.parametrize("number", [-10.5, 10.5])
    def test_number(self, number):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "length": {"type": "number"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"length": number}
        assert schema_reduce(schema, document) == document

    def test_invalid_number(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": "number"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"years": "10"}
        msg_pattern = r"invalid: .years: type not in \['number'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert schema_reduce(schema, document) == document

    def test_string(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"name": "Joe"}
        assert schema_reduce(schema, document) == document

    def test_object_properties(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
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
        jsonschema.Draft4Validator.check_schema(schema)

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
        assert schema_reduce(schema, document) == expected_document

    def test_object_properties_required(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "number"},
                    },
                    "required": ["name", "age"],
                },
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {
            "person": {
                "name": "Dennis",
            },
        }
        with pytest.raises(
            InvalidDocumentError, match=r"invalid: .person.age: required.*"
        ):
            schema_reduce(schema, document)

    def test_object_pattern_properties(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "registers": {
                    "type": "object",
                    "patternProperties": {
                        "^r.*$": {"type": "string"},
                    },
                },
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {
            "registers": {
                "r10": "0x00007ffbd6a20000",
                "r8": "0x000000b95ebfdd54",
                "rsi": "0x000000000000002d",
                "rsp": "0x000000b95ebfdaf0",
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
        assert schema_reduce(schema, document) == expected_document

    def test_object_properties_and_pattern_properties(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "registers": {
                    "type": "object",
                    "properties": {
                        "pc": {"type": "string"},
                    },
                    "patternProperties": {
                        "^r.*$": {"type": "string"},
                    },
                },
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {
            "registers": {
                "r10": "0x00007ffbd6a20000",
                "r8": "0x000000b95ebfdd54",
                "rsi": "0x000000000000002d",
                "rsp": "0x000000b95ebfdaf0",
                "pc": "0x000000b95ebfdaf0",
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
        assert schema_reduce(schema, document) == expected_document

    def test_array(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"numbers": [1, 5, 10]}
        assert schema_reduce(schema, document) == document

    def test_array_invalid(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"numbers": [5, "Janice", 10]}
        msg_pattern = r"invalid: .numbers.\[1\]: type not in \['integer'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert schema_reduce(schema, document) == document

    def test_array_reference(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
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
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"numbers": [1, 5, 10]}
        assert schema_reduce(schema, document) == document

    def test_array_position_restriction(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "record": {
                    "type": "array",
                    "items": [
                        {"type": "string"},
                        {"type": "integer"},
                    ],
                }
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"record": ["Janice", 5]}
        assert schema_reduce(schema, document) == document

    def test_array_position_restriction_with_reference(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "definitions": {
                "some_number": {"type": "integer"},
            },
            "properties": {
                "record": {
                    "type": "array",
                    "items": [
                        {"type": "string"},
                        {"$ref": "#/definitions/some_number"},
                    ],
                }
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"record": ["Janice", 5]}
        assert schema_reduce(schema, document) == document

    def test_array_position_restriction_too_many_items(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "record": {
                    "type": "array",
                    "items": [
                        {"type": "string"},
                        {"type": "integer"},
                    ],
                }
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"record": ["Janice", 5, 5]}
        msg_pattern = r"invalid: .record: too many items"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert schema_reduce(schema, document) == document

    def test_array_position_restriction_invalid(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "record": {
                    "type": "array",
                    "items": [
                        {"type": "string"},
                        {"type": "integer"},
                    ],
                }
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"record": [5, "Janice"]}
        msg_pattern = r"invalid: .record.\[0\]: type not in \['string'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert schema_reduce(schema, document) == document

    def test_references(self):
        """Verify references are traversed."""
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
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
        jsonschema.Draft4Validator.check_schema(schema)

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
        assert schema_reduce(schema, document) == expected_document

    def test_invalid_ref(self):
        """Reducer only support json pointers to things in the schema"""
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "numbers": {
                    "type": "array",
                    "items": {"$ref": "http://example.com/schema"},
                }
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"numbers": [1, 5, 10]}
        with pytest.raises(InvalidSchemaError):
            assert schema_reduce(schema, document) == document

    def test_include_predicate(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "socorro_permissions": ["public"],
                        },
                        "favorites": {
                            "type": "object",
                            "properties": {
                                "color": {
                                    "type": "string",
                                    "socorro_permissions": ["public"],
                                },
                                # ice_cream is not marked public
                                "ice_cream": {"type": "string"},
                            },
                            "socorro_permissions": ["public"],
                        },
                    },
                    "socorro_permissions": ["public"],
                },
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {
            "person": {
                "name": "Jha",
                "favorites": {
                    "color": "blue",
                    # ice_cream is not marked public, so it will be removed
                    "ice_cream": "vanilla",
                },
            }
        }
        expected_document = {
            "person": {
                "name": "Jha",
                "favorites": {
                    "color": "blue",
                },
            },
        }

        def only_public(path, general_path, schema_item):
            return "public" in schema_item.get("socorro_permissions", [])

        reduced_document = schema_reduce(
            schema, document, include_predicate=only_public
        )
        assert reduced_document == expected_document

    def test_socorroConvertTo(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": ["string", "null"], "socorroConvertTo": "string"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        assert schema_reduce(schema, {"years": "10"}) == {"years": "10"}
        assert schema_reduce(schema, {"years": 10}) == {"years": "10"}
        assert schema_reduce(schema, {"years": None}) == {"years": None}


@pytest.mark.parametrize(
    "schema, nodes",
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
            ["", ".key1", ".key2"],
        ),
        # Object traversal with patternProperties
        (
            {
                "type": "object",
                "patternProperties": {
                    "^r.+$": {
                        "type": "string",
                    },
                    "^c.+$": {
                        "type": "string",
                    },
                },
            },
            ["", ".(re:^r.+$)", ".(re:^c.+$)"],
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
            ["", ".colors", ".colors.[]"],
        ),
        # Array traversal with items as list indicating records
        (
            {
                "type": "object",
                "properties": {
                    "person": {
                        "type": "array",
                        "items": [
                            {"type": "string"},
                            {"type": "integer"},
                        ],
                    },
                },
            },
            ["", ".person", ".person.[0]", ".person.[1]"],
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
            ["", ".colors", ".colors.[]", ".colors.[].name", ".colors.[].hex"],
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
            ["", ".colors", ".colors.[]", ".colors.[].name", ".colors.[].hex"],
        ),
    ],
)
def test_traverse_schema(schema, nodes):
    class Visitor:
        def __init__(self):
            self.nodes = []

        def visit(self, path, general_path, schema):
            self.nodes.append(path)

    visitor = Visitor()
    traverse_schema(schema=schema, visitor_function=visitor.visit)
    assert visitor.nodes == nodes


@pytest.mark.parametrize(
    "permissions_have, expected",
    [
        (
            ["public"],
            {"key1": "abc"},
        ),
        (
            ["public", "protected"],
            {
                "key1": "abc",
                "key2": "def",
                "key3": {"key3sub1": "ghi"},
                "key4": ["jkl"],
            },
        ),
    ],
)
def test_permissions_predicate(permissions_have, expected):
    schema = {
        "$id": "https://mozilla.org/schemas/libjson_test/1",
        "type": "object",
        "properties": {
            "key1": {
                "type": "string",
                "socorro": {
                    "permissions": ["public"],
                },
            },
            "key2": {
                "type": "string",
                "socorro": {
                    "permissions": ["protected"],
                },
            },
            "key3": {
                "type": "object",
                "properties": {
                    "key3sub1": {
                        "type": "string",
                        "socorro": {
                            "permissions": ["protected"],
                        },
                    },
                },
                "socorro": {
                    "permissions": ["protected"],
                },
            },
            "key4": {
                "type": "array",
                "items": {
                    "type": "string",
                    "socorro": {
                        "permissions": ["protected"],
                    },
                },
                "socorro": {
                    "permissions": ["protected"],
                },
            },
        },
    }

    document = {
        "key1": "abc",
        "key2": "def",
        "key3": {
            "key3sub1": "ghi",
        },
        "key4": ["jkl"],
    }

    predicate = permissions_predicate(permissions_have=permissions_have)
    reducer = Reducer(schema=schema, include_predicate=predicate)
    redacted_document = reducer.traverse(document=document)
    assert redacted_document == expected

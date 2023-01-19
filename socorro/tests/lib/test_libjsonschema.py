# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import jsonschema
import pytest

from socorro.lib.libjsonschema import (
    InvalidDocumentError,
    InvalidSchemaError,
    JsonSchemaReducer,
    resolve_references,
)


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
                            },
                            "cost": {
                                "description": "the cost",
                                "type": "integer",
                            },
                        },
                        "type": "object",
                    },
                },
                "properties": {
                    "color": {
                        "description": "the color used here",
                        "$ref": "#/definitions/color",
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
                            },
                            "cost": {
                                "type": "integer",
                                "description": "the cost",
                            },
                        },
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
                    },
                },
                "properties": {
                    "colors": {
                        "description": "list of colors",
                        "items": {
                            "description": "a single color",
                            "$ref": "#/definitions/color",
                        },
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
                            "type": "string",
                        },
                        "type": "array",
                    },
                },
                "type": "object",
            },
        ),
    ],
)
def test_resolve_references(schema, expected):
    assert resolve_references(schema) == expected


class TestJsonSchemaReducer:
    def schema_reduce(self, schema, document):
        reducer = JsonSchemaReducer(schema=schema)
        return reducer.traverse(document=document)

    def test_multiple_types_and_null(self):
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": ["integer", "null"]},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"years": 10}
        assert self.schema_reduce(schema, document) == document

        document = {"years": None}
        assert self.schema_reduce(schema, document) == document

        document = {}
        assert self.schema_reduce(schema, document) == document

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
        assert self.schema_reduce(schema, document) == document

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
        msg_pattern = r"invalid: .years: type string not in \['integer'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert self.schema_reduce(schema, document) == document

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
        assert self.schema_reduce(schema, document) == document

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
        msg_pattern = r"invalid: .years: type string not in \['number'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert self.schema_reduce(schema, document) == document

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
        assert self.schema_reduce(schema, document) == document

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
        assert self.schema_reduce(schema, document) == expected_document

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
        assert self.schema_reduce(schema, document) == document

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
        msg_pattern = r"invalid: .numbers.\[1\]: type string not in \['integer'\]"
        with pytest.raises(InvalidDocumentError, match=msg_pattern):
            assert self.schema_reduce(schema, document) == document

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
        assert self.schema_reduce(schema, document) == document

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
        assert self.schema_reduce(schema, document) == expected_document

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
            assert self.schema_reduce(schema, document) == document

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

        assert self.schema_reduce(schema, {"years": "10"}) == {"years": "10"}
        assert self.schema_reduce(schema, {"years": 10}) == {"years": "10"}
        assert self.schema_reduce(schema, {"years": None}) == {"years": None}

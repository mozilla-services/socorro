# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import jsonschema
import pytest

from socorro.lib.libjson import schema_reduce, InvalidDocumentError, InvalidSchemaError


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

    def test_integer(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": "integer"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        document = {"years": 10}
        assert schema_reduce(schema, document) == document

    def test_bad_integer(self):
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

    @pytest.mark.parametrize("number", [-10, 10, 10.5])
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

    def test_object(self):
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
        msg_pattern = r"invalid: .numbers.1: type not in \['integer'\]"
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
        msg_pattern = r"invalid: .record.0: type not in \['string'\]"
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

        def only_public(schema_item):
            return "public" in schema_item.get("socorro_permissions", [])

        reduced_document = schema_reduce(
            schema, document, include_predicate=only_public
        )
        assert reduced_document == expected_document

    def test_convert_to(self):
        schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "$target_version": 2,
            "type": "object",
            "properties": {
                "years": {"type": ["string", "null"], "socorro_convert_to": "string"},
            },
        }
        jsonschema.Draft4Validator.check_schema(schema)

        assert schema_reduce(schema, {"years": "10"}) == {"years": "10"}
        assert schema_reduce(schema, {"years": 10}) == {"years": "10"}
        assert schema_reduce(schema, {"years": None}) == {"years": None}

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Utilities for working with JSON schemas and JSON.
"""


class InvalidDocumentError(Exception):
    """Raised when the document is invalid"""


class InvalidSchemaError(Exception):
    """Raised when the schema is invalid"""


class UnknownConvertFormat(Exception):
    """Raised when the schema specifies an unknown convert format"""


def listify(item):
    if isinstance(item, (tuple, list)):
        return item

    return [item]


BASIC_TYPES = {
    type(None): "null",
    bool: "boolean",
    str: "string",
    int: ("integer", "number"),
    float: "number",
}
BASIC_TYPES_KEYS = tuple(BASIC_TYPES.keys())


def lookup_definition(schema, ref):
    """Looks up a JSON pointer in the definitions.

    .. Note::

       This only supports definitions in the current document and doesn't
       support URIs.

    :arg dict schema: the full schema
    :arg string ref: a ref like "#/definition/frames"

    :returns: schema

    """
    ref_parts = ref.split("/")
    if not ref_parts or ref_parts[0] != "#":
        raise InvalidSchemaError("invalid: $ref must be in this document {ref!r}")

    # Ignore first item which should be "#"
    for part in ref_parts[1:]:
        schema = schema.get(part, {})
    return schema


def expand_references(schema, schema_item):
    """Expands $ref items

    :arg dict schema: the schema
    :arg dict schema_item: the sub-schema we're expanding a reference in

    :returns: the new schema item with reference expanded

    """
    # FIXME(willkg): expanding references doesn't handle cycles, but we could handle
    # that if we switched from recursion to iterative and maintaining context
    if "$ref" in schema_item:
        return lookup_definition(schema, schema_item["$ref"])
    return schema_item


def everything_predicate(schema_item):
    """include_predicate that includes everything in the document"""
    return True


def convert_to(document_part, target_format):
    """Conversion for handling historical schema goofs"""
    # We never convert nulls
    if document_part is None:
        return document_part

    if target_format == "string":
        # Boolean gets convert to "0" or "1"
        if document_part is True:
            return "1"
        elif document_part is False:
            return "0"
        return str(document_part)

    raise UnknownConvertFormat(f"{target_format!r} is an unknown format")


class Reducer:
    def __init__(self, schema, include_predicate=everything_predicate):
        self.schema = schema
        self.include_predicate = include_predicate

    def traverse(self, schema_part, document_part, path=""):
        """Following the schema, traverses the document

        This validates types and some type-related restrictions while reducing the
        document to the schema.

        :arg dict schema_part: the part of the schema we're looking at now
        :arg dict document_part: the part of the document we're looking at now
        :arg string path: the path in the structure for error reporting

        :returns: new document

        """
        # Telemetry ingestion is marred by historical fun-ness, so we first look at the
        # schema and if it defines a converter, we run the document part through that
        # first.
        if "socorro_convert_to" in schema_part:
            document_part = convert_to(document_part, schema_part["socorro_convert_to"])

        schema_part_types = listify(schema_part.get("type", "string"))

        # FIXME(willkg): implement:
        #
        # * string: minLength, maxLength, pattern
        # * integer/number: minimum, maximum, exclusiveMaximum, exclusiveMinimum, multipleOf
        # * array: maxItems, minItems, uniqueItems
        # * object: additionalProperties, minProperties, maxProperties, dependencies,
        #   patternProperties, regexp
        if isinstance(document_part, BASIC_TYPES_KEYS):
            valid_schema_part_types = listify(BASIC_TYPES[type(document_part)])
            for type_ in valid_schema_part_types:
                if type_ in schema_part_types:
                    return document_part

            raise InvalidDocumentError(
                f"invalid: {path}: type not in {schema_part_types}"
            )

        if isinstance(document_part, list):
            if "array" not in schema_part_types:
                raise InvalidDocumentError(
                    f"invalid: {path}: type not in {schema_part_types}"
                )

            schema_items = schema_part.get("items", {"type": "string"})
            if isinstance(schema_items, list):
                # If schema_items is a list, then it's denoting a record like thing and the
                # document must match the schema items in the list (or fewer)
                schema_items = [
                    expand_references(self.schema, schema_item)
                    for schema_item in schema_items
                ]
                new_doc = []
                if len(document_part) > len(schema_items):
                    raise InvalidDocumentError(f"invalid: {path}: too many items")

                for i in range(0, len(document_part)):
                    new_part = self.traverse(
                        schema_part=schema_items[i],
                        document_part=document_part[i],
                        path=f"{path}.{i}",
                    )
                    new_doc.append(new_part)
                return new_doc

            # If schema_items is not a list, then each document_part must match this
            # schema
            schema_item = expand_references(self.schema, schema_items)

            new_doc = []
            for i in range(0, len(document_part)):
                new_part = self.traverse(
                    schema_part=schema_item,
                    document_part=document_part[i],
                    path=f"{path}.{i}",
                )
                new_doc.append(new_part)
            return new_doc

        if isinstance(document_part, dict):
            if "object" not in schema_part_types:
                raise InvalidDocumentError(
                    f"invalid: {path}: type not in {schema_part_types}"
                )

            properties = schema_part.get("properties", {})
            new_doc = {}
            for name, schema_property in properties.items():
                required_properties = schema_part.get("required", [])

                if not self.include_predicate(schema_property):
                    continue

                schema_property = expand_references(self.schema, schema_property)

                if name in document_part:
                    new_doc[name] = self.traverse(
                        schema_part=schema_property,
                        document_part=document_part[name],
                        path=f"{path}.{name}",
                    )
                elif name in required_properties:
                    raise InvalidDocumentError(
                        f"invalid: {path}.{name}: required, but missing"
                    )

            return new_doc


def schema_reduce(schema, document, include_predicate=everything_predicate):
    """Reduce a given document to a structure specified in the schema

    There's some overlap between reducing and validating the document. This does type
    validation, but doesn't do other kinds of validation like minItems/maxItems,
    additionalProperties, etc.

    .. Note::

       This does not validate that the schema is valid JSON schema. It's assumed
       that's the case.

    :arg dict schema: a JSON schema as a Python dict structure
    :arg dict document: a Python dict structure
    :arg function include_predicate: a function that takes a schema part
        and returns whether to include the document part

    :returns: a reduced Python dict structure and list of errors

    :raises InvalidDocumentError: raised for anything in the document that doesn't
        validate with the schema: type mismatches, JSON schema requirements fails, etc

    :raises InvalidSchemaError: raised for issues with the schema

    """
    reducer = Reducer(schema, include_predicate)
    return reducer.traverse(schema_part=schema, document_part=document)

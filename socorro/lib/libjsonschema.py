# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utilities for working with jsonschemas.
"""

import copy


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
    int: "integer",
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
        raise InvalidSchemaError(f"invalid: $ref must be in this document {ref!r}")

    # Ignore first item which should be "#"
    for part in ref_parts[1:]:
        schema = schema.get(part, {})
    return schema


def resolve_reference(root_schema, schema, ref):
    """Given a root schema and a schema with a ref, resolves the ref

    :arg root schema: the root schema holding a "definitions" section
    :arg schema: the schema to resolve the reference in
    :arg ref: the ``$ref`` value

    :returns: the new schema with the reference resolved

    """
    # Resolve by finding the referenced schema, update it with schema data, and then
    # returning it
    #
    # Deepcopy because this schema can end up in multiple parts of the tree.
    new_schema = copy.deepcopy(lookup_definition(root_schema, ref))

    # Copy anything from the original schema (other than "$ref") into the
    # new schema
    for key, val in schema.items():
        if key == "$ref":
            continue
        new_schema[key] = copy.deepcopy(schema[key])

    return new_schema


def resolve_references(schema):
    """Returns a schema with all ``$ref`` resolved

    .. Note::

       When resolving a ``$ref``, all the properties are replaced with the exception of
       "socorro" which is copied into the referenced schema.

       For example::

           "definitions": {
               "color_definition": {
                   "type": "object",
                   "properties": {
                       "name": {"type": "string"},
                       "hex": {"type": "string"},
                   },
                   "foo": "bat",
                   # This is overwritten by the referring schema
                   "properties": ["public"],
               },
           },
           "color": {
               "$ref": "#/definitions/color_definition",
               "foo": "bar",
               "properties": ["protected"],
           }

       Results in:

           "color": {
               # From the referenced schema
               "type": "object",
               "properties": {
                   "name": {"type": "string"},
                   "hex": {"type": "string"},
               },
               "foo": "bat",
               # From the referring schema
               "properties": ["protected"],
           }

    :arg dict schema: the schema

    :returns: the new schema item with ``$ref`` resolved

    """
    # FIXME(willkg): resolving references doesn't currently handle cycles

    def _resolve(root_schema, schema):
        if not schema:
            return schema

        if "$ref" in schema:
            schema = resolve_reference(
                root_schema=root_schema,
                schema=schema,
                ref=schema["$ref"],
            )

        type_ = schema["type"]
        if "object" in type_:
            if schema.get("properties"):
                schema["properties"] = {
                    key: _resolve(root_schema, val)
                    for key, val in schema["properties"].items()
                }

        elif "array" in type_:
            schema_items = schema.get("items", {"type": "string"})
            # NOTE(willkg): this doesn't support record-type arrays; we should add that
            # if we need it
            schema["items"] = _resolve(root_schema, schema_items)

        return schema

    # Remove the "definitions" section to make it smaller
    new_schema = _resolve(root_schema=schema, schema=schema)
    if "definitions" in new_schema:
        del new_schema["definitions"]
    return new_schema


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


class JsonSchemaReducer:
    """Reducer for reducing a document to the structure of the specified jsonschema

    Several things to know about the reducer:

    1. It doesn't support full jsonschema spec--it only supports the parts we
       needed for our schemas.
    2. It does some light type validation and raises exceptions for documents that
       are invalid.

    """

    def __init__(self, schema):
        """
        :arg schema: the schema document specifying the structure to traverse
        """
        schema = resolve_references(schema)
        self.schema = schema

        self._pattern_cache = {}

    def get_schema_property(self, schema_part, name):
        """Returns the matching property value

        :arg dict schema_part: the part of the schema we're looking at now
        :arg string name: the name we're looking for

        :returns: property schema or None

        """
        properties = schema_part.get("properties", {})
        if name in properties:
            return schema_part["properties"][name]

        return None

    def traverse(self, document):
        """Following the schema, traverses the document

        This validates types and some type-related restrictions while traversing the
        document using the structure specified in the schema.

        :arg dict document: the document to traverse using the structure specified
            in the schema

        :returns: new document

        """
        return self._traverse(schema_part=self.schema, document_part=document)

    def _traverse(self, schema_part, document_part, path="", general_path=""):
        """Following the schema, traverses the document

        This validates types and some type-related restrictions while reducing the
        document to the schema.

        :arg dict schema_part: the part of the schema we're looking at now
        :arg dict document_part: the part of the document we're looking at now
        :arg string path: the path in the structure
        :arg string general_path: the generalized path in the structure where array
            indexes are replaced with `[]`

        :returns: new document

        """
        # Telemetry ingestion is marred by historical fun-ness, so we first look at the
        # schema and if it defines a converter, we run the document part through that
        # first.
        if "socorroConvertTo" in schema_part:
            document_part = convert_to(document_part, schema_part["socorroConvertTo"])

        schema_part_types = listify(schema_part.get("type", "string"))

        # FIXME(willkg): maybe implement:
        #
        # * string: minLength, maxLength, pattern
        # * integer/number: minimum, maximum, exclusiveMaximum, exclusiveMinimum,
        #   multipleOf
        # * array: maxItems, minItems, uniqueItems
        # * object: additionalProperties, minProperties, maxProperties, dependencies,
        #   regexp

        # If the document_part is a basic type (string, number, etc) and it matches
        # what's in the schema, then return it so it's included in the reduced document
        if isinstance(document_part, BASIC_TYPES_KEYS):
            valid_schema_part_type = BASIC_TYPES[type(document_part)]
            if valid_schema_part_type in schema_part_types:
                return document_part

            raise InvalidDocumentError(
                f"invalid: {path}: type {valid_schema_part_type} not in "
                + f"{schema_part_types}"
            )

        if isinstance(document_part, list):
            if "array" not in schema_part_types:
                raise InvalidDocumentError(
                    f"invalid: {path}: type array not in {schema_part_types}"
                )

            schema_items = schema_part.get("items", {"type": "string"})
            if isinstance(schema_items, list):
                # If schema_items is a list, then it's denoting a record like thing and the
                # document must match the schema items in the list (or fewer)
                new_doc = []
                if len(document_part) > len(schema_items):
                    raise InvalidDocumentError(f"invalid: {path}: too many items")

                for i in range(0, len(document_part)):
                    schema_item = schema_items[i]

                    schema_item_path = f"{path}.[{i}]"
                    # Since this is a record and position matters, we keep the
                    # index number
                    schema_item_general_path = f"{general_path}.[{i}]"

                    new_part = self._traverse(
                        schema_part=schema_items[i],
                        document_part=document_part[i],
                        path=schema_item_path,
                        general_path=schema_item_general_path,
                    )
                    new_doc.append(new_part)
                return new_doc

            # If schema_items is not a list, then each document_part must match this
            # schema
            schema_item = schema_items
            schema_item_path = f"{path}.[]"
            schema_item_general_path = f"{path}.[]"

            new_doc = []
            for i in range(0, len(document_part)):
                schema_item_path = f"{path}.[{i}]"
                schema_item_general_path = f"{path}.[]"
                new_part = self._traverse(
                    schema_part=schema_item,
                    document_part=document_part[i],
                    path=schema_item_path,
                    general_path=schema_item_general_path,
                )
                new_doc.append(new_part)
            return new_doc

        if isinstance(document_part, dict):
            if "object" not in schema_part_types:
                raise InvalidDocumentError(
                    f"invalid: {path}: type object not in {schema_part_types}"
                )

            new_doc = {}
            for name, document_property in document_part.items():
                properties = schema_part.get("properties", {})

                # If the item is in the document, but not in the schema, we don't add
                # this part of the document to the new document
                if name not in properties:
                    continue

                schema_property = schema_part["properties"][name]

                path_name = f"{path}.{name}"
                general_path_name = f"{general_path}.{name}"

                new_doc[name] = self._traverse(
                    schema_part=schema_property,
                    document_part=document_part[name],
                    path=path_name,
                    general_path=general_path_name,
                )

            return new_doc

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utilities for working with JSON schemas and JSON.
"""

import copy
import re


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

    This works for both jsonschema schemas and socorro-data schemas.

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
            if schema.get("pattern_properties"):
                schema["pattern_properties"] = {
                    key: _resolve(root_schema, val)
                    for key, val in schema["pattern_properties"].items()
                }

        elif "array" in type_:
            schema["items"] = _resolve(root_schema, schema["items"])

        return schema

    # Remove the "definitions" section to make it smaller
    new_schema = _resolve(root_schema=schema, schema=schema)
    if "definitions" in new_schema:
        del new_schema["definitions"]
    return new_schema


class _DropItem:
    def __repr__(self):
        return "<DROP>"


DROP_ITEM = _DropItem()


def permissions_transform_function(permissions_have):
    """Creates a permissions transform function that returns True iff user has all
    required permissions for specified field

    :arg permissions_have: the list of permissions the user has

    :returns: True if the user has all required permissions

    """
    permissions_have = frozenset(permissions_have)

    def _permissions_predicate(path, schema_item):
        permissions_required = schema_item.get("permissions") or []
        permissions_required = frozenset(permissions_required)

        if len(permissions_required - permissions_have) > 0:
            return DROP_ITEM
        return schema_item

    return _permissions_predicate


class FlattenSchemaKeys:
    def __init__(self):
        self.keys = []

    def flatten(self, path, schema):
        # Skip the root (path == "") and any arrays (we're interested in the items in
        # the array and not the array itself)
        if path and "array" not in schema["type"]:
            self.keys.append(path.lstrip("."))
        return schema


def transform_socorro_data_schema(schema, transform_function):
    """Transforms a socorro-data schema using some transform_function called on nodes

    The ``transform_function`` gets called pre-order as the schema is traversed.

    :arg dict schema: the schema
    :arg function transform_function: function transforming nodes in pre-order

    :returns: the new schema

    """

    def _transform_schema(schema, path, transform_function):
        type_ = schema["type"]

        new_schema = transform_function(path, schema)
        if new_schema == DROP_ITEM:
            return DROP_ITEM

        if "object" in type_:
            keep = False
            if schema.get("properties") is not None:
                new_properties = {}
                for key, val in schema["properties"].items():
                    new_item = _transform_schema(
                        schema=val,
                        path=f"{path}.{key}",
                        transform_function=transform_function,
                    )
                    if new_item != DROP_ITEM:
                        new_properties[key] = new_item
                        keep = True
                new_schema["properties"] = new_properties

            if schema.get("pattern_properties") is not None:
                new_properties = {}
                for key, val in schema["pattern_properties"].items():
                    new_item = _transform_schema(
                        schema=val,
                        path=f"{path}.(re:{key})",
                        transform_function=transform_function,
                    )
                    if new_item != DROP_ITEM:
                        new_properties[key] = new_item
                        keep = True
                new_schema["pattern_properties"] = new_properties

            if not keep:
                return DROP_ITEM

        elif "array" in type_:
            keep = False
            new_items = _transform_schema(
                schema=schema["items"],
                path=f"{path}.[]",
                transform_function=transform_function,
            )
            if new_items != DROP_ITEM:
                schema["items"] = new_items
                keep = True

            if not keep:
                return DROP_ITEM

        return new_schema

    # Copy the schema so transforms can be lazy about being pristine about changes
    schema = copy.deepcopy(schema)

    if "definitions" in schema:
        schema = resolve_references(schema)

    new_schema = _transform_schema(
        schema=schema,
        path="",
        transform_function=transform_function,
    )
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


# Cache of pattern -> re object
PATTERN_CACHE = {}


def compile_pattern_re(pattern):
    """Compile a patternProperties regex pattern

    Note that uses a module-level cache to reduce repeated pattern compiling.

    :arg string pattern: a patternProperties regex pattern

    :returns: re.Pattern

    """
    if pattern not in PATTERN_CACHE:
        PATTERN_CACHE[pattern] = re.compile(pattern)
    return PATTERN_CACHE[pattern]


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
        self.schema = schema

        self._pattern_cache = {}

    def get_schema_property(self, schema_part, name):
        """Returns the matching property or patternProperties value

        :arg dict schema_part: the part of the schema we're looking at now
        :arg string name: the name we're looking for

        :returns: property schema or None

        """
        properties = schema_part.get("properties", {})
        if name in properties:
            return schema_part["properties"][name]

        pattern_properties = schema_part.get("patternProperties", {})
        for pattern, property_schema in pattern_properties.items():
            pattern_re = compile_pattern_re(pattern)
            if pattern_re.match(name):
                return property_schema

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

                    if "$ref" in schema_item:
                        schema_item = resolve_reference(
                            root_schema=self.schema,
                            schema=schema_item,
                            ref=schema_item["$ref"],
                        )

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

            if "$ref" in schema_item:
                schema_item = resolve_reference(
                    root_schema=self.schema,
                    schema=schema_item,
                    ref=schema_item["$ref"],
                )

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
                schema_property = self.get_schema_property(schema_part, name)

                # If the item is in the document, but not in the schema, we don't add
                # this part of the document to the new document
                if schema_property is None:
                    continue

                path_name = f"{path}.{name}"
                general_path_name = f"{general_path}.{name}"

                # Expand references in the schema property
                if "$ref" in schema_property:
                    schema_property = resolve_reference(
                        root_schema=self.schema,
                        schema=schema_property,
                        ref=schema_property["$ref"],
                    )

                new_doc[name] = self._traverse(
                    schema_part=schema_property,
                    document_part=document_part[name],
                    path=path_name,
                    general_path=general_path_name,
                )

            # Verify all required properties exist in the document
            for required_property in schema_part.get("required", []):
                if required_property not in new_doc:
                    required_property_path = ".".join([path, required_property])
                    raise InvalidDocumentError(
                        f"invalid: {required_property_path}: required, but missing"
                    )

            return new_doc


class SocorroDataReducer:
    """Reducer for reducing a document to the structure of the specified socorro-data
    schema

    This does some light type validation and raises exceptions for documents that
    are invalid.

    """

    def __init__(self, schema):
        """
        :arg schema: the schema document specifying the structure to traverse
        """
        if "definitions" in schema:
            schema = resolve_references(schema)

        self.schema = schema
        self._pattern_cache = {}

    def get_schema_property(self, schema_part, name):
        """Returns the matching property or pattern_properties value

        :arg dict schema_part: the part of the schema we're looking at now
        :arg string name: the name we're looking for

        :returns: property schema or None

        """
        properties = schema_part.get("properties", {})
        if name in properties:
            return schema_part["properties"][name]

        pattern_properties = schema_part.get("pattern_properties", {})
        for pattern, property_schema in pattern_properties.items():
            pattern_re = compile_pattern_re(pattern)
            if pattern_re.match(name):
                return property_schema

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

    def _traverse(self, schema_part, document_part, path=""):
        """Following the schema, traverses the document

        This validates types and some type-related restrictions while reducing the
        document to the schema.

        :arg dict schema_part: the part of the schema we're looking at now
        :arg dict document_part: the part of the document we're looking at now
        :arg string path: the path in the structure

        :returns: new document

        """
        schema_part_types = listify(schema_part["type"])

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

        elif isinstance(document_part, list):
            if "array" not in schema_part_types:
                raise InvalidDocumentError(
                    f"invalid: {path}: type array not in {schema_part_types}"
                )

            schema_item = schema_part["items"]
            schema_item_path = f"{path}.[]"

            new_doc = []
            for i in range(0, len(document_part)):
                schema_item_path = f"{path}.[{i}]"
                new_part = self._traverse(
                    schema_part=schema_item,
                    document_part=document_part[i],
                    path=schema_item_path,
                )
                new_doc.append(new_part)
            return new_doc

        elif isinstance(document_part, dict):
            if "object" not in schema_part_types:
                raise InvalidDocumentError(
                    f"invalid: {path}: type object not in {schema_part_types}"
                )

            new_doc = {}
            for name, document_property in document_part.items():
                schema_property = self.get_schema_property(schema_part, name)

                # If the item is in the document, but not in the schema, we don't add
                # this part of the document to the new document
                if schema_property is None:
                    continue

                path_name = f"{path}.{name}"

                new_doc[name] = self._traverse(
                    schema_part=schema_property,
                    document_part=document_part[name],
                    path=path_name,
                )

            # Verify all required properties exist in the document
            for required_property in schema_part.get("required", []):
                if required_property not in new_doc:
                    required_property_path = ".".join([path, required_property])
                    raise InvalidDocumentError(
                        f"invalid: {required_property_path}: required, but missing"
                    )

            return new_doc

        else:
            raise InvalidDocumentError(
                f"invalid: {path}: type {type(document_part)} not recognized"
            )

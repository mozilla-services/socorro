# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utilities for working with socorro-data schemas.
"""

import copy
import re

import jsonschema


class InvalidDocumentError(Exception):
    """Raised when the document is invalid"""


class InvalidSchemaError(Exception):
    """Raised when the schema is invalid"""


def listify(item):
    if isinstance(item, (tuple, list)):
        return item

    return [item]


def split_path(path):
    """Split a general path into parts

    This handles the case where pattern_properties parts are enclosed in parens and can
    contain ``.`` which is a regex thing.

    :arg path: a path to split

    :returns: generator of parts

    """
    part = []
    in_paren = False
    for c in path:
        if in_paren:
            if c == ")":
                in_paren = False
            part.append(c)
        elif c == "(":
            in_paren = True
            part.append(c)
        elif c == ".":
            if part:
                yield "".join(part)
            part = []
        else:
            part.append(c)

    if part:
        yield "".join(part)


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


# FIXME(willkg): rewrite as a transform
def resolve_references(schema):
    """Returns a schema with all ``$ref`` resolved

    This works for both jsonschema schemas and socorro-data schemas because they
    both support ``$ref`` in the same way Socorro uses it.

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


class FlattenKeys:
    def __init__(self):
        self.keys = []

    def flatten(self, path, schema):
        # Skip the root (path == "") and any arrays (we're interested in the items in
        # the array and not the array itself)
        if path and "array" not in schema["type"]:
            self.keys.append(path.lstrip("."))
        return schema


def transform_schema(schema, transform_function):
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
        schema = copy.deepcopy(schema)
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

            new_doc = []
            for i in range(0, len(document_part)):
                new_part = self._traverse(
                    schema_part=schema_item,
                    document_part=document_part[i],
                    path=f"{path}.[{i}]",
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

                new_doc[name] = self._traverse(
                    schema_part=schema_property,
                    document_part=document_part[name],
                    path=f"{path}.{name}",
                )

            return new_doc

        else:
            raise InvalidDocumentError(
                f"invalid: {path}: type {type(document_part)} not recognized"
            )


def validate_instance(instance, schema):
    """Validates an instance document against the specified socorro-data schema

    :arg dict instance: the instance document
    :arg dict schema: the schema which is valid socorro-data schema

    :raises: validation errors

    """
    # NOTE(willkg): If we update the jsonschema used for socorro-data, we need to update
    # this, too
    jsonschema.validate(
        instance=instance, schema=schema, cls=jsonschema.Draft7Validator
    )

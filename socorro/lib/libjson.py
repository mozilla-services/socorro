# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utilities for working with JSON schemas and JSON.
"""

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


def permissions_predicate(permissions_have):
    """Creates a permissions predicate that returns True iff user has all required
    permissions for specified field

    :arg permissions_have: the list of permissions the user has

    :returns: True if the user has all required permissions

    """
    permissions_have = frozenset(permissions_have)

    def _permissions_predicate(path, general_path, schema_item):
        permissions_required = schema_item.get("socorro", {}).get("permissions")
        permissions_required = permissions_required or []
        permissions_required = frozenset(permissions_required)

        return not len(permissions_required - permissions_have) > 0

    return _permissions_predicate


def everything_predicate(path, general_path, schema_item):
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


class Reducer:
    def __init__(self, schema, include_predicate=everything_predicate):
        """
        :arg schema: the schema document specifying the structure to traverse
        :arg include_predicate: a predicate function that determines whether to
            include the traversed item or not in the final document
        """
        self.schema = schema
        self.include_predicate = include_predicate

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
        document using the structure specified in the schema and calling the
        include_predicate.

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
                    schema_item_path = f"{path}.[{i}]"
                    # Since this is a record and position matters, we keep the
                    # index number
                    schema_item_general_path = f"{general_path}.[{i}]"

                    # If the predicate doesn't pass, we don't add this part of the document
                    # to the new document
                    if not self.include_predicate(
                        path=schema_item_path,
                        general_path=schema_item_general_path,
                        schema_item=schema_items[i],
                    ):
                        # NOTE(willkg): This is a wonky case where one item in the
                        # record is being redacted. Since it's a record and position
                        # matters, we swap it to be a None
                        new_part = None
                    else:
                        new_part = self._traverse(
                            schema_part=schema_items[i],
                            document_part=document_part[i],
                            path=schema_item_path,
                            general_path=schema_item_general_path,
                        )
                    new_doc.append(new_part)
                return new_doc

            # If schema_items is not a list, then each document_part must match this
            # schema and match the predicate
            new_doc = []
            schema_item = expand_references(self.schema, schema_items)

            for i in range(0, len(document_part)):
                schema_item_path = f"{path}.[{i}]"
                schema_item_general_path = f"{path}.[]"
                if self.include_predicate(
                    path=schema_item_path,
                    general_path=schema_item_general_path,
                    schema_item=schema_item,
                ):
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
                    f"invalid: {path}: type not in {schema_part_types}"
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
                schema_property = expand_references(self.schema, schema_property)

                # If the predicate doesn't pass, we don't add this part of the document
                # to the new document
                if not self.include_predicate(
                    path=path_name,
                    general_path=general_path_name,
                    schema_item=schema_property,
                ):
                    continue

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
    reducer = Reducer(schema=schema, include_predicate=include_predicate)
    return reducer.traverse(document=document)


def print_function(path, general_path, schema_item):
    print(f"{path}: {schema_item}")


def traverse_schema(schema, visitor_function=print_function):
    def _traverse(root_schema, schema, visitor_function, path="", general_path=""):
        schema = expand_references(root_schema, schema)
        if "type" not in schema:
            raise InvalidSchemaError(f"{path} has no type")

        visitor_function(path, general_path, schema)

        type_ = schema["type"]
        if isinstance(type_, list):
            type_ = [t for t in type_ if t != "null"][0]

        if type_ == "object":
            for name, subschema in schema.get("properties", {}).items():
                _traverse(
                    root_schema=root_schema,
                    schema=subschema,
                    visitor_function=visitor_function,
                    path=f"{path}.{name}",
                    general_path=f"{general_path}.{name}",
                )

            for pattern, subschema in schema.get("patternProperties", {}).items():
                _traverse(
                    root_schema=root_schema,
                    schema=subschema,
                    visitor_function=visitor_function,
                    path=f"{path}.(re:{pattern})",
                    general_path=f"{general_path}.(re:{pattern})",
                )

        elif type_ == "array":
            items = schema.get("items", {"type": "string"})

            if isinstance(items, list):
                for i, item in enumerate(items):
                    _traverse(
                        root_schema=root_schema,
                        schema=item,
                        visitor_function=visitor_function,
                        path=f"{path}.[{i}]",
                        general_path=f"{general_path}.[]",
                    )
            else:
                _traverse(
                    root_schema=root_schema,
                    schema=items,
                    visitor_function=visitor_function,
                    path=f"{path}.[]",
                    general_path=f"{general_path}.[]",
                )

    return _traverse(
        root_schema=schema,
        schema=schema,
        visitor_function=visitor_function,
    )

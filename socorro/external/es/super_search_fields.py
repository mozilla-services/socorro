# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import suppress
import logging

from socorro.lib.libsocorrodataschema import get_schema


logger = logging.getLogger(__name__)


PROCESSED_CRASH_SCHEMA = get_schema("processed_crash.schema.yaml")


def parse_mapping(mapping, namespace):
    """Return set of fields in a mapping

    This parses the mapping recursively.

    :arg dict mapping: the mapping yielded by Elasticsearch
    :arg str namespace: the namespace being parsed or None for the root

    :returns: set of fields

    """
    fields = set()

    for key in mapping:
        field = mapping[key]
        if namespace:
            field_full_name = ".".join((namespace, key))
        else:
            field_full_name = key

        if "properties" in field:
            fields.update(parse_mapping(field["properties"], field_full_name))
        else:
            fields.add(field_full_name)

    return fields


def add_field_to_properties(properties, key_parts, field):
    """Add a field to a mapping properties

    An Elasticsearch mapping is a specification for how to index all
    the fields for a document type. This builds that mapping one field
    at a time taking into account that some fields are nested and
    the nesting needs to be built before that field can be added at
    the proper place.

    Note: This inserts things in-place and recurses on namespaces.

    :param properties: the mapping we're adding the field to
    :param key: a list of key parts denoting where the field needs to be inserted
    :param field: the field value from super search fields containing
        the ``storage_mapping`` to be added to the properties

    """
    if len(key_parts) == 1:
        properties[key_parts[0]] = field["storage_mapping"]
        return

    namespace = key_parts.pop(0)

    if namespace not in properties:
        properties[namespace] = {"type": "object", "dynamic": "true", "properties": {}}

    add_field_to_properties(properties[namespace]["properties"], key_parts, field)


def is_indexable(field):
    """Returns True if the field is indexable

    :param field: the field to check

    :returns: True if indexable and False if not

    """
    # All of these things have to be non-None and non-empty for this field to be
    # indexable
    return bool(
        get_source_key(field)
        and get_destination_keys(field)
        and field.get("storage_mapping")
    )


def get_search_key(field):
    """Returns the key in the indexed document to use for search

    This returns either the value of ``search_key`` in the field properties or the first
    destination key.

    :param field: a super search fields field

    :returns: the search key as a string or None if the field isn't
        indexable

    """
    search_key = field.get("search_key")
    if search_key is not None:
        return search_key

    destination_keys = get_destination_keys(field)
    return destination_keys[0]


def get_source_key(field):
    """Returns source key for the field.

    :param field: a super search fields field

    :returns: source key as a string or None if the field isn't indexable

    """
    src = field.get("source_key")
    if src:
        return src

    # If there isn't an explicit source key, derive it from the properties of the field
    namespace = field.get("namespace")
    in_database_name = field.get("in_database_name")
    if namespace and in_database_name:
        return f"{namespace}.{in_database_name}"

    # If the field has no namespace or in_database_name, then it's not indexable
    return None


def get_destination_keys(field):
    """Return a list of destination keys for this field.

    :param field: a super search fields field

    :returns: list of destination keys or None if the field is not indexable

    """
    dests = field.get("destination_keys")
    if dests:
        return dests

    # If there aren't explicit destination keys, derive them from the properties of the
    # field
    namespace = field.get("namespace")
    in_database_name = field.get("in_database_name")
    if namespace and in_database_name:
        return [f"{namespace}.{in_database_name}"]

    # If the field has no namespace or in_database_name, then it's not indexable
    return None


def build_mapping(fields=None):
    """Generates Elasticsearch mapping from the super search fields schema

    :arg any fields: map of field name -> field value; defaults to FIELDS

    :returns: Elasticsearch mapping

    """
    fields = fields or FIELDS
    properties = {}

    for field in fields.values():
        if not field.get("storage_mapping"):
            continue

        destination_keys = get_destination_keys(field)
        for destination_key in destination_keys:
            key_parts = destination_key.split(".")
            add_field_to_properties(properties, key_parts, field)

    mapping = {
        "properties": properties,
    }
    return mapping


# Cache of hashed_args -> list of fields values
_FIELDS_CACHE = {}


def get_fields_by_item(fields, key, val):
    """Returns the values in fields that have the specified key=val item

    Note: This "hashes" the fields argument by using `id`. I think this is fine because
    fields don't change between runs and it's not mutated in-place. We're hashing it
    sufficiently often that it's faster to use `id` than a more computationally
    intensive hash of a large data structure.

    :arg dict fields: dict of field information mapped as field name to
        properties
    :arg str key: the key to match; example: "analyzer"
    :arg str value: the value that key should have

    :returns: list of field properties for fields that match the analyzer

    """
    map_key = (id(fields), key, val)
    with suppress(KeyError):
        return _FIELDS_CACHE[map_key]

    def has_key_val(key, val, data):
        for this_key, this_val in data.items():
            if isinstance(this_val, dict):
                ret = has_key_val(key, val, this_val)
                if ret:
                    return True
            elif isinstance(this_key, str):
                if (this_key, this_val) == (key, val):
                    return True
        return False

    fields_by_item = [
        field for field in fields.values() if has_key_val(key, val, field)
    ]
    _FIELDS_CACHE[map_key] = fields_by_item
    return fields_by_item


def boolean_field(
    name,
    namespace="processed_crash",
    in_database_name="",
):
    """Generates a boolean field.

    These can be searched and aggregated, but documents that are missing the field won't
    show up in aggregations.

    :param name: the name used to query the field in super search
    :param namespace: either "processed_crash" or some dotted path to a key deep in
        the processed crash
    :param in_database_name: the field in the processed crash to pull this data from

    :returns: super search field specification as a dict

    """
    in_database_name = in_database_name or name

    return {
        "name": name,
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "namespace": namespace,
        "in_database_name": in_database_name,
        "is_exposed": True,
        "is_returned": True,
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    }


def keyword_field(
    name,
    namespace="processed_crash",
    in_database_name="",
    choices=None,
):
    """Generates a keyword field.

    Keyword field values are analyzed as a single token. This is good for ids, product
    names, fields that have a limited set of choices, etc.

    :param name: the name used to query the field in super search
    :param namespace: either "processed_crash" or some dotted path to a key deep in
        the processed crash
    :param in_database_name: the field in the processed crash to pull this data from
    :param choices: a list of valid values for the dropdown

    :returns: super search field specification as a dict

    """
    in_database_name = in_database_name or name

    choices = choices or []

    return {
        "name": name,
        "data_validation_type": "str",
        "form_field_choices": choices,
        "has_full_version": False,
        "namespace": namespace,
        "in_database_name": in_database_name,
        "is_exposed": True,
        "is_returned": True,
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    }


def text_field(
    name,
    has_full_version=True,
    storage_mapping=None,
    **kwargs,
):
    """Generates a text field.

    :param name: the name used to query the field in super search
    :param has_full_version: when True include a multi-field full version with the
        keyword type for sorting and aggregations
    :param storage_mapping: optional dict with additional items for storage_mapping
    :param **kwargs: may be used to add or override keys in the return value

    :returns: super search field specification as a dict

    """
    return {
        "name": name,
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": has_full_version,
        "namespace": "processed_crash",
        "in_database_name": name,
        "is_exposed": True,
        "is_returned": True,
        "query_type": "string",
        "storage_mapping": {
            "type": "text",
            **({"fields": {"full": {"type": "keyword"}}} if has_full_version else {}),
            **(storage_mapping or {}),
        },
        **kwargs,
    }


def integer_field(
    name,
    namespace="processed_crash",
    in_database_name="",
    storage_mapping_type="integer",
):
    """Generates a whole number field.

    :param name: the name used to query the field in super search
    :param namespace: either "processed_crash" or some dotted path to a key deep in
        the processed crash
    :param in_database_name: the field in the processed crash to pull this data from
    :param storage_mapping_type: the storage mapping type to use for Elasticsearch;
        "short", "integer", "long"

    :returns: super search field specification as a dict

    """
    in_database_name = in_database_name or name

    if storage_mapping_type not in ["short", "integer", "long"]:
        raise ValueError(f"storage_mapping_type {storage_mapping_type} is not valid")

    return {
        "name": name,
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "namespace": namespace,
        "in_database_name": in_database_name,
        "is_exposed": True,
        "is_returned": True,
        "query_type": "integer",
        "storage_mapping": {"type": storage_mapping_type},
    }


def float_field(
    name,
    namespace="processed_crash",
    in_database_name="",
):
    """Generates a floating point field.

    :param name: the name used to query the field in super search
    :param namespace: either "processed_crash" or some dotted path to a key deep in
        the processed crash
    :param in_database_name: the field in the processed crash to pull this data from

    :returns: super search field specification as a dict

    """
    in_database_name = in_database_name or name

    return {
        "name": name,
        "data_validation_type": "float",
        "form_field_choices": [],
        "has_full_version": False,
        "namespace": namespace,
        "in_database_name": in_database_name,
        "is_exposed": True,
        "is_returned": True,
        "query_type": "float",
        "storage_mapping": {"type": "double"},
    }


def apply_schema_properties(fields, schema):
    """Applies schema properties to super search fields

    This applies properties from the schema to super search fields. Currently, this
    is just "permissions", but later will include other things.

    Note: This mutates the fields input.

    :arg fields: the super search FIELDS structure
    :arg schema: a socorro data schema

    :returns: a super search FIELDS structure with schema properties added

    """
    default_permissions = schema["default_permissions"]

    for val in fields.values():
        source_key = get_source_key(val)
        if not source_key or not source_key.startswith("processed_crash."):
            continue

        path = source_key.split(".")[1:]
        schema_node = schema

        # NOTE(willkg): if the path doesn't point to something in the schema, that's
        # an error and we should fix the field
        for part in path:
            if "pattern_properties" in schema_node:
                # If "pattern_properties" is in the schema node, then we use the
                # permissions of the root for all children
                break
            schema_node = schema_node["properties"][part]

        val["permissions_needed"] = schema_node.get("permissions", default_permissions)
        val["description"] = schema_node.get("description", "")

    return fields


# Tree of super search fields
FIELDS = {
    "application_build_id": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "application_build_id",
        "is_exposed": True,
        "is_returned": True,
        "name": "application_build_id",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "crash_report_keys": keyword_field(name="crash_report_keys"),
    "phc_kind": {
        "data_validation_type": "str",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "phc_kind",
        "is_exposed": True,
        "is_returned": True,
        "name": "phc_kind",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "phc_base_address": text_field("phc_base_address"),
    "phc_usable_size": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "phc_usable_size",
        "is_exposed": True,
        "is_returned": True,
        "name": "phc_usable_size",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "phc_alloc_stack": text_field("phc_alloc_stack"),
    "phc_free_stack": text_field("phc_free_stack"),
    "abort_message": text_field("abort_message"),
    "accessibility": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "accessibility",
        "is_exposed": True,
        "is_returned": True,
        "name": "accessibility",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "accessibility_client": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "accessibility_client",
        "is_exposed": True,
        "is_returned": True,
        "name": "accessibility_client",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "accessibility_in_proc_client": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "accessibility_in_proc_client",
        "is_exposed": True,
        "is_returned": True,
        "name": "accessibility_in_proc_client",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "adapter_device_id": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "adapter_device_id",
        "is_exposed": True,
        "is_returned": True,
        "name": "adapter_device_id",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "adapter_driver_version": text_field("adapter_driver_version"),
    "adapter_subsys_id": text_field("adapter_subsys_id"),
    "adapter_vendor_id": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "adapter_vendor_id",
        "is_exposed": True,
        "is_returned": True,
        "name": "adapter_vendor_id",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "addons": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "addons",
        "is_exposed": True,
        "is_returned": True,
        "name": "addons",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "addons_checked": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "addons_checked",
        "is_exposed": True,
        "is_returned": True,
        "name": "addons_checked",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "boolean"},
    },
    "address": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "address",
        "is_exposed": True,
        "is_returned": True,
        "name": "address",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "android_board": text_field(
        "android_board", data_validation_type="enum", query_type="enum"
    ),
    "android_brand": text_field(
        "android_brand", data_validation_type="enum", query_type="enum"
    ),
    "android_cpu_abi": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "android_cpu_abi",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_cpu_abi",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "android_cpu_abi2": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "android_cpu_abi2",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_cpu_abi2",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "android_device": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "android_device",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_device",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "android_display": text_field(
        "android_display",
        data_validation_type="enum",
        form_field_choices=None,
        query_type="enum",
    ),
    "android_fingerprint": text_field(
        "android_fingerprint",
        data_validation_type="enum",
        form_field_choices=None,
        query_type="enum",
    ),
    "android_hardware": text_field(
        "android_hardware", data_validation_type="enum", query_type="enum"
    ),
    "android_manufacturer": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "android_manufacturer",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_manufacturer",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "android_model": text_field("android_model"),
    "android_packagename": keyword_field(name="android_packagename"),
    "android_version": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "android_version",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_version",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "app_init_dlls": text_field(
        "app_init_dlls",
        has_full_version=False,
        storage_mapping={"analyzer": "semicolon_keywords", "fielddata": True},
    ),
    "app_notes": text_field("app_notes"),
    "async_shutdown_timeout": text_field("async_shutdown_timeout"),
    "available_page_file": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "available_page_file",
        "is_exposed": True,
        "is_returned": True,
        "name": "available_page_file",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "available_physical_memory": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "available_physical_memory",
        "is_exposed": True,
        "is_returned": True,
        "name": "available_physical_memory",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "available_virtual_memory": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "available_virtual_memory",
        "is_exposed": True,
        "is_returned": True,
        "name": "available_virtual_memory",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "background_task_name": keyword_field(name="background_task_name"),
    "build_id": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "build",
        "is_exposed": True,
        "is_returned": True,
        "name": "build_id",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "co_marshal_interface_failure": text_field(
        "co_marshal_interface_failure", data_validation_type="enum", query_type="enum"
    ),
    "collector_notes": text_field(
        "collector_notes",
        source_key="processed_crash.collector_metadata.collector_notes",
    ),
    # FIXME(willkg): We have this indexed as an integer, but the annotation is listed as
    # a string. The actual value is an int converted to a string so in indexing we
    # convert that to an integer and that's why this works at all. However, I think this
    # should match the annotation and be a string and we should fix that somehow some
    # day.
    "content_sandbox_capabilities": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "content_sandbox_capabilities",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_capabilities",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "integer"},
    },
    "content_sandbox_capable": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "content_sandbox_capable",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_capable",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "content_sandbox_enabled": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "content_sandbox_enabled",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_enabled",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "content_sandbox_level": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "content_sandbox_level",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_level",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "short"},
    },
    "cpu_arch": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "cpu_arch",
        "is_exposed": True,
        "is_returned": True,
        "name": "cpu_arch",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "cpu_count": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "cpu_count",
        "is_exposed": True,
        "is_returned": True,
        "name": "cpu_count",
        "namespace": "processed_crash",
        # FIXME(willkg): We can stop pulling from the old location in 12/2022
        "source_key": "processed_crash.json_dump.system_info.cpu_count",
        "destination_keys": [
            "processed_crash.json_dump.system_info.cpu_count",
            "processed_crash.cpu_count",
        ],
        "query_type": "integer",
        "storage_mapping": {"type": "short"},
    },
    "cpu_info": text_field("cpu_info"),
    "cpu_microcode_version": text_field(
        "cpu_microcode_version", data_validation_type="enum", query_type="enum"
    ),
    "crash_inconsistencies": keyword_field(
        name="crash_inconsistencies",
    ),
    "crashing_thread": integer_field(name="crashing_thread"),
    "crashing_thread_name": keyword_field(
        "crashing_thread_name",
        in_database_name="crashing_thread_name",
    ),
    "date": {
        "data_validation_type": "datetime",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "date_processed",
        "is_exposed": True,
        "is_returned": True,
        "name": "date",
        "namespace": "processed_crash",
        "query_type": "date",
        "storage_mapping": {
            "format": "yyyy-MM-dd'T'HH:mm:ssZZZZZ||yyyy-MM-dd'T'HH:mm:ss.SSSSSSZZZZZ",
            "type": "date",
        },
    },
    "distribution_id": keyword_field(
        name="distribution_id",
    ),
    "dom_fission_enabled": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "dom_fission_enabled",
        "is_exposed": True,
        "is_returned": True,
        "name": "dom_fission_enabled",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "dom_ipc_enabled": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "dom_ipc_enabled",
        "is_exposed": True,
        "is_returned": True,
        "name": "dom_ipc_enabled",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "dumper_error": text_field("dumper_error"),
    "em_check_compatibility": {
        "data_validation_type": "bool",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "em_check_compatibility",
        "is_exposed": True,
        "is_returned": True,
        "name": "em_check_compatibility",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "gmp_library_path": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "gmp_library_path",
        "is_exposed": True,
        "is_returned": True,
        "name": "gmp_library_path",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "gmp_plugin": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "gmp_plugin",
        "is_exposed": True,
        "is_returned": True,
        "name": "gmp_plugin",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "graphics_critical_error": text_field("graphics_critical_error"),
    "graphics_startup_test": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "graphics_startup_test",
        "is_exposed": True,
        "is_returned": True,
        "name": "graphics_startup_test",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "hang": keyword_field(name="hang"),
    "has_device_touch_screen": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "has_device_touch_screen",
        "is_exposed": True,
        "is_returned": True,
        "name": "has_device_touch_screen",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "has_guard_page_access": boolean_field(name="has_guard_page_access"),
    "has_mac_boot_args": boolean_field(name="has_mac_boot_args"),
    "install_age": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "install_age",
        "is_exposed": True,
        "is_returned": True,
        "name": "install_age",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "install_time": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "install_time",
        "is_exposed": True,
        "is_returned": True,
        "name": "install_time",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "ipc_channel_error": text_field("ipc_channel_error"),
    "ipc_fatal_error_msg": text_field("ipc_fatal_error_msg"),
    "ipc_fatal_error_protocol": text_field("ipc_fatal_error_protocol"),
    "ipc_message_name": text_field("ipc_message_name"),
    "ipc_message_size": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ipc_message_size",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_message_size",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "ipc_shutdown_state": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ipc_shutdown_state",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_shutdown_state",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "ipc_system_error": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ipc_system_error",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_system_error",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "integer"},
    },
    "is_garbage_collecting": {
        "data_validation_type": "bool",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "is_garbage_collecting",
        "is_exposed": True,
        "is_returned": True,
        "name": "is_garbage_collecting",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "java_stack_trace": text_field("java_stack_trace"),
    "java_stack_trace_raw": text_field("java_stack_trace_raw"),
    "js_large_allocation_failure": keyword_field(name="js_large_allocation_failure"),
    "last_crash": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "last_crash",
        "is_exposed": True,
        "is_returned": True,
        "name": "last_crash",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "last_error_value": keyword_field("last_error_value"),
    "mac_boot_args": text_field("mac_boot_args"),
    "mac_crash_info": text_field("mac_crash_info"),
    "mac_available_memory_sysctl": integer_field(name="mac_available_memory_sysctl"),
    "mac_memory_pressure": keyword_field(
        name="mac_memory_pressure",
        choices=["Normal", "Unset", "Warning", "Critical", "Unexpected"],
    ),
    "mac_memory_pressure_sysctl": integer_field(name="mac_memory_pressure_sysctl"),
    "major_version": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "major_version",
        "is_exposed": True,
        "is_returned": True,
        "name": "major_version",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "integer"},
    },
    "memory_explicit": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "explicit",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_explicit",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_gfx_textures": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "gfx_textures",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_gfx_textures",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_ghost_windows": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ghost_windows",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_ghost_windows",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_heap_allocated": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "heap_allocated",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_heap_allocated",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_heap_overhead": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "heap_overhead",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_heap_overhead",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_heap_unclassified": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "heap_unclassified",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_heap_unclassified",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_host_object_urls": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "host_object_urls",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_host_object_urls",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_images": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "images",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_images",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_js_main_runtime": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "js_main_runtime",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_js_main_runtime",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_private": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "private",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_private",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_resident": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "resident",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_resident",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_resident_unique": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "resident_unique",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_resident_unique",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_system_heap_allocated": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "system_heap_allocated",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_system_heap_allocated",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_top_none_detached": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "top_none_detached",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_top_none_detached",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_vsize": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "vsize",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_vsize",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "memory_vsize_max_contiguous": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "vsize_max_contiguous",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_vsize_max_contiguous",
        "namespace": "processed_crash.memory_measures",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "minidump_sha256_hash": text_field("minidump_sha256_hash"),
    "missing_symbols": text_field(
        "missing_symbols",
        has_full_version=False,
        storage_mapping={"analyzer": "semicolon_keywords", "fielddata": True},
    ),
    "modules_in_stack": text_field(
        "modules_in_stack",
        has_full_version=False,
        storage_mapping={"analyzer": "semicolon_keywords", "fielddata": True},
    ),
    "moz_crash_reason": text_field("moz_crash_reason"),
    "moz_crash_reason_raw": text_field("moz_crash_reason_raw"),
    "oom_allocation_size": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "oom_allocation_size",
        "is_exposed": True,
        "is_returned": True,
        "name": "oom_allocation_size",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "platform": text_field(
        "platform",
        data_validation_type="enum",
        in_database_name="os_name",
        query_type="enum",
    ),
    "platform_pretty_version": text_field(
        "platform_pretty_version", in_database_name="os_pretty_version"
    ),
    "platform_version": text_field("platform_version", in_database_name="os_version"),
    "plugin_filename": text_field(
        "plugin_filename", data_validation_type="enum", query_type="enum"
    ),
    "plugin_name": text_field(
        "plugin_name", data_validation_type="enum", query_type="enum"
    ),
    "plugin_version": text_field(
        "plugin_version", data_validation_type="enum", query_type="enum"
    ),
    "possible_bit_flips_max_confidence": integer_field(
        name="possible_bit_flips_max_confidence",
    ),
    "process_type": {
        "data_validation_type": "str",
        "form_field_choices": [
            "any",
            "parent",
            "plugin",
            "content",
            "gpu",
            "all",
        ],
        "has_full_version": False,
        "in_database_name": "process_type",
        "is_exposed": True,
        "is_returned": True,
        "name": "process_type",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {
            "type": "keyword",
        },
    },
    "processor_notes": text_field("processor_notes"),
    "product": text_field("product", data_validation_type="enum", query_type="enum"),
    "productid": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "productid",
        "is_exposed": True,
        "is_returned": True,
        "name": "productid",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "proto_signature": text_field("proto_signature"),
    "quota_manager_shutdown_timeout": text_field("quota_manager_shutdown_timeout"),
    "reason": text_field("reason"),
    "release_channel": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "release_channel",
        "is_exposed": True,
        "is_returned": True,
        "name": "release_channel",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "remote_type": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "remote_type",
        "is_exposed": True,
        "is_returned": True,
        "name": "remote_type",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "report_type": keyword_field(name="report_type"),
    "safe_mode": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "safe_mode",
        "is_exposed": True,
        "is_returned": True,
        "name": "safe_mode",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "shutdown_progress": text_field("shutdown_progress"),
    "shutdown_reason": keyword_field(name="shutdown_reason"),
    "signature": text_field("signature"),
    "stackwalk_version": keyword_field(
        name="stackwalk_version",
        namespace="processed_crash",
    ),
    "startup_crash": {
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "startup_crash",
        "is_exposed": True,
        "is_returned": True,
        "name": "startup_crash",
        "namespace": "processed_crash",
        "query_type": "bool",
        # NOTE(willkg): startup_crash is used in signature report in some interesting
        # ways so I think we need to have both T and F values in ES
        "storage_mapping": {"null_value": False, "type": "boolean"},
    },
    "startup_time": {
        "data_validation_type": "int",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "startup_time",
        "is_exposed": True,
        "is_returned": True,
        "name": "startup_time",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "submitted_from": keyword_field(name="submitted_from"),
    "system_memory_use_percentage": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "system_memory_use_percentage",
        "is_exposed": True,
        "is_returned": True,
        "name": "system_memory_use_percentage",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "throttleable": {
        "data_validation_type": "bool",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "throttleable",
        "is_exposed": True,
        "is_returned": True,
        "name": "throttleable",
        "namespace": "processed_crash",
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "topmost_filenames": text_field(
        "topmost_filenames",
        has_full_version=False,
        storage_mapping={"analyzer": "semicolon_keywords", "fielddata": True},
    ),
    "total_page_file": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "total_page_file",
        "is_exposed": True,
        "is_returned": True,
        "name": "total_page_file",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "total_physical_memory": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "total_physical_memory",
        "is_exposed": True,
        "is_returned": True,
        "name": "total_physical_memory",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "total_virtual_memory": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "total_virtual_memory",
        "is_exposed": True,
        "is_returned": True,
        "name": "total_virtual_memory",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "uptime": {
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "uptime",
        "is_exposed": True,
        "is_returned": True,
        "name": "uptime",
        "namespace": "processed_crash",
        "query_type": "integer",
        "storage_mapping": {"type": "long"},
    },
    "uptime_ts": float_field(name="uptime_ts"),
    "url": {
        "data_validation_type": "str",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "url",
        "is_exposed": True,
        "is_returned": True,
        "name": "url",
        "namespace": "processed_crash",
        "query_type": "string",
        "storage_mapping": {"type": "keyword"},
    },
    "user_comments": text_field("user_comments"),
    "useragent_locale": text_field(
        "useragent_locale",
        data_validation_type="enum",
        has_full_version=False,
        query_type="enum",
        storage_mapping={"analyzer": "semicolon_keywords", "fielddata": True},
    ),
    "utility_actors_name": keyword_field(name="utility_actors_name"),
    "utility_process_sandboxing_kind": integer_field(
        name="utility_process_sandboxing_kind"
    ),
    "uuid": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "uuid",
        "is_exposed": True,
        "is_returned": True,
        "name": "uuid",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "vendor": text_field(
        "vendor",
        data_validation_type="enum",
        form_field_choices=None,
        query_type="enum",
    ),
    "version": {
        "data_validation_type": "enum",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "version",
        "is_exposed": True,
        "is_returned": True,
        "name": "version",
        "namespace": "processed_crash",
        "query_type": "enum",
        "storage_mapping": {"type": "keyword"},
    },
    "windows_error_reporting": boolean_field(
        name="windows_error_reporting",
    ),
    "xpcom_spin_event_loop_stack": keyword_field(
        name="xpcom_spin_event_loop_stack",
    ),
}


FIELDS = apply_schema_properties(FIELDS, schema=PROCESSED_CRASH_SCHEMA)

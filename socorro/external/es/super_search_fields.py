# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
import datetime
import logging

from configman import class_converter, Namespace, RequiredConfig
import elasticsearch
from elasticsearch_dsl import Search

from socorro.external.es.base import generate_list_of_indexes
from socorro.lib import datetimeutil, BadArgumentError


logger = logging.getLogger(__name__)


# The number of crash reports to test against when attempting to validate a new
# Elasticsearch mapping.
MAPPING_TEST_CRASH_NUMBER = 100


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


def build_mapping(doctype, fields=None):
    """Generates Elasticsearch mapping from the super search fields schema

    :arg str doctype: the doctype to use
    :arg any fields: map of field name -> field value; defaults to FIELDS

    :returns: dict of doctype -> Elasticsearch mapping

    """
    fields = fields or FIELDS
    properties = {}

    for field in fields.values():
        if not field.get("storage_mapping"):
            continue

        add_doc_values(field["storage_mapping"])

        destination_keys = get_destination_keys(field)
        for destination_key in destination_keys:
            key_parts = destination_key.split(".")
            add_field_to_properties(properties, key_parts, field)

    mapping = {
        doctype: {
            "_all": {"enabled": False},
            "_source": {"compress": True},
            "properties": properties,
        }
    }
    return mapping


def is_doc_values_friendly(field_value):
    """Predicate denoting whether this field should have doc_values added

    ``doc_values=True`` is a thing we can add to certain fields to reduce the
    memory they use in Elasticsearch.

    This predicate determines whether we should add it or not for a given
    field.

    :arg field_value: a field value from super search fields

    :returns: True if ``doc_values=True` should be added; False otherwise

    """
    field_type = field_value.get("type")

    # No clue what type this is--probably false
    if not field_type:
        return False

    # object, and multi_fields fields don't work with doc_values=True
    if field_type in ("object", "multi_field"):
        return False

    # analyzed string fields don't work with doc_values=True
    if field_type == "string" and field_value.get("index") != "not_analyzed":
        return False

    # Everything is fine! Yay!
    return True


def add_doc_values(value):
    """Add "doc_values": True to storage mapping of field value

    NOTE(willkg): Elasticsearch 2.0+ does this automatically, so we
    can nix this when we upgrade.

    Note: This makes changes in-place and recurses on the structure
    of value.

    :arg value: the storage mapping of a field value

    """
    if is_doc_values_friendly(value):
        value["doc_values"] = True

    # Handle subfields
    if value.get("fields"):
        for field in value.get("fields", {}).values():
            add_doc_values(field)

    # Handle objects with nested properties
    if value.get("properties"):
        for field in value["properties"].values():
            add_doc_values(field)


class SuperSearchFieldsData:
    """Data class for super search fields.

    This just holds the FIELDS and some accessors to get them.

    """

    def get_fields(self):
        """Return all the fields from our super_search_fields.json file."""
        return FIELDS

    # Alias ``get`` as ``get_fields`` so this can be used in the API well and
    # can be conveniently subclassed by ``SuperSearchMissingFields``.
    get = get_fields


@dataclass
class IndexDataItem:
    name: str
    start_date: datetime.datetime
    count: int


class SuperSearchFields(SuperSearchFieldsData):
    def __init__(self, context):
        self.context = context

    def get_connection(self):
        with self.context() as conn:
            return conn

    def get_supersearch_status(self):
        """Return list of indices, latest index, and mapping.

        :returns: list of IndexDataItem instances

        """
        conn = self.get_connection()
        index_client = elasticsearch.client.IndicesClient(conn)
        indices = sorted(self.context.get_indices())
        latest_index = indices[-1]

        doctype = self.context.get_doctype()
        index_template = self.context.get_index_template()
        if index_template.endswith("%Y%W"):
            # Doing strptime on a template that has %W but doesn't have a day-of-week,
            # will ignore the %W part; so we anchor it with 1 (Monday)
            add_day_of_week = True
            index_template = f"{index_template}%w"
        else:
            add_day_of_week = False

        index_data = []
        for index_name in indices:
            count = Search(using=conn, index=index_name, doc_type=doctype).count()

            if add_day_of_week:
                # %W starts on Mondays, so we set the day-of-week to 1 which is
                # Monday
                adjusted_index_name = f"{index_name}1"
            else:
                adjusted_index_name = index_name
            start_date = datetime.datetime.strptime(adjusted_index_name, index_template)
            start_date = start_date.date()

            index_data.append(
                IndexDataItem(
                    name=index_name,
                    start_date=start_date,
                    count=count,
                )
            )

        mapping = index_client.get_mapping(index=latest_index)
        mapping_properties = mapping[latest_index]["mappings"][doctype]["properties"]

        return {
            "indices": index_data,
            "latest_index": latest_index,
            "mapping": mapping_properties,
        }

    def get_missing_fields(self):
        """Return fields missing from our FIELDS list

        Go through the last three weeks of indexes, fetch the mappings, and
        figure out which fields are in the mapping that aren't in our list of
        known fields.

        :returns: dict of missing fields (``hits``) and total number of missing
            fields (``total``)

        """
        now = datetimeutil.utc_now()
        two_weeks_ago = now - datetime.timedelta(weeks=2)
        index_template = self.context.get_index_template()
        indices = generate_list_of_indexes(two_weeks_ago, now, index_template)

        es_connection = self.get_connection()
        index_client = elasticsearch.client.IndicesClient(es_connection)
        doctype = self.context.get_doctype()

        all_existing_fields = set()
        for index in indices:
            try:
                mapping = index_client.get_mapping(index=index)
                properties = mapping[index]["mappings"][doctype]["properties"]
                all_existing_fields.update(parse_mapping(properties, None))
            except elasticsearch.exceptions.NotFoundError as e:
                # If an index does not exist, this should not fail
                logger.warning(
                    "Missing index in elasticsearch while running "
                    "SuperSearchFields.get_missing_fields, error is: %s",
                    str(e),
                )

        all_known_fields = {
            ".".join((x["namespace"], x["in_database_name"]))
            for x in self.get_fields().values()
        }

        missing_fields = sorted(all_existing_fields - all_known_fields)

        return {"hits": missing_fields, "total": len(missing_fields)}

    def test_mapping(self, mapping):
        """Verify that a mapping is correct

        This method verifies a mapping by creating a new, temporary index in
        elasticsearch using the mapping. It then takes some recent crash
        reports that are in elasticsearch and tries to insert them in the
        temporary index. Any failure in any of those steps will raise an
        exception. If any is raised, that means the mapping is incorrect in
        some way (either it doesn't validate against elasticsearch's rules, or
        is not compatible with the data we currently store).

        Raises an exception if the mapping is bad.

        Use this to test any mapping changes.

        :arg mapping: the Elasticsearch mapping to test

        """
        temp_index = "socorro_mapping_test"

        es_connection = self.get_connection()

        try:
            self.context.create_index(temp_index, mappings=mapping)

            now = datetimeutil.utc_now()
            last_week = now - datetime.timedelta(days=7)
            index_template = self.context.get_index_template()
            current_indices = generate_list_of_indexes(last_week, now, index_template)

            crashes_sample = es_connection.search(
                index=current_indices,
                doc_type=self.context.get_doctype(),
                size=MAPPING_TEST_CRASH_NUMBER,
            )
            crashes = [x["_source"] for x in crashes_sample["hits"]["hits"]]

            for crash in crashes:
                es_connection.index(
                    index=temp_index, doc_type=self.context.get_doctype(), body=crash
                )
        except elasticsearch.exceptions.ElasticsearchException as e:
            raise BadArgumentError(
                "storage_mapping",
                msg=(
                    "Indexing existing data in Elasticsearch failed with the "
                    "new mapping. Error is: %s" % str(e)
                ),
            )
        finally:
            try:
                self.context.indices_client().delete(temp_index)
            except elasticsearch.exceptions.NotFoundError:
                # If the index does not exist (if the index creation failed
                # for example), we don't need to do anything.
                pass


class SuperSearchFieldsModel(RequiredConfig, SuperSearchFields):
    """Model for accessing super search fields."""

    # Defining some filters that need to be considered as lists.
    filters = [
        ("form_field_choices", None, ["list", "str"]),
        ("permissions_needed", None, ["list", "str"]),
    ]

    required_config = Namespace()
    required_config.add_option(
        "elasticsearch_class",
        doc="a class that implements the ES connection object",
        default="socorro.external.es.connection_context.ConnectionContext",
        from_string_converter=class_converter,
    )

    def __init__(self, config):
        # NOTE(willkg): This doesn't call the super().__init__ but instead
        # sets everything up itself.
        self.config = config
        self.context = self.config.elasticsearch_class(self.config)


class SuperSearchMissingFieldsModel(SuperSearchFieldsModel):
    """Model that returns fields missing from super search fields."""

    def get(self):
        return super().get_missing_fields()


class SuperSearchStatusModel(SuperSearchFieldsModel):
    """Model that returns list of indices and latest mapping."""

    def get(self):
        return super().get_supersearch_status()


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
    try:
        return _FIELDS_CACHE[map_key]
    except KeyError:
        pass

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


def flag_field(
    name,
    description,
    namespace="processed_crash",
    in_database_name="",
    is_protected=True,
):
    """Generates a flag field.

    Flag fields are one of a few things:

    1. a boolean value that is either true and false
    2. a crash annotation flag that is "1" or missing

    These can be searched and aggregated, but documents that are missing the field won't
    show up in aggregations.

    :param name: the name used to query the field in super search
    :param description: the description of this field; if this is a crash annotation,
        you can copy the annotation description
    :param namespace: either "raw_crash" or "processed_crash"; note that we're moving
        to a model where we pull everything from the processed_crash, so prefer that
    :param in_database_name: the field in the processed crash to pull this data from
    :param is_protected: whether or not this is protected data

    :returns: super search field specification as a dict

    """
    if is_protected:
        permissions_needed = ["crashstats.view_pii"]
    else:
        permissions_needed = []

    in_database_name = in_database_name or name

    return {
        "name": name,
        "description": description,
        "data_validation_type": "bool",
        "form_field_choices": [],
        "has_full_version": False,
        "namespace": namespace,
        "in_database_name": in_database_name,
        "is_exposed": True,
        "is_returned": True,
        "query_type": "bool",
        "permissions_needed": permissions_needed,
        "storage_mapping": {"type": "boolean"},
    }


def keyword_field(
    name,
    description,
    namespace="processed_crash",
    in_database_name="",
    choices=None,
    is_protected=True,
):
    """Generates a keyword field.

    Keyword field values are analyzed as a single token. This is good for ids, product
    names, fields that have a limited set of choices, etc.

    :param name: the name used to query the field in super search
    :param description: the description of this field; if this is a crash annotation,
        you can copy the annotation description
    :param namespace: either "raw_crash" or "processed_crash"; note that we're moving
        to a model where we pull everything from the processed_crash, so prefer that
    :param in_database_name: the field in the processed crash to pull this data from
    :param choices: a list of valid values for the dropdown
    :param is_protected: whether or not this is protected data

    :returns: super search field specification as a dict

    """

    if is_protected:
        permissions_needed = ["crashstats.view_pii"]
    else:
        permissions_needed = []

    in_database_name = in_database_name or name

    choices = choices or []

    return {
        "name": name,
        "description": description,
        "data_validation_type": "str",
        "form_field_choices": choices,
        "has_full_version": False,
        "namespace": namespace,
        "in_database_name": in_database_name,
        "is_exposed": True,
        "is_returned": True,
        "permissions_needed": permissions_needed,
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    }


def number_field(
    name,
    description,
    namespace="processed_crash",
    in_database_name="",
    number_type="integer",
    is_protected=True,
):
    """Generates a numeric field.

    :param name: the name used to query the field in super search
    :param description: the description of this field; if this is a crash annotation,
        you can copy the annotation description
    :param namespace: either "raw_crash" or "processed_crash"; note that we're moving
        to a model where we pull everything from the processed_crash, so prefer that
    :param in_database_name: the field in the processed crash to pull this data from
    :param number_type: "short", "integer", "long", "double"
    :param is_protected: whether or not this is protected data

    :returns: super search field specification as a dict

    """
    if is_protected:
        permissions_needed = ["crashstats.view_pii"]
    else:
        permissions_needed = []

    in_database_name = in_database_name or name

    if number_type not in ["short", "integer", "long", "double"]:
        raise ValueError(f"number_type {number_type} is not valid")

    return {
        "name": name,
        "description": description,
        "data_validation_type": "int",
        "form_field_choices": [],
        "has_full_version": False,
        "namespace": namespace,
        "in_database_name": in_database_name,
        "is_exposed": True,
        "is_returned": True,
        "query_type": "number",
        "permissions_needed": permissions_needed,
        "storage_mapping": {"type": number_type},
    }


# Tree of super search fields
FIELDS = {
    "application_build_id": {
        "data_validation_type": "int",
        "description": "Product application's build ID.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "application_build_id",
        "is_exposed": True,
        "is_returned": True,
        "name": "application_build_id",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "crash_report_keys": keyword_field(
        name="crash_report_keys",
        description="Crash annotation keys and dump filenames from the crash report.",
        is_protected=False,
    ),
    "phc_kind": {
        "data_validation_type": "str",
        "description": (
            "The allocation kind, if the crash involved a bad access of a special PHC "
            "allocation."
        ),
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "phc_kind",
        "is_exposed": True,
        "is_returned": True,
        "name": "phc_kind",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "phc_base_address": {
        "data_validation_type": "str",
        "description": (
            "The allocation's base address, if the crash involved a bad access of a "
            "special PHC allocation. Encoded as a decimal address."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "phc_base_address",
        "is_exposed": True,
        "is_returned": True,
        "name": "phc_base_address",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "phc_usable_size": {
        "data_validation_type": "int",
        "description": (
            "The allocation's usable size, if the crash involved a bad access of a "
            "special PHC allocation."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "phc_usable_size",
        "is_exposed": True,
        "is_returned": True,
        "name": "phc_usable_size",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "phc_alloc_stack": {
        "data_validation_type": "str",
        "description": (
            "The allocation's allocation stack trace, if the crash involved a bad "
            "access of a special PHC allocation. Encoded as a comma-separated list "
            "of decimal addresses."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "phc_alloc_stack",
        "is_exposed": True,
        "is_returned": True,
        "name": "phc_alloc_stack",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "phc_free_stack": {
        "data_validation_type": "str",
        "description": (
            "The allocation's free stack trace, if the crash involved a bad access "
            "of a special PHC allocation. Encoded as a comma-separated list of decimal "
            "addresses."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "phc_free_stack",
        "is_exposed": True,
        "is_returned": True,
        "name": "phc_free_stack",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "abort_message": {
        "data_validation_type": "str",
        "description": "The abort message.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "AbortMessage",
        "is_exposed": True,
        "is_returned": True,
        "name": "abort_message",
        "namespace": "raw_crash",
        "permissions_needed": [],
        # FIXME(willkg): 7/14 change this to save to the processed_crash
        "source_key": "processed_crash.abort_message",
        "destination_keys": [
            "raw_crash.AbortMessage",
            "processed_crash.abort_message",
        ],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "accessibility": {
        "data_validation_type": "bool",
        "description": (
            "The presence of this field indicates that accessibility services were accessed."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Accessibility",
        "is_exposed": True,
        "is_returned": True,
        "name": "accessibility",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "accessibility_client": {
        "data_validation_type": "str",
        "description": "Out-of-process accessibility client program name and version information.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AccessibilityClient",
        "is_exposed": True,
        "is_returned": True,
        "name": "accessibility_client",
        "namespace": "raw_crash",
        "permissions_needed": [],
        # FIXME(willkg): 7/14 change this to save to the processed_crash
        "source_key": "processed_crash.accessibility_client",
        "destination_keys": [
            "raw_crash.AccessibilityClient",
            "processed_crash.accessibility_client",
        ],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "accessibility_in_proc_client": {
        "data_validation_type": "str",
        "description": (
            "In-process accessibility client detection information. See Compatibility.h for more "
            "details."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AccessibilityInProcClient",
        "is_exposed": True,
        "is_returned": True,
        "name": "accessibility_in_proc_client",
        "namespace": "raw_crash",
        "permissions_needed": [],
        # FIXME(willkg): 7/14 change this to save to the processed_crash
        "source_key": "processed_crash.accessibility_in_proc_client",
        "destination_keys": [
            "raw_crash.AccessibilityInProcClient",
            "processed_crash.accessibility_in_proc_client",
        ],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "adapter_device_id": {
        "data_validation_type": "str",
        "description": "The graphics adapter device identifier.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AdapterDeviceID",
        "is_exposed": True,
        "is_returned": True,
        "name": "adapter_device_id",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.adapter_device_id",
        "destination_keys": [
            "raw_crash.AdapterDeviceID",
            "processed_crash.adapter_device_id",
        ],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "adapter_driver_version": {
        "data_validation_type": "str",
        "description": "The graphics adapter driver version.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AdapterDriverVersion",
        "is_exposed": True,
        "is_returned": True,
        "name": "adapter_driver_version",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.adapter_driver_version",
        "destination_keys": [
            "raw_crash.AdapterDriverVersion",
            "processed_crash.adapter_driver_version",
        ],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "adapter_subsys_id": {
        "data_validation_type": "str",
        "description": "The graphics adapter subsystem identifier.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AdapterSubsysID",
        "is_exposed": True,
        "is_returned": True,
        "name": "adapter_subsys_id",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.adapter_subsys_id",
        "destination_keys": [
            "raw_crash.AdapterSubsysID",
            "processed_crash.adapter_subsys_id",
        ],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "adapter_vendor_id": {
        "data_validation_type": "str",
        "description": (
            "The graphics adapter vendor. This value is sometimes a name, and sometimes a "
            "hexidecimal identifier. Common identifiers include: 0x8086 (Intel), 0x1002 (AMD), "
            "0x10de (NVIDIA)."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AdapterVendorID",
        "is_exposed": True,
        "is_returned": True,
        "name": "adapter_vendor_id",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.adapter_vendor_id",
        "destination_keys": [
            "raw_crash.AdapterVendorID",
            "processed_crash.adapter_vendor_id",
        ],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "addons": {
        "data_validation_type": "str",
        "description": (
            "A list of the addons currently enabled at the time of the crash. This takes the form "
            'of "addonid:version,[addonid:version...]". This value could be empty if the crash '
            "happens during startup before the addon manager is enabled, and on products/platforms "
            "which do not support addons."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "addons",
        "is_exposed": True,
        "is_returned": True,
        "name": "addons",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "addons_checked": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "addons_checked",
        "is_exposed": True,
        "is_returned": True,
        "name": "addons_checked",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"type": "boolean"},
    },
    "address": {
        "data_validation_type": "str",
        "description": (
            "The crashing address. This value is only meaningful for crashes involving bad memory "
            "accesses."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "address",
        "is_exposed": True,
        "is_returned": True,
        "name": "address",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "android_board": {
        "data_validation_type": "enum",
        "description": "The board used by the Android device.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_Board",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_board",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_board",
        "destination_keys": [
            "raw_crash.Android_Board",
            "processed_crash.android_board",
        ],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "android_brand": {
        "data_validation_type": "enum",
        "description": "The Android device brand.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_Brand",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_brand",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_brand",
        "destination_keys": [
            "raw_crash.Android_Brand",
            "processed_crash.android_brand",
        ],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "android_cpu_abi": {
        "data_validation_type": "enum",
        "description": "The Android primary CPU ABI being used.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_CPU_ABI",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_cpu_abi",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_cpu_abi",
        "destination_keys": [
            "raw_crash.Android_CPU_ABI",
            "processed_crash.android_cpu_abi",
        ],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "android_cpu_abi2": {
        "data_validation_type": "enum",
        "description": "The Android secondary CPU ABI being used.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_CPU_ABI2",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_cpu_abi2",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_cpu_abi2",
        "destination_keys": [
            "raw_crash.Android_CPU_ABI2",
            "processed_crash.android_cpu_abi2",
        ],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "android_device": {
        "data_validation_type": "enum",
        "description": "The android device name.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_Device",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_device",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_device",
        "destination_keys": [
            "raw_crash.Android_Device",
            "processed_crash.android_device",
        ],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "android_display": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "Android_Display",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_display",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_display",
        "destination_keys": [
            "raw_crash.Android_Display",
            "processed_crash.android_display",
        ],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "android_fingerprint": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "Android_Fingerprint",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_fingerprint",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_fingerprint",
        "destination_keys": [
            "raw_crash.Android_Fingerprint",
            "processed_crash.android_fingerprint",
        ],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "android_hardware": {
        "data_validation_type": "enum",
        "description": "The android device hardware.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_Hardware",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_hardware",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_hardware",
        "destination_keys": [
            "raw_crash.Android_Hardware",
            "processed_crash.android_hardware",
        ],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "android_manufacturer": {
        "data_validation_type": "enum",
        "description": "The Android device manufacturer.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_Manufacturer",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_manufacturer",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_manufacturer",
        "destination_keys": [
            "raw_crash.Android_Manufacturer",
            "processed_crash.android_manufacturer",
        ],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "android_model": {
        "data_validation_type": "str",
        "description": "The Android device model name.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "Android_Model",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_model",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_model",
        "destination_keys": [
            "raw_crash.Android_Model",
            "processed_crash.android_model",
        ],
        "query_type": "string",
        "storage_mapping": {
            "fields": {
                "Android_Model": {"type": "string"},
                "full": {"index": "not_analyzed", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "android_version": {
        "data_validation_type": "str",
        "description": "The Android version.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "Android_Version",
        "is_exposed": True,
        "is_returned": True,
        "name": "android_version",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.android_version",
        "destination_keys": [
            "raw_crash.Android_Version",
            "processed_crash.android_version",
        ],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "app_init_dlls": {
        "data_validation_type": "str",
        "description": "DLLs injected through the AppInit_DLLs registry key.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AppInitDLLs",
        "is_exposed": True,
        "is_returned": True,
        "name": "app_init_dlls",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.app_init_dlls",
        "destination_keys": [
            "raw_crash.AppInitDLLs",
            "processed_crash.app_init_dlls",
        ],
        "query_type": "string",
        "storage_mapping": {"analyzer": "semicolon_keywords", "type": "string"},
    },
    "app_notes": {
        "data_validation_type": "str",
        "description": (
            "Notes from the application that crashed. Mostly contains graphics-related "
            "annotations."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "app_notes",
        "is_exposed": True,
        "is_returned": True,
        "name": "app_notes",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "async_shutdown_timeout": {
        "data_validation_type": "str",
        "description": "",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "AsyncShutdownTimeout",
        "is_exposed": True,
        "is_returned": True,
        "name": "async_shutdown_timeout",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.async_shutdown_timeout",
        "destination_keys": [
            "raw_crash.AsyncShutdownTimeout",
            "processed_crash.async_shutdown_timeout",
        ],
        "query_type": "string",
        "storage_mapping": {
            "fields": {
                "AsyncShutdownTimeout": {
                    "analyzer": "standard",
                    "index": "analyzed",
                    "type": "string",
                },
                "full": {"index": "not_analyzed", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "available_page_file": {
        "data_validation_type": "int",
        "description": (
            "The maximum amount of memory the current process can commit. This value is equal "
            "to or smaller than the system-wide available commit value."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AvailablePageFile",
        "is_exposed": True,
        "is_returned": True,
        "name": "available_page_file",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.available_page_file",
        "destination_keys": [
            "raw_crash.AvailablePageFile",
            "processed_crash.available_page_file",
        ],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "available_physical_memory": {
        "data_validation_type": "int",
        "description": (
            "The amount of physical memory currently available. This is the amount of physical "
            "memory that can be immediately reused without having to write its contents to disk "
            "first."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AvailablePhysicalMemory",
        "is_exposed": True,
        "is_returned": True,
        "name": "available_physical_memory",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.available_physical_memory",
        "destination_keys": [
            "raw_crash.AvailablePhysicalMemory",
            "processed_crash.available_physical_memory",
        ],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "available_virtual_memory": {
        "data_validation_type": "int",
        "description": (
            "The amount of unreserved and uncommited (i.e. available) memory in the process's "
            "address space. Note that this memory may be fragmented into many separate segments, "
            "so an allocation attempt may fail even when this value is substantially greater than "
            "zero."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "AvailableVirtualMemory",
        "is_exposed": True,
        "is_returned": True,
        "name": "available_virtual_memory",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.available_virtual_memory",
        "destination_keys": [
            "raw_crash.AvailableVirtualMemory",
            "processed_crash.available_virtual_memory",
        ],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "bios_manufacturer": {
        "data_validation_type": "enum",
        "description": "The BIOS manufacturer.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "BIOS_Manufacturer",
        "is_exposed": True,
        "is_returned": True,
        "name": "bios_manufacturer",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.bios_manufacturer",
        "destination_keys": [
            "raw_crash.BIOS_Manufacturer",
            "processed_crash.bios_manufacturer",
        ],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "build_id": {
        "data_validation_type": "int",
        "description": (
            "The unique build identifier of this version, which is a timestamp of the form "
            "YYYYMMDDHHMMSS."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "build",
        "is_exposed": True,
        "is_returned": True,
        "name": "build_id",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "co_marshal_interface_failure": {
        "data_validation_type": "enum",
        "description": (
            "Contains the hexadecimal value of the return code from Windows "
            "CoMarshalInterfaceFailure API when invoked by IPDL serialization and "
            "deserialization code."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "CoMarshalInterfaceFailure",
        "is_exposed": True,
        "is_returned": True,
        "name": "co_marshal_interface_failure",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.co_marshal_interface_failure",
        "destination_keys": [
            "raw_crash.CoMarshalInterfaceFailure",
            "processed_crash.co_marshal_interface_failure",
        ],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "collector_notes": {
        "data_validation_type": "str",
        "description": (
            "Notes of the Socorro collector, contains information about the report "
            "during collection."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "collector_notes",
        "is_exposed": True,
        "is_returned": True,
        "name": "collector_notes",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "contains_memory_report": {
        "data_validation_type": "str",
        "description": "Has content for processed_crash.memory_report or not.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ContainsMemoryReport",
        "is_exposed": True,
        "is_returned": True,
        "name": "contains_memory_report",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "flag",
        "storage_mapping": {"type": "short"},
    },
    # FIXME(willkg): We have this indexed as an integer, but the annotation is listed as
    # a string. The actual value is an int converted to a string so in indexing we
    # convert that to an integer and that's why this works at all. However, I think this
    # should match the annotation and be a string and we should fix that somehow some
    # day.
    "content_sandbox_capabilities": {
        "data_validation_type": "int",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ContentSandboxCapabilities",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_capabilities",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.content_sandbox_capabilities",
        "destination_keys": [
            "raw_crash.ContentSandboxCapabilities",
            "processed_crash.content_sandbox_capabilities",
        ],
        "query_type": "number",
        "storage_mapping": {"type": "integer"},
    },
    "content_sandbox_capable": {
        "data_validation_type": "bool",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ContentSandboxCapable",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_capable",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"null_value": False, "type": "boolean"},
    },
    "content_sandbox_enabled": {
        "data_validation_type": "bool",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ContentSandboxEnabled",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_enabled",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"null_value": False, "type": "boolean"},
    },
    "content_sandbox_level": {
        "data_validation_type": "int",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ContentSandboxLevel",
        "is_exposed": True,
        "is_returned": True,
        "name": "content_sandbox_level",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.content_sandbox_level",
        "destination_keys": [
            "raw_crash.ContentSandboxLevel",
            "processed_crash.content_sandbox_level",
        ],
        "query_type": "number",
        "storage_mapping": {"type": "short"},
    },
    "cpu_arch": {
        "data_validation_type": "enum",
        "description": (
            'The build architecture. Usually one of: "x86", "amd64" (a.k.a. x86-64), "arm", '
            '"arm64".'
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "cpu_arch",
        "is_exposed": True,
        "is_returned": True,
        "name": "cpu_arch",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "cpu_count": {
        "data_validation_type": "int",
        "description": "Number of processor units in the CPU.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "cpu_count",
        "is_exposed": True,
        "is_returned": True,
        "name": "cpu_count",
        "namespace": "processed_crash.json_dump.system_info",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "short"},
    },
    "cpu_info": {
        "data_validation_type": "str",
        "description": (
            "Detailed processor info. Usually contains information such as the family, model, "
            "and stepping number."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "cpu_info",
        "is_exposed": True,
        "is_returned": True,
        "name": "cpu_info",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {
                "cpu_info": {
                    "analyzer": "standard",
                    "index": "analyzed",
                    "type": "string",
                },
                "full": {"index": "not_analyzed", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "cpu_microcode_version": {
        "data_validation_type": "enum",
        "description": "Microcode version of the CPU.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "CPUMicrocodeVersion",
        "is_exposed": True,
        "is_returned": True,
        "name": "cpu_microcode_version",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "source_key": "processed_crash.cpu_microcode_version",
        "destination_keys": [
            "raw_crash.CPUMicrocodeVersion",
            "processed_crash.cpu_microcode_version",
        ],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "date": {
        "data_validation_type": "datetime",
        "description": "Date at which the crash report was received by Socorro.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "date_processed",
        "is_exposed": True,
        "is_returned": True,
        "name": "date",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "date",
        "storage_mapping": {
            "format": "yyyy-MM-dd'T'HH:mm:ssZZ||yyyy-MM-dd'T'HH:mm:ss.SSSSSSZZ",
            "type": "date",
        },
    },
    "distribution_id": keyword_field(
        name="distribution_id",
        description=(
            "Product application's distribution ID. This is either the DistributionID "
            "annotation or the TelemetryEnvironment.partner.distributionId value."
        ),
        is_protected=False,
    ),
    "dom_fission_enabled": {
        "data_validation_type": "str",
        "description": (
            "Set to 1 when DOM fission is enabled, and subframes are potentially "
            "loaded in a separate process."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "DOMFissionEnabled",
        "is_exposed": True,
        "is_returned": True,
        "name": "dom_fission_enabled",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "flag",
        "storage_mapping": {"None_value": 0, "type": "short"},
    },
    "dom_ipc_enabled": {
        "data_validation_type": "str",
        "description": "Set to 1 when a tab is running in a content process.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "DOMIPCEnabled",
        "is_exposed": True,
        "is_returned": True,
        "name": "dom_ipc_enabled",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "flag",
        "storage_mapping": {"None_value": 0, "type": "short"},
    },
    "dumper_error": {
        "data_validation_type": "str",
        "description": (
            "Error message of the minidump writer, in case there was an error during dumping."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "dumper_error",
        "is_exposed": True,
        "is_returned": True,
        "name": "dumper_error",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {
            "fields": {
                "full": {"index": "not_analyzed", "type": "string"},
                "dumper_error": {
                    "type": "string",
                    "index": "analyzed",
                    "analyzer": "standard",
                },
            },
            "type": "multi_field",
        },
    },
    "em_check_compatibility": {
        "data_validation_type": "bool",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "EMCheckCompatibility",
        "is_exposed": True,
        "is_returned": True,
        "name": "em_check_compatibility",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "exploitability": {
        "data_validation_type": "enum",
        "description": "An automated estimate of how exploitable this crash is.",
        "form_field_choices": ["high", "normal", "low", "none", "unknown", "error"],
        "has_full_version": True,
        "in_database_name": "exploitability",
        "is_exposed": True,
        "is_returned": True,
        "name": "exploitability",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_exploitability"],
        "query_type": "enum",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "flash_version": {
        "data_validation_type": "enum",
        "description": "Version of the Flash Player plugin.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "flash_version",
        "is_exposed": True,
        "is_returned": True,
        "name": "flash_version",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "gmp_library_path": {
        "data_validation_type": "str",
        "description": "Holds the path to the GMP plugin library.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "GMPLibraryPath",
        "is_exposed": True,
        "is_returned": True,
        "name": "gmp_library_path",
        "namespace": "raw_crash",
        "permissions_needed": [
            # This contains file paths on the user's computer.
            "crashstats.view_pii"
        ],
        "source_key": "processed_crash.gmp_library_path",
        "destination_keys": [
            "raw_crash.GMPLibraryPath",
            "processed_crash.gmp_library_path",
        ],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "gmp_plugin": {
        "data_validation_type": "str",
        "description": "Whether it is a GMP plugin crash.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "GMPPlugin",
        "is_exposed": True,
        "is_returned": True,
        "name": "gmp_plugin",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "flag",
        "storage_mapping": {"type": "short"},
    },
    "graphics_critical_error": {
        "data_validation_type": "str",
        "description": "Log of graphics-related errors.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "GraphicsCriticalError",
        "is_exposed": True,
        "is_returned": True,
        "name": "graphics_critical_error",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "graphics_startup_test": {
        "data_validation_type": "str",
        "description": "Whether the crash occured in the DriverCrashGuard.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "GraphicsStartupTest",
        "is_exposed": True,
        "is_returned": True,
        "name": "graphics_startup_test",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "flag",
        "storage_mapping": {"type": "short"},
    },
    "hang_type": {
        "data_validation_type": "enum",
        "description": (
            "Tells if a report was caused by a crash or a hang. In the database, the value "
            "is `0` if the problem was a crash of the software, and `1` or `-1` if the problem "
            "was a hang of the software. \n\nNote: for querying, you should use `crash` or "
            "`hang`, since those are automatically transformed into the correct underlying "
            "values."
        ),
        "form_field_choices": ["any", "crash", "hang", "all"],
        "has_full_version": False,
        "in_database_name": "hang_type",
        "is_exposed": True,
        "is_returned": True,
        "name": "hang_type",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"type": "short"},
    },
    "has_device_touch_screen": {
        "data_validation_type": "bool",
        "description": (
            "Set to 1 if the device had a touch-screen, this only applies to Firefox "
            "desktop as on mobile devices we assume a touch-screen is always present."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "HasDeviceTouchScreen",
        "is_exposed": True,
        "is_returned": True,
        "name": "has_device_touch_screen",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "install_age": {
        "data_validation_type": "int",
        "description": "Length of time since this version was installed.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "install_age",
        "is_exposed": True,
        "is_returned": True,
        "name": "install_age",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "install_time": {
        "data_validation_type": "int",
        "description": (
            "Epoch time of when this version was installed. Commonly used as a unique "
            "identifier for software installations (since it is unlikely that two instances "
            "are installed at the very same second)."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "InstallTime",
        "is_exposed": True,
        "is_returned": True,
        "name": "install_time",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "ipc_channel_error": {
        "data_validation_type": "str",
        "description": "The IPC channel error.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ipc_channel_error",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_channel_error",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "ipc_fatal_error_msg": {
        "data_validation_type": "str",
        "description": "The message linked to an IPC fatal error.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "IPCFatalErrorMsg",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_fatal_error_msg",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "ipc_fatal_error_protocol": {
        "data_validation_type": "str",
        "description": "The protocol linked to an IPC fatal error.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "IPCFatalErrorProtocol",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_fatal_error_protocol",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "ipc_message_name": {
        "data_validation_type": "str",
        "description": "The name of the IPC message.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "IPCMessageName",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_message_name",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "ipc_message_size": {
        "data_validation_type": "int",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "IPCMessageSize",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_message_size",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "ipc_shutdown_state": {
        "data_validation_type": "enum",
        "description": (
            "Shows that a shutdown hang was after we have received RecvShutdown but never "
            "each SendFinishShutdown or the hang happened before or after RecvShutdown. "
            "https://bugzilla.mozilla.org/show_bug.cgi?id=1301339"
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "IPCShutdownState",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_shutdown_state",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "ipc_system_error": {
        "data_validation_type": "int",
        "description": (
            "A replacement of `system_error`. "
            "https://bugzilla.mozilla.org/show_bug.cgi?id=1267222"
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "IPCSystemError",
        "is_exposed": True,
        "is_returned": True,
        "name": "ipc_system_error",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "integer"},
    },
    "is_garbage_collecting": {
        "data_validation_type": "bool",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "IsGarbageCollecting",
        "is_exposed": True,
        "is_returned": True,
        "name": "is_garbage_collecting",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "java_stack_trace": {
        "data_validation_type": "str",
        "description": (
            "The unstructured JavaStackTrace crash annotation without the exception "
            "value which is protected data."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "java_stack_trace",
        "is_exposed": True,
        "is_returned": True,
        "name": "java_stack_trace",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "java_stack_trace_raw": {
        "data_validation_type": "str",
        "description": (
            "The raw unstructured JavaStackTrace crash annotation value. This is "
            "protected data."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "java_stack_trace_raw",
        "is_exposed": True,
        "is_returned": True,
        "name": "java_stack_trace_raw",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "last_crash": {
        "data_validation_type": "int",
        "description": (
            "Length of time between the previous crash submission and this one. Low values "
            "indicate repeated crashes."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "last_crash",
        "is_exposed": True,
        "is_returned": True,
        "name": "last_crash",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "mac_crash_info": {
        "data_validation_type": "str",
        "description": "macOS __crash_info data.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "mac_crash_info",
        "is_exposed": True,
        "is_returned": True,
        "name": "mac_crash_info",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "mac_available_memory_sysctl": number_field(
        name="mac_available_memory_sysctl",
        description=(
            "The value of the available memory sysctl 'kern.memorystatus_level'. "
            "Expected to be a percentage integer value."
        ),
        number_type="integer",
        is_protected=False,
    ),
    "mac_memory_pressure": keyword_field(
        name="mac_memory_pressure",
        description=(
            "The current memory pressure state as provided by the macOS memory "
            'pressure dispatch source. The annotation value is one of "Normal" '
            'for no memory pressure, "Unset" indicating a memory pressure event '
            'has not been received, "Warning" or "Critical" mapping to the system '
            'memory pressure levels, or "Unexpected" for an unexpected level. This '
            "is a Mac-specific annotation."
        ),
        choices=["Normal", "Unset", "Warning", "Critical", "Unexpected"],
        is_protected=False,
    ),
    "mac_memory_pressure_sysctl": number_field(
        name="mac_memory_pressure_sysctl",
        description=(
            "The value of the memory pressure sysctl "
            "'kern.memorystatus_vm_pressure_level'. Indicates which memory pressure "
            "level the system is in at the time of the crash. The expected values "
            "are one of 4 (Critical), 2 (Warning), or 0 (Normal)."
        ),
        number_type="integer",
        is_protected=False,
    ),
    "major_version": {
        "data_validation_type": "int",
        "description": "Major part of the version",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "major_version",
        "is_exposed": True,
        "is_returned": True,
        "name": "major_version",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "integer"},
    },
    "memory_error_correction": {
        "data_validation_type": "str",
        "description": (
            "Windows only, type of error correction used by system memory.  See "
            "documentation for MemoryErrorCorrection property of "
            "Win32_PhysicalMemoryArray WMI class."
        ),
        "form_field_choices": [
            "Reserved",
            "Other",
            "Unknown",
            "None",
            "Parity",
            "Single-bit ECC",
            "Multi-bit ECC",
            "CRC",
            "Unexpected value",
        ],
        "has_full_version": False,
        "in_database_name": "MemoryErrorCorrection",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_error_correction",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "memory_explicit": {
        "data_validation_type": "int",
        "description": (
            'The "explicit" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "explicit",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_explicit",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_gfx_textures": {
        "data_validation_type": "int",
        "description": (
            'The "gfx-textures" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "gfx_textures",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_gfx_textures",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_ghost_windows": {
        "data_validation_type": "int",
        "description": (
            'The "ghost-windows" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ghost_windows",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_ghost_windows",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_heap_allocated": {
        "data_validation_type": "int",
        "description": (
            'The "heap-allocated" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "heap_allocated",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_heap_allocated",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_heap_overhead": {
        "data_validation_type": "int",
        "description": (
            'The "heap-overhead" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "heap_overhead",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_heap_overhead",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_heap_unclassified": {
        "data_validation_type": "int",
        "description": (
            'The "heap-unclassified" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "heap_unclassified",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_heap_unclassified",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_host_object_urls": {
        "data_validation_type": "int",
        "description": (
            'The "host-object-urls" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "host_object_urls",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_host_object_urls",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_images": {
        "data_validation_type": "int",
        "description": (
            'The "images" measurement from the memory report. See about:memory for a fuller '
            "description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "images",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_images",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_js_main_runtime": {
        "data_validation_type": "int",
        "description": (
            'The "js-main-runtime" measurement from the memory report. See about:memory for a '
            "fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "js_main_runtime",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_js_main_runtime",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_measures": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "memory_measures",
        "is_exposed": False,
        "is_returned": True,
        "name": "memory_measures",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": None,
    },
    "memory_private": {
        "data_validation_type": "int",
        "description": (
            'The "private" measurement from the memory report. See about:memory for a fuller '
            "description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "private",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_private",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_resident": {
        "data_validation_type": "int",
        "description": (
            'The "resident" measurement from the memory report. See about:memory for a fuller '
            "description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "resident",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_resident",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_resident_unique": {
        "data_validation_type": "int",
        "description": (
            'The "resident-unique" measurement from the memory report. See about:memory for a '
            "fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "resident_unique",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_resident_unique",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_system_heap_allocated": {
        "data_validation_type": "int",
        "description": (
            'The "system-heap-allocated" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "system_heap_allocated",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_system_heap_allocated",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_top_none_detached": {
        "data_validation_type": "int",
        "description": (
            'The "top(none)/detached" measurement from the memory report. See about:memory for a '
            "fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "top_none_detached",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_top_none_detached",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_vsize": {
        "data_validation_type": "int",
        "description": (
            'The "vsize" measurement from the memory report. See about:memory for a fuller '
            "description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "vsize",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_vsize",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "memory_vsize_max_contiguous": {
        "data_validation_type": "int",
        "description": (
            'The "vsize-max-contiguous" measurement from the memory report. See about:memory for '
            "a fuller description."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "vsize_max_contiguous",
        "is_exposed": True,
        "is_returned": True,
        "name": "memory_vsize_max_contiguous",
        "namespace": "processed_crash.memory_measures",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "minidump_sha256_hash": {
        "data_validation_type": "str",
        "description": "SHA256 hash of the minidump if there was one.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "minidump_sha256_hash",
        "is_exposed": True,
        "is_returned": True,
        "name": "minidump_sha256_hash",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "modules_in_stack": {
        "data_validation_type": "str",
        "description": "Set of module/debugid strings that show up in stack of the crashing thread.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "modules_in_stack",
        "is_exposed": True,
        "is_returned": True,
        "name": "modules_in_stack",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"analyzer": "semicolon_keywords", "type": "string"},
    },
    "moz_crash_reason": {
        "data_validation_type": "str",
        "description": (
            "For aborts caused by MOZ_CRASH, MOZ_RELEASE_ASSERT and related macros, this is the "
            "accompanying description. This is the sanitized value from the crash report."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "moz_crash_reason",
        "is_exposed": True,
        "is_returned": True,
        "name": "moz_crash_reason",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "moz_crash_reason_raw": {
        "data_validation_type": "str",
        "description": (
            "For aborts caused by MOZ_CRASH, MOZ_RELEASE_ASSERT and related macros, this is the "
            "accompanying description. This is the raw value from the crash report."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "moz_crash_reason_raw",
        "is_exposed": True,
        "is_returned": True,
        "name": "moz_crash_reason_raw",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "oom_allocation_size": {
        "data_validation_type": "int",
        "description": (
            "A measure or estimate of the allocation request size that triggered an OOM crash. "
            "Note that allocators usually work with large (e.g. 1 MiB) chunks of memory, and a "
            "small request may have triggered a large chunk request, in which case the latter "
            "actually caused the OOM crash."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "OOMAllocationSize",
        "is_exposed": True,
        "is_returned": True,
        "name": "oom_allocation_size",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "platform": {
        "data_validation_type": "enum",
        "description": (
            "Basic name of the operating system. Can be 'Windows NT', 'Mac OS X' or "
            "'Linux'. Use `platform_pretty_version` for a more precise OS name including "
            "version."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "os_name",
        "is_exposed": True,
        "is_returned": True,
        "name": "platform",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {
            "fields": {
                "full": {"index": "not_analyzed", "type": "string"},
                "os_name": {"type": "string"},
            },
            "type": "multi_field",
        },
    },
    "platform_pretty_version": {
        "data_validation_type": "str",
        "description": "A better platform name, including version for Windows and Mac OS X.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "os_pretty_version",
        "is_exposed": True,
        "is_returned": True,
        "name": "platform_pretty_version",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "platform_version": {
        "data_validation_type": "str",
        "description": "Version of the operating system.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "os_version",
        "is_exposed": True,
        "is_returned": True,
        "name": "platform_version",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "plugin_filename": {
        "data_validation_type": "enum",
        "description": (
            "When a plugin process crashes, this is the name of the file of the plugin loaded "
            "into that process."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "PluginFilename",
        "is_exposed": True,
        "is_returned": True,
        "name": "plugin_filename",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {
            "fields": {
                "PluginFilename": {"index": "analyzed", "type": "string"},
                "full": {"index": "not_analyzed", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "plugin_name": {
        "data_validation_type": "enum",
        "description": (
            "When a plugin process crashes, this is the name of the plugin loaded into that "
            "process."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "PluginName",
        "is_exposed": True,
        "is_returned": True,
        "name": "plugin_name",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {
            "fields": {
                "PluginName": {"index": "analyzed", "type": "string"},
                "full": {"index": "not_analyzed", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "plugin_version": {
        "data_validation_type": "enum",
        "description": (
            "When a plugin process crashes, this is the version of the plugin loaded into that "
            "process."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "PluginVersion",
        "is_exposed": True,
        "is_returned": True,
        "name": "plugin_version",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {
            "fields": {
                "PluginVersion": {"index": "analyzed", "type": "string"},
                "full": {"index": "not_analyzed", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "process_type": {
        "data_validation_type": "str",
        "description": (
            'Type of the process that crashed. This will be "parent" if the crash '
            "report had no ProcessType annotation."
        ),
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
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "processor_notes": {
        "data_validation_type": "str",
        "description": (
            "Notes of the Socorro processor, contains information about what changes were made to "
            "the report during processing."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "processor_notes",
        "is_exposed": True,
        "is_returned": True,
        "name": "processor_notes",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "product": {
        "data_validation_type": "enum",
        "description": "Name of the software.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "product",
        "is_exposed": True,
        "is_returned": True,
        "name": "product",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {
            "fields": {
                "full": {"index": "not_analyzed", "type": "string"},
                "product": {"index": "analyzed", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "productid": {
        "data_validation_type": "enum",
        "description": "Identifier of the software.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "productid",
        "is_exposed": True,
        "is_returned": True,
        "name": "productid",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "proto_signature": {
        "data_validation_type": "str",
        "description": (
            "A concatenation of the signatures of all the frames of the crashing thread."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "proto_signature",
        "is_exposed": True,
        "is_returned": True,
        "name": "proto_signature",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "reason": {
        "data_validation_type": "str",
        "description": (
            "The crash's exception kind. Different OSes have different exception kinds. Example"
            'values: "EXCEPTION_ACCESS_VIOLATION_READ", "EXCEPTION_BREAKPOINT", "SIGSEGV".'
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "reason",
        "is_exposed": True,
        "is_returned": True,
        "name": "reason",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {
                "full": {"index": "not_analyzed", "type": "string"},
                "reason": {"analyzer": "standard", "type": "string"},
            },
            "type": "multi_field",
        },
    },
    "release_channel": {
        "data_validation_type": "enum",
        "description": (
            "The update channel that the user is on. Typically 'nightly', 'aurora', 'beta', "
            "or 'release', but this may also be other values like 'release-cck-partner'."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "release_channel",
        "is_exposed": True,
        "is_returned": True,
        "name": "release_channel",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "remote_type": {
        "data_validation_type": "enum",
        "description": (
            '"extension" if a WebExtension, "web" or missing otherwise. This is only set for '
            "content crashes."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "RemoteType",
        "is_exposed": True,
        "is_returned": True,
        "name": "remote_type",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "safe_mode": {
        "data_validation_type": "bool",
        "description": "Was the browser running in Safe mode?",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "SafeMode",
        "is_exposed": True,
        "is_returned": True,
        "name": "safe_mode",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "shutdown_progress": {
        "data_validation_type": "str",
        "description": "See https://bugzilla.mozilla.org/show_bug.cgi?id=1038342",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "ShutdownProgress",
        "is_exposed": True,
        "is_returned": True,
        "name": "shutdown_progress",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"type": "string"},
    },
    "signature": {
        "data_validation_type": "str",
        "description": (
            "This is the field most commonly used for aggregating individual crash reports "
            "into a group. It usually contains one or more stack frames from the crashing "
            "thread. The stack frames may also be augmented or replaced with other tokens such "
            'as "OOM | small" or "shutdownhang" that further identify the crash kind.'
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "signature",
        "is_exposed": True,
        "is_returned": True,
        "name": "signature",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {
                "full": {"index": "not_analyzed", "type": "string"},
                "signature": {"type": "string"},
            },
            "type": "multi_field",
        },
    },
    "skunk_classification": {
        "data_validation_type": "enum",
        "description": (
            "The skunk classification of this crash report, assigned by the processors."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "classification",
        "is_exposed": True,
        "is_returned": True,
        "name": "skunk_classification",
        "namespace": "processed_crash.classifications.skunk_works",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "stackwalk_version": keyword_field(
        name="stackwalk_version",
        description="binary and version for stackwalker used to process report",
        namespace="processed_crash.json_dump",
        is_protected=False,
    ),
    "startup_crash": {
        "data_validation_type": "bool",
        "description": (
            "Annotation that tells whether the crash happened before the startup phase "
            "was finished or not."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "StartupCrash",
        "is_exposed": True,
        "is_returned": True,
        "name": "startup_crash",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"null_value": "False", "type": "boolean"},
    },
    "startup_time": {
        "data_validation_type": "int",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "StartupTime",
        "is_exposed": True,
        "is_returned": True,
        "name": "startup_time",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "submitted_from_infobar": {
        "data_validation_type": "bool",
        "description": (
            "True if the crash report was submitted after the crash happened, from an infobar "
            "in the UI."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "SubmittedFromInfobar",
        "is_exposed": True,
        "is_returned": True,
        "name": "submitted_from_infobar",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    # NOTE(willkg): This is only here because the report view in the webapp uses the
    # description.
    "submitted_timestamp": {
        "data_validation_type": "enum",
        "description": "The datetime when the crash was submitted to the Socorro collector.",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "submitted_timestamp",
        "is_exposed": False,
        "is_returned": True,
        "name": "submitted_timestamp",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": None,
    },
    "support_classification": {
        "data_validation_type": "enum",
        "description": (
            "The support classification of this crash report, assigned by the processors."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "classification",
        "is_exposed": True,
        "is_returned": True,
        "name": "support_classification",
        "namespace": "processed_crash.classifications.support",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "system_memory_use_percentage": {
        "data_validation_type": "int",
        "description": "The approximate percentage of physical memory that is in use.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "SystemMemoryUsePercentage",
        "is_exposed": True,
        "is_returned": True,
        "name": "system_memory_use_percentage",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "throttleable": {
        "data_validation_type": "bool",
        "description": "Whether the crash report was throttleable when submitted.",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "Throttleable",
        "is_exposed": True,
        "is_returned": True,
        "name": "throttleable",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "bool",
        "storage_mapping": {"type": "boolean"},
    },
    "topmost_filenames": {
        "data_validation_type": "str",
        "description": "Paths of the files at the top of the stack.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "topmost_filenames",
        "is_exposed": True,
        "is_returned": True,
        "name": "topmost_filenames",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {"analyzer": "semicolon_keywords", "type": "string"},
    },
    "total_page_file": {
        "data_validation_type": "int",
        "description": "",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "TotalPageFile",
        "is_exposed": True,
        "is_returned": True,
        "name": "total_page_file",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "total_physical_memory": {
        "data_validation_type": "int",
        "description": "The total amount of physical memory.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "TotalPhysicalMemory",
        "is_exposed": True,
        "is_returned": True,
        "name": "total_physical_memory",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "total_virtual_memory": {
        "data_validation_type": "int",
        "description": (
            "The size of the user-mode portion of the virtual address space of the calling "
            "process. This value depends on the type of process, the type of processor, and "
            "the configuration of the operating system. 32-bit processes usually have values "
            "in the range 2--4 GiB. 64-bit processes usually have *much* larger values."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "TotalVirtualMemory",
        "is_exposed": True,
        "is_returned": True,
        "name": "total_virtual_memory",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "upload_file_minidump_browser": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "upload_file_minidump_browser",
        "is_exposed": False,
        "is_returned": True,
        "name": "upload_file_minidump_browser",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": None,
    },
    "upload_file_minidump_flash1": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "upload_file_minidump_flash1",
        "is_exposed": False,
        "is_returned": True,
        "name": "upload_file_minidump_flash1",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": None,
    },
    "upload_file_minidump_flash2": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "upload_file_minidump_flash2",
        "is_exposed": False,
        "is_returned": True,
        "name": "upload_file_minidump_flash2",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": None,
    },
    "uptime": {
        "data_validation_type": "int",
        "description": (
            "Length of time the process was running before it crashed. Small values "
            "(from 0 to 5 or so) usually indicate start-up crashes. Calculated by "
            "the Socorro processor using CrashTime and StartupTime."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "uptime",
        "is_exposed": True,
        "is_returned": True,
        "name": "uptime",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "long"},
    },
    "uptime_ts": {
        "data_validation_type": "int",
        "description": (
            "Uptime in seconds. This annotation uses a string instead of an integer "
            "because it has a fractional component."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "UptimeTS",
        "is_exposed": True,
        "is_returned": True,
        "name": "uptime_ts",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "number",
        "storage_mapping": {"type": "double"},
    },
    "url": {
        "data_validation_type": "str",
        "description": (
            "The website which the user most recently visited in the browser before the crash. "
            "Users have the option of opting in or out of sending the current URL. This "
            "information may not always be valuable, because pages in other tabs or windows "
            "may be responsible for a particular crash."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "url",
        "is_exposed": True,
        "is_returned": True,
        "name": "url",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "user_comments": {
        "data_validation_type": "str",
        "description": "Comments entered by the user when they crashed.",
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "user_comments",
        "is_exposed": True,
        "is_returned": True,
        "name": "user_comments",
        "namespace": "processed_crash",
        "permissions_needed": ["crashstats.view_pii"],
        "query_type": "string",
        "storage_mapping": {
            "fields": {
                "full": {"index": "not_analyzed", "type": "string"},
                "user_comments": {"type": "string"},
            },
            "type": "multi_field",
        },
    },
    "useragent_locale": {
        "data_validation_type": "enum",
        "description": "The locale of the software installation.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "useragent_locale",
        "is_exposed": True,
        "is_returned": True,
        "name": "useragent_locale",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "semicolon_keywords", "type": "string"},
    },
    "uuid": {
        "data_validation_type": "enum",
        "description": "Unique identifier of the report.",
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "uuid",
        "is_exposed": True,
        "is_returned": True,
        "name": "uuid",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "vendor": {
        "data_validation_type": "enum",
        "description": "",
        "form_field_choices": None,
        "has_full_version": False,
        "in_database_name": "Vendor",
        "is_exposed": True,
        "is_returned": True,
        "name": "vendor",
        "namespace": "raw_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"type": "string"},
    },
    "version": {
        "data_validation_type": "enum",
        "description": (
            "The product version number. A value lacking any letters indicates a normal release; "
            'a value with a "b" indicates a Beta release; a value with an "a" indicates an Aurora '
            '(a.k.a. Developer Edition) release; a value with "esr" indicates an Extended Service '
            "Release."
        ),
        "form_field_choices": [],
        "has_full_version": False,
        "in_database_name": "version",
        "is_exposed": True,
        "is_returned": True,
        "name": "version",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "enum",
        "storage_mapping": {"analyzer": "keyword", "type": "string"},
    },
    "windows_error_reporting": flag_field(
        name="windows_error_reporting",
        description=(
            "Set to 1 if this crash was intercepted via the Windows Error Reporting "
            "runtime exception module."
        ),
        is_protected=False,
    ),
    "winsock_lsp": {
        "data_validation_type": "str",
        "description": (
            "On Windows, a string of data from the Windows OS about the list of installed LSPs "
            "(Layered Service Provider)."
        ),
        "form_field_choices": [],
        "has_full_version": True,
        "in_database_name": "Winsock_LSP",
        "is_exposed": True,
        "is_returned": True,
        "name": "winsock_lsp",
        "namespace": "processed_crash",
        "permissions_needed": [],
        "query_type": "string",
        "storage_mapping": {
            "fields": {"full": {"index": "not_analyzed", "type": "string"}},
            "index": "analyzed",
            "type": "string",
        },
    },
    "xpcom_spin_event_loop_stack": keyword_field(
        name="xpcom_spin_event_loop_stack",
        description=(
            "If we crash while some code is spinning manually the event loop, we will "
            "see the stack of nested annotations here."
        ),
        is_protected=False,
    ),
}

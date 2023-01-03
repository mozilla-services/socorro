# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import datetime
import json
import re
import time

from configman import Namespace
from configman.converters import class_converter
import elasticsearch
from elasticsearch.exceptions import NotFoundError
import glom
import markus

from socorro.external.crashstorage_base import CrashStorageBase
from socorro.external.es.super_search_fields import (
    FIELDS,
    get_destination_keys,
    get_source_key,
    is_indexable,
    parse_mapping,
)
from socorro.lib.libdatetime import JsonDTEncoder, string_to_datetime


# Maximum size in characters for a keyword field value
MAX_KEYWORD_FIELD_VALUE_SIZE = 10_000

# Maximum size in utf-8 encoded characters for a string field value
MAX_STRING_FIELD_VALUE_SIZE = 32_766


# Valid Elasticsearch keys contain one or more ascii alphanumeric characters, underscore, and hyphen
# and that's it.
VALID_KEY = re.compile(r"^[a-zA-Z0-9_-]+$")


def is_valid_key(key):
    """Validates an Elasticsearch document key

    :arg string key: the key to validate

    :returns: True if it's valid and False if not

    """
    return bool(VALID_KEY.match(key))


def fix_keyword(value, max_size):
    """Truncates keyword value greater than max_size length in characters

    :param value: the value to fix
    :param int max_size: the maximum size for the field value

    :returns: fixed value

    """
    if isinstance(value, list):
        if len(value) == 0:
            return value
        if not isinstance(value[0], str):
            # Return a list of "BAD DATA" so we keep the right shape
            return ["BAD DATA"]

        return [fix_keyword(line, max_size=max_size) for line in value]

    if not isinstance(value, str):
        return "BAD DATA"

    if len(value) > max_size:
        value = value[:max_size]
    return value


def fix_string(value, max_size):
    """Truncates string value greater than max_size length in bytes

    :param value: the value to fix
    :param int max_size: the maximum size in bytes to truncate the unicode string encoded
        as utf-8 to

    :returns: fixed value

    """
    if isinstance(value, list):
        if len(value) == 0:
            return value
        if not isinstance(value[0], str):
            # Return a list of "BAD DATA" so we keep the right shape
            return ["BAD DATA"]

        return [fix_string(line, max_size=max_size) for line in value]

    if not isinstance(value, str):
        return "BAD DATA"

    try:
        value_bytes = value.encode("utf-8")
    except UnicodeEncodeError:
        # If we hit an encoding error, then it's probably not valid unicode
        # and we should reject it
        return "BAD DATA"

    if len(value_bytes) <= max_size:
        return value

    value_bytes = value_bytes[:max_size]
    new_value = ""

    # Remove bytes until we either run out of bytes or we can decode to a unicode
    # string
    while value_bytes:
        try:
            new_value = value_bytes.decode("utf-8")
            break
        except UnicodeDecodeError:
            value_bytes = value_bytes[:-1]

    new_value = new_value or "BAD DATA"
    return new_value


POSSIBLE_TRUE_VALUES = [1, "1", "true", True]


def fix_boolean(value):
    """Converts pseudo-boolean value to boolean value.

    Valid boolean values are True, 'true', False, and 'false'.

    :param value: the value to fix

    :returns: fixed value

    """
    return True if value in POSSIBLE_TRUE_VALUES else False


INTEGER_BOUNDS = (-2_147_483_648, 2_147_483_647)


def fix_integer(value):
    """Fix integer value so it doesn't exceed Elasticsearch maximums

    :param value: the value to fix

    :returns: fixed value

    """
    min_int, max_int = INTEGER_BOUNDS
    if not isinstance(value, int):
        try:
            value = int(value)
        except ValueError:
            # If the value isn't valid, remove it
            return None

    if not (min_int <= value <= max_int):
        # If the value isn't within the bounds, remove it
        return None

    return value


LONG_BOUNDS = (-9_223_372_036_854_775_808, 9_223_372_036_854_775_807)


def fix_long(value):
    """Fix long value so it doesn't exceed Elasticsearch maximums

    :param value: the value to fix

    :returns: fixed value

    """
    min_long, max_long = LONG_BOUNDS
    if not isinstance(value, int):
        try:
            value = int(value)
        except ValueError:
            # If the value isn't valid, remove it
            return None

    if not (min_long <= value <= max_long):
        # If the value isn't within the bounds, remove it
        return None
    return value


def fix_datetime(value):
    """Fix datetime value to index correctly

    :param value: the value to fix

    :returns: fixed value

    """
    if isinstance(value, str):
        return string_to_datetime(value)
    if not isinstance(value, (datetime.datetime, datetime.time)):
        return None
    return value


def build_document(src, crash_document, fields, all_keys):
    """Given a source document and fields and valid keys, builds a document to index.

    :param dict src: the source document with raw_crash and processed_crash keys
    :param dict crash_document: the document to fill
    :param list fields: the list of fields in super search fields
    :param set all_keys: the list of valid keys

    """
    for field in fields.values():
        # There are some fields that aren't indexable--skip those
        if not is_indexable(field):
            continue

        src_key = get_source_key(field)
        value = glom.glom(src, src_key, default=None)
        if value is None:
            continue

        # Fix values so they index correctly
        storage_type = field.get("type", field["storage_mapping"].get("type"))

        if (
            storage_type == "multi_field"
            and glom.glom(field, "storage_mapping.fields.full.type", default="")
            == "string"
        ):
            storage_type = "string"

        if storage_type == "string":
            analyzer = field.get("analyzer", field["storage_mapping"].get("analyzer"))
            if analyzer == "keyword":
                value = fix_keyword(value, max_size=MAX_KEYWORD_FIELD_VALUE_SIZE)
            else:
                value = fix_string(value, max_size=MAX_STRING_FIELD_VALUE_SIZE)

        elif storage_type == "integer":
            value = fix_integer(value)
            if value is None:
                continue

        elif storage_type == "long":
            value = fix_long(value)
            if value is None:
                continue

        elif storage_type == "date":
            value = fix_datetime(value)
            if value is None:
                continue

        for dest_key in get_destination_keys(field):
            if dest_key in all_keys:
                glom.assign(crash_document, dest_key, value, missing=dict)


class ESCrashStorage(CrashStorageBase):
    """This sends raw and processed crash reports to Elasticsearch."""

    required_config = Namespace()
    required_config.elasticsearch = Namespace()
    required_config.elasticsearch.add_option(
        "elasticsearch_class",
        default="socorro.external.es.connection_context.ConnectionContext",
        from_string_converter=class_converter,
        reference_value_from="resource.elasticsearch",
    )

    # These regex will catch field names from Elasticsearch exceptions. They
    # have been tested with Elasticsearch 1.4.
    field_name_string_error_re = re.compile(r"field=\"([\w\-.]+)\"")
    field_name_number_error_re = re.compile(r"\[failed to parse \[([\w\-.]+)]]")
    field_name_unknown_property_error_re = field_name_number_error_re

    def __init__(self, config, namespace=""):
        super().__init__(config, namespace=namespace)

        self.es_context = self.config.elasticsearch.elasticsearch_class(
            config=self.config.elasticsearch
        )
        self.metrics = markus.get_metrics(namespace)

        # Cached answers for things that don't change
        self._keys_for_indexable_fields_cache = None
        self._keys_for_mapping_cache = {}

    def get_keys_for_indexable_fields(self):
        """Return keys for FIELDS in "namespace.key" format

        NOTE(willkg): Results are cached on this ESCrashStorage instance. If you change
        FIELDS (like in tests), create a new ESCrashStorage instance.

        :returns: set of "namespace.key" strings

        """
        keys = self._keys_for_indexable_fields_cache
        if keys is None:
            keys = set()
            for field in FIELDS.values():
                if not is_indexable(field):
                    continue

                keys = keys | set(get_destination_keys(field))
            self._keys_for_indexable_fields_cache = keys

        return keys

    def get_keys_for_mapping(self, index_name, es_doctype):
        """Get the keys in "namespace.key" format for a given mapping

        NOTE(willkg): Results are cached on this ESCrashStorage instance.

        :arg str index_name: the name of the index
        :arg str es_doctype: the doctype for the index

        :returns: set of "namespace.key" fields

        :raise elasticsearch.exceptions.NotFoundError: if the index doesn't exist

        """
        cache_key = f"{index_name}::{es_doctype}"
        keys = self._keys_for_mapping_cache.get(cache_key)
        if keys is None:
            mapping = self.es_context.get_mapping(index_name, es_doctype, reraise=True)
            keys = parse_mapping(mapping, None)
            self._keys_for_mapping_cache[cache_key] = keys
        return keys

    def get_keys(self, index_name, es_doctype):
        supersearch_fields_keys = self.get_keys_for_indexable_fields()
        try:
            mapping_keys = self.get_keys_for_mapping(index_name, es_doctype)
        except NotFoundError:
            mapping_keys = None
        all_valid_keys = supersearch_fields_keys
        if mapping_keys:
            # If there are mapping_keys, then the index exists already and we
            # should make sure we're not indexing anything that's not in that
            # mapping
            all_valid_keys = all_valid_keys & mapping_keys

        return all_valid_keys

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save processed crash report to Elasticsearch"""
        crash_id = processed_crash["uuid"]

        index_name = self.es_context.get_index_for_date(
            string_to_datetime(processed_crash["date_processed"])
        )
        es_doctype = self.config.elasticsearch.elasticsearch_doctype
        all_valid_keys = self.get_keys(index_name, es_doctype)

        src = {
            "raw_crash": copy.deepcopy(raw_crash),
            "processed_crash": copy.deepcopy(processed_crash),
        }

        crash_document = {
            "crash_id": crash_id,
            "raw_crash": {},
            "processed_crash": {},
        }
        build_document(src, crash_document, fields=FIELDS, all_keys=all_valid_keys)

        # Capture crash data size metrics
        self.capture_crash_metrics(crash_document)

        self._submit_crash_to_elasticsearch(
            crash_id=crash_id,
            es_doctype=es_doctype,
            index_name=index_name,
            crash_document=crash_document,
        )

    def capture_crash_metrics(self, crash_document):
        """Capture metrics about crash data being saved to Elasticsearch"""

        def _capture(key, data):
            try:
                self.metrics.histogram(
                    key, value=len(json.dumps(data, cls=JsonDTEncoder))
                )
            except Exception:
                # NOTE(willkg): An error here shouldn't screw up saving data. Log it so
                # we can fix it later.
                self.logger.exception(f"something went wrong when capturing {key}")

        _capture("raw_crash_size", crash_document["raw_crash"])
        _capture("processed_crash_size", crash_document["processed_crash"])
        _capture("crash_document_size", crash_document)

    def _index_crash(self, connection, es_index, es_doctype, crash_document, crash_id):
        try:
            start_time = time.time()
            connection.index(
                index=es_index, doc_type=es_doctype, body=crash_document, id=crash_id
            )
            index_outcome = "successful"
        except Exception:
            index_outcome = "failed"
            raise
        finally:
            elapsed_time = time.time() - start_time
            self.metrics.histogram(
                "index", value=elapsed_time * 1000.0, tags=["outcome:" + index_outcome]
            )

    def _submit_crash_to_elasticsearch(
        self, crash_id, es_doctype, index_name, crash_document
    ):
        """Submit a crash report to elasticsearch"""
        # Attempt to create the index; it's OK if it already exists.
        self.es_context.create_index(index_name)

        # Submit the crash for indexing.
        # Don't retry more than 5 times. That is to avoid infinite loops in
        # case of an unhandled exception.
        for attempt in range(5):
            try:
                with self.es_context() as conn:
                    return self._index_crash(
                        conn, index_name, es_doctype, crash_document, crash_id
                    )

            except elasticsearch.exceptions.ConnectionError:
                # If this is a connection error, sleep a second and then try again
                time.sleep(1.0)

            except elasticsearch.exceptions.TransportError as e:
                # If this is a TransportError, we try to figure out what the error
                # is and fix the document and try again
                field_name = None

                if "MaxBytesLengthExceededException" in e.error:
                    # This is caused by a string that is way too long for
                    # Elasticsearch.
                    matches = self.field_name_string_error_re.findall(e.error)
                    if matches:
                        field_name = matches[0]
                        self.metrics.incr(
                            "indexerror", tags=["error:maxbyteslengthexceeded"]
                        )

                elif "NumberFormatException" in e.error:
                    # This is caused by a number that is either too big for
                    # Elasticsearch or just not a number.
                    matches = self.field_name_number_error_re.findall(e.error)
                    if matches:
                        field_name = matches[0]
                        self.metrics.incr(
                            "indexerror", tags=["error:numberformatexception"]
                        )

                elif "unknown property" in e.error:
                    # This is caused by field values that are nested for a field where a
                    # previously indexed value was a string. For example, the processor
                    # first indexes ModuleSignatureInfo value as a string, then tries to
                    # index ModuleSignatureInfo as a nested dict.
                    matches = self.field_name_unknown_property_error_re.findall(e.error)
                    if matches:
                        field_name = matches[0]
                        self.metrics.incr("indexerror", tags=["error:unknownproperty"])

                if not field_name:
                    # We are unable to parse which field to remove, we cannot
                    # try to fix the document. Let it raise.
                    self.logger.critical(
                        "Submission to Elasticsearch failed for %s (%s)",
                        crash_id,
                        e,
                        exc_info=True,
                    )
                    self.metrics.incr("indexerror", tags=["error:unhandled"])
                    raise

                if field_name.endswith(".full"):
                    # Remove the `.full` at the end, that is a special mapping
                    # construct that is not part of the real field name.
                    field_name = field_name.rstrip(".full")

                # Now remove that field from the document before trying again.
                field_path = field_name.split(".")
                parent = crash_document
                for i, field in enumerate(field_path):
                    if i == len(field_path) - 1:
                        # This is the last level, so `field` contains the name
                        # of the field that we want to remove from `parent`.
                        del parent[field]
                    else:
                        parent = parent[field]

                # Add a note in the document that a field has been removed.
                if crash_document.get("removed_fields"):
                    crash_document["removed_fields"] = "{} {}".format(
                        crash_document["removed_fields"], field_name
                    )
                else:
                    crash_document["removed_fields"] = field_name

            except elasticsearch.exceptions.ElasticsearchException as exc:
                self.logger.critical(
                    "Submission to Elasticsearch failed for %s (%s)",
                    crash_id,
                    exc,
                    exc_info=True,
                )
                raise

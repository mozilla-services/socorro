# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import datetime
import json
import re
import time
from math import isnan, isinf

import elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch.dsl import Search
import glom
import markus

from socorro.external.crashstorage_base import CrashStorageBase
from socorro.external.es.connection_context import ConnectionContext
from socorro.external.es.query import Query
from socorro.external.es.supersearch import SuperSearch
from socorro.external.es.super_search_fields import (
    build_mapping,
    FIELDS,
    get_destination_keys,
    get_source_key,
    is_indexable,
    parse_mapping,
)
from socorro.libmarkus import METRICS, build_prefix
from socorro.lib.libdatetime import JsonDTEncoder, string_to_datetime, utc_now


# Additional custom analyzers for crash report data
ES_CUSTOM_ANALYZERS = {
    "analyzer": {"semicolon_keywords": {"type": "pattern", "pattern": ";"}}
}

# Elasticsearch indices configuration
ES_QUERY_SETTINGS = {"default_field": "signature"}

# Maximum size in characters for a keyword field value
MAX_KEYWORD_FIELD_VALUE_SIZE = 10_000

# Maximum size in utf-8 encoded characters for a string field value
MAX_STRING_FIELD_VALUE_SIZE = 32_766

# Valid Elasticsearch keys contain one or more ascii alphanumeric characters,
# underscore, and hyphen and that's it
VALID_KEY = re.compile(r"^[a-zA-Z0-9_-]+$")


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


def fix_double(value):
    """Fix double value so it doesn't encode invalid json

    :param value: the value to fix

    :returns: fixed value

    """
    if not isinstance(value, float):
        try:
            value = float(value)
        except ValueError:
            # If the value isn't valid, remove it
            return None

    if isnan(value) or isinf(value):
        # If the value isn't within bounds, remove it
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

    :param dict src: the source document with "processed_crash" key
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

        if storage_type == "keyword":
            value = fix_keyword(value, max_size=MAX_KEYWORD_FIELD_VALUE_SIZE)

        elif storage_type == "text":
            value = fix_string(value, max_size=MAX_STRING_FIELD_VALUE_SIZE)

        elif storage_type == "integer":
            value = fix_integer(value)
            if value is None:
                continue

        elif storage_type == "long":
            value = fix_long(value)
            if value is None:
                continue

        elif storage_type == "double":
            value = fix_double(value)
            if value is None:
                continue

        elif storage_type == "date":
            value = fix_datetime(value)
            if value is None:
                continue

        elif storage_type == "boolean":
            value = fix_boolean(value)

        for dest_key in get_destination_keys(field):
            if dest_key in all_keys:
                glom.assign(crash_document, dest_key, value, missing=dict)


class ESCrashStorage(CrashStorageBase):
    """Indexes documents based on the processed crash to Elasticsearch."""

    SUPERSEARCH_FIELDS = FIELDS

    # These regex will catch field names from Elasticsearch exceptions. They
    # have been tested with Elasticsearch 8.17.
    field_name_string_error_re = re.compile(r"field=\"([\w\-.]+)\"")
    field_name_number_error_re = re.compile(r"failed to parse field \[([\w\-.]+)]")
    field_name_unknown_property_error_re = field_name_number_error_re

    def __init__(
        self,
        url="http://localhost:9200",
        index="socorro%Y%W",
        index_regex=r"^socorro[0-9]{6}$",
        retention_policy=26,
        metrics_prefix="processor.es",
        timeout=30,
        shards_per_index=10,
        ca_certs=None,
    ):
        super().__init__()

        self.client = self.build_client(url=url, timeout=timeout, ca_certs=ca_certs)

        # Create a MetricsInterface that includes the base prefix plus the prefix passed
        # into __init__
        self.metrics = markus.get_metrics(
            build_prefix(METRICS.prefix, metrics_prefix),
            filters=list(METRICS.filters),
        )

        self.index = index
        self.index_regex = index_regex
        self.retention_policy = retention_policy
        self.shards_per_index = shards_per_index

        # Cached answers for things that don't change
        self._keys_for_indexable_fields_cache = None
        self._keys_for_mapping_cache = {}
        self._mapping_cache = {}

    @classmethod
    def build_client(cls, url, timeout, ca_certs=None):
        return ConnectionContext(url=url, timeout=timeout, ca_certs=ca_certs)

    def build_query(self):
        """Return new instance of Query."""
        return Query(crashstorage=self)

    def build_supersearch(self):
        """Return new instance of SuperSearch."""
        return SuperSearch(crashstorage=self)

    def build_search(self, **kwargs):
        """Return new instance of elasticsearch.dsl's Search."""
        with self.client() as conn:
            return Search(using=conn, **kwargs)

    @staticmethod
    def get_source_key(field):
        """Return source key for the field."""
        return get_source_key(field)

    def get_index_template(self):
        """Return template for index names."""
        return self.index

    def get_index_for_date(self, date):
        """Return the index name for a given date.

        Index names are generated by filling in the date parameters for the
        specified date in the index template.

        :arg datetime date: the datetime to use to generate the index template

        :returns: index name as a str

        """
        template = self.get_index_template()
        return date.strftime(template)

    def get_retention_policy(self):
        """Return retention policy in weeks."""
        return self.retention_policy

    def get_socorro_index_settings(self, mappings):
        """Return a dictionary containing settings for an Elasticsearch index."""
        return {
            "settings": {
                "index": {
                    "number_of_shards": self.shards_per_index,
                    "query": ES_QUERY_SETTINGS,
                    "analysis": ES_CUSTOM_ANALYZERS,
                }
            },
            "mappings": mappings,
        }

    def get_mapping(self, index_name, reraise=False):
        """Retrieves the mapping for a given index

        NOTE(willkg): Mappings are cached on the ESCrashStorage instance. If you change
        the indices (like in tests), you should get a new ESCrashStorage instance.

        :arg str index_name: the index to retrieve the mapping for
        :arg bool reraise: True if you want this to reraise a NotFoundError; False
            otherwise

        :returns: mapping as a dict or None

        """
        mapping = self._mapping_cache.get(index_name)
        if mapping is None:
            try:
                mapping = self.client.get_mapping(index_name=index_name)
                self._mapping_cache[index_name] = mapping
            except elasticsearch.exceptions.NotFoundError:
                if reraise:
                    raise
        return mapping

    def create_index(self, index_name, mappings=None):
        """Create an index that will receive crash reports.

        :arg index_name: the name of the index to create
        :arg mappings: ES mapping

        :returns: True if the index was created, False if it already existed

        """
        if mappings is None:
            mappings = build_mapping()

        index_settings = self.get_socorro_index_settings(mappings)

        return self.client.create_index(
            index_name=index_name,
            index_settings=index_settings,
        )

    def delete_index(self, index_name):
        return self.client.delete_index(index_name=index_name)

    def get_indices(self):
        """Return list of existing crash report indices.

        :returns: list of str

        """
        indices = self.client.get_indices()
        index_regex = re.compile(self.index_regex, re.I)

        indices = [index for index in indices if index_regex.match(index)]
        indices.sort()
        return indices

    def delete_expired_indices(self):
        """Delete indices that exceed our retention policy.

        :returns: list of index names that were deleted

        """
        policy = datetime.timedelta(weeks=self.retention_policy)
        cutoff = (utc_now() - policy).replace(tzinfo=None)
        cutoff = cutoff.strftime(self.index)

        was_deleted = []
        for index_name in self.get_indices():
            if index_name > cutoff:
                continue

            self.client.delete_index(index_name)
            was_deleted.append(index_name)

        return was_deleted

    def get_keys_for_indexable_fields(self):
        """Return keys for SUPERSEARCH_FIELDS in "namespace.key" format

        NOTE(willkg): Results are cached on this ESCrashStorage instance. If you change
        FIELDS (like in tests), create a new ESCrashStorage instance.

        :returns: set of "namespace.key" strings

        """
        keys = self._keys_for_indexable_fields_cache
        if keys is None:
            keys = set()
            for field in self.SUPERSEARCH_FIELDS.values():
                if not is_indexable(field):
                    continue

                keys = keys | set(get_destination_keys(field))
            self._keys_for_indexable_fields_cache = keys

        return keys

    def get_keys_for_mapping(self, index_name):
        """Get the keys in "namespace.key" format for a given mapping

        NOTE(willkg): Results are cached on this ESCrashStorage instance.

        :arg str index_name: the name of the index

        :returns: set of "namespace.key" fields

        :raise elasticsearch.exceptions.NotFoundError: if the index doesn't exist

        """
        keys = self._keys_for_mapping_cache.get(index_name)
        if keys is None:
            mapping = self.get_mapping(index_name, reraise=True)
            keys = parse_mapping(mapping, None)
            self._keys_for_mapping_cache[index_name] = keys
        return keys

    def get_keys(self, index_name):
        supersearch_fields_keys = self.get_keys_for_indexable_fields()
        try:
            mapping_keys = self.get_keys_for_mapping(index_name)
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

        index_name = self.get_index_for_date(
            string_to_datetime(processed_crash["date_processed"])
        )
        all_valid_keys = self.get_keys(index_name)

        src = {"processed_crash": copy.deepcopy(processed_crash)}

        crash_document = {
            "crash_id": crash_id,
            "processed_crash": {},
        }
        build_document(
            src, crash_document, fields=self.SUPERSEARCH_FIELDS, all_keys=all_valid_keys
        )

        # Capture crash data size metrics
        self.capture_crash_metrics(crash_document)

        self._submit_crash_to_elasticsearch(
            crash_id=crash_id,
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

        _capture("crash_document_size", crash_document)

    def _index_crash(self, connection, es_index, crash_document, crash_id):
        try:
            start_time = time.time()
            connection.index(index=es_index, body=crash_document, id=crash_id)
            index_outcome = "successful"
        except Exception:
            index_outcome = "failed"
            raise
        finally:
            elapsed_time = time.time() - start_time
            self.metrics.histogram(
                "index", value=elapsed_time * 1000.0, tags=["outcome:" + index_outcome]
            )

    def _submit_crash_to_elasticsearch(self, crash_id, index_name, crash_document):
        """Submit a crash report to elasticsearch"""
        # Attempt to create the index; it's OK if it already exists.

        # FIXME(willkg): we shouldn't do this--instead we should try to index and create
        # the index if the index doesn't exist
        self.create_index(index_name)

        # Submit the crash for indexing.
        # Don't retry more than 5 times. That is to avoid infinite loops in
        # case of an unhandled exception.
        for _ in range(5):
            try:
                with self.client() as conn:
                    return self._index_crash(conn, index_name, crash_document, crash_id)

            except elasticsearch.ConnectionError:
                # If this is a connection error, sleep a second and then try again
                time.sleep(1.0)

            except elasticsearch.BadRequestError as e:
                # If this is a BadRequestError, we try to figure out what the error
                # is and fix the document and try again
                field_name = None

                error = e.body["error"]

                if (
                    error["type"] == "document_parsing_exception"
                    and error["caused_by"]["type"] == "illegal_argument_exception"
                    and error["reason"].startswith(
                        "Document contains at least one immense term"
                    )
                ):
                    # This is caused by a string that is way too long for
                    # Elasticsearch, specifically 32_766 bytes when UTF8 encoded.
                    matches = self.field_name_string_error_re.findall(error["reason"])
                    if matches:
                        field_name = matches[0]
                        self.metrics.incr(
                            "indexerror", tags=["error:maxbyteslengthexceeded"]
                        )

                elif (
                    error["type"] == "document_parsing_exception"
                    and error["caused_by"]["type"] == "number_format_exception"
                ):
                    # This is caused by a number that is either too big for
                    # Elasticsearch or just not a number.
                    matches = self.field_name_number_error_re.findall(error["reason"])
                    if matches:
                        field_name = matches[0]
                        self.metrics.incr(
                            "indexerror", tags=["error:numberformatexception"]
                        )

                elif (
                    error["type"] == "document_parsing_exception"
                    and error["caused_by"]["type"] == "illegal_argument_exception"
                ):
                    # This is caused by field values that are nested for a field where a
                    # previously indexed value was a string. For example, the processor
                    # first indexes ModuleSignatureInfo value as a string, then tries to
                    # index ModuleSignatureInfo as a nested dict.
                    matches = self.field_name_unknown_property_error_re.findall(
                        error["reason"]
                    )
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
                    # Remove the `.full` at the end, that is a special mapping construct
                    # that is not part of the real field name.
                    field_name = field_name.removesuffix(".full")

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

            except elasticsearch.ApiError as exc:
                self.logger.critical(
                    "Submission to Elasticsearch failed for %s (%s)",
                    crash_id,
                    exc,
                    exc_info=True,
                )
                raise

    def catalog_crash(self, crash_id):
        """Return a list of data items for this crash id"""
        contents = []
        with self.client() as conn:
            try:
                search = Search(using=conn)
                search = search.filter("term", **{"processed_crash.uuid": crash_id})
                results = search.execute().to_dict()
                hits = results["hits"]["hits"]
                if hits:
                    contents.append("es_processed_crash")
            except Exception:
                self.logger.exception(f"ERROR: es: when deleting {crash_id}")
        return contents

    def delete_crash(self, crash_id):
        with self.client() as conn:
            try:
                search = Search(using=conn)
                search = search.filter("term", **{"processed_crash.uuid": crash_id})
                results = search.execute().to_dict()
                hits = results["hits"]["hits"]
                if hits:
                    hit = hits[0]
                    conn.delete(index=hit["_index"], id=hit["_id"])
                    self.client.refresh()
            except Exception:
                self.logger.exception(f"ERROR: es: when deleting {crash_id}")

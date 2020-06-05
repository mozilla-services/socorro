# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import json
import re
import time

from configman import Namespace
from configman.converters import class_converter, list_converter
import elasticsearch
import markus

from socorro.external.crashstorage_base import CrashStorageBase, Redactor
from socorro.external.es.super_search_fields import FIELDS
from socorro.lib.datetimeutil import JsonDTEncoder, string_to_datetime


# Maximum size in characters for a keyword field value
MAX_KEYWORD_FIELD_VALUE_SIZE = 10_000

# Maximum size in utf-8 encoded characters for a string field value
MAX_STRING_FIELD_VALUE_SIZE = 32_766


def reconstitute_datetimes(processed_crash):
    """Convert string values to datetimes for specified fields

    This operates in-place.

    """
    # FIXME(willkg): These should be specified in super_search_fields.py
    # and not hard-coded
    datetime_fields = [
        "submitted_timestamp",
        "date_processed",
        "client_crash_date",
        "started_datetime",
        "startedDateTime",
        "completed_datetime",
        "completeddatetime",
    ]
    for a_key in datetime_fields:
        if a_key not in processed_crash:
            continue

        processed_crash[a_key] = string_to_datetime(processed_crash[a_key])


class RawCrashRedactor(Redactor):
    """Remove some specific keys from a dict. The dict is modified.

    This is a special Redactor used on raw crashes before we send them
    to our Elasticsearch database. It is used to remove fields that we don't
    need to store, in order mostly to save some disk space and memory.

    Not that this overwrites the list of forbidden_keys that would be defined
    through configuration. That list is hard-coded in the __init__ function.
    """

    def __init__(self, config):
        super().__init__(config)

        # Overwrite the list of fields to redact away.
        self.forbidden_keys = ["StackTraces"]


# Valid Elasticsearch keys contain one or more ascii alphanumeric characters, underscore, and hyphen
# and that's it.
VALID_KEY = re.compile(r"^[a-zA-Z0-9_-]+$")


# Cache of (fields id, analyzer) -> list of fields properties
_ANALYZER_TO_FIELDS_MAP = {}


def get_fields_by_analyzer(fields, analyzer):
    """Returns the fields in fields that have the specified analyzer

    Note: This "hashes" the fields argument by using `id`. I think this is fine because
    fields don't change between runs and it's not mutated in-place. We're hashing it
    sufficiently often that it's faster to use `id` than a more computationally
    intensive hash of a large data structure.

    :arg dict fields: dict of field information mapped as field name to
        properties
    :arg str analyzer: the Elasticsearch analyzer to match

    :returns: list of field properties for fields that match the analyzer

    """
    map_key = (id(fields), analyzer)
    try:
        return _ANALYZER_TO_FIELDS_MAP[map_key]
    except KeyError:
        pass

    fields = [
        field
        for field in fields.values()
        if (field.get("storage_mapping") or {}).get("analyzer", "") == analyzer
    ]
    _ANALYZER_TO_FIELDS_MAP[map_key] = fields
    return fields


def is_valid_key(key):
    """Validates an Elasticsearch document key

    :arg string key: the key to validate

    :returns: True if it's valid and False if not

    """
    return bool(VALID_KEY.match(key))


def extract_indexable(fields, namespace, doc):
    """Builds a doc of all the keys that should be indexed

    This copies the data over, so the new doc is not tied to the original document at
    all and can be mutated safely.

    """
    new_doc = {}

    for field in FIELDS.values():
        if field["namespace"] != namespace:
            continue

        key = field["in_database_name"]
        if key in doc:
            new_doc[key] = copy.deepcopy(doc[key])

    return new_doc


def truncate_keyword_field_values(fields, data):
    """Truncates keyword field values greater than MAX_KEYWORD_FIELD_VALUE_SIZE length

    Note: This modifies the data dict in-place and only looks at the top level.

    :arg dict fields: the super search fields schema
    :arg dict data: the data to look through

    """
    keyword_fields = get_fields_by_analyzer(fields, "keyword")

    for field in keyword_fields:
        field_name = field.get("in_database_name")
        if not field_name:
            continue

        value = data.get(field_name)
        if isinstance(value, str) and len(value) > MAX_KEYWORD_FIELD_VALUE_SIZE:
            data[field_name] = value[:MAX_KEYWORD_FIELD_VALUE_SIZE]


def truncate_string_field_values(fields, data):
    """Truncates string field values greater than MAX_STRING_FIELD_VALUE_SIZE length

    Note: This modifies the data dict in-place and only looks at the top level.

    :arg dict fields: the super search fields schema
    :arg dict data: the data to look through

    """
    string_fields = [
        field
        for field in fields.values()
        if (field.get("storage_mapping") or {}).get("type", "") == "string"
    ]

    for field in string_fields:
        field_name = field.get("in_database_name")
        if not field_name:
            continue
        value = data.get(field_name)
        if not isinstance(value, str):
            continue

        new_value = value

        # First truncate down to MAX_STRING_FIELD_VALUE_SIZE
        try:
            if len(new_value.encode("utf-8")) > MAX_STRING_FIELD_VALUE_SIZE:
                new_value = new_value[:MAX_STRING_FIELD_VALUE_SIZE]

            # If the utf-8 encoded bytes is still larger, whittle off unicode
            # characters until it fits
            while len(new_value.encode("utf-8")) > MAX_STRING_FIELD_VALUE_SIZE:
                new_value = new_value[:-1]
        except UnicodeEncodeError:
            # If we hit a UnicodeEncodeError converting the unicode to utf-8, then the
            # string value is likely junk and we don't want it in Elasticsearch.
            new_value = "BAD DATA"

        if value != new_value:
            data[field_name] = new_value


POSSIBLE_TRUE_VALUES = [1, "1", "true", True]


def convert_booleans(fields, data):
    """Converts pseudo-boolean values to boolean values for boolean fields

    Valid boolean values are True, 'true', False, and 'false'.

    Note: This modifies the data dict in-place and only looks at the top level.

    :arg dict fields: the super search fields schema
    :arg dict data: the data to look through

    """
    boolean_fields = get_fields_by_analyzer(fields, "boolean")

    for field in boolean_fields:
        field_name = field["in_database_name"]

        value = data.get(field_name)
        data[field_name] = True if value in POSSIBLE_TRUE_VALUES else False


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

    def get_index_for_crash(self, crash_date):
        """Return submission URL for a crash; based on the submission URL
        from config and the date of the crash.

        If the index name contains a datetime pattern (ex. %Y%m%d) then the
        crash_date will be parsed and appended to the index name.

        """
        index = self.config.elasticsearch.elasticsearch_index

        if not index:
            return None
        elif "%" in index:
            # Note that crash_date must be a datetime object!
            index = crash_date.strftime(index)

        return index

    def prepare_processed_crash(self, raw_crash, processed_crash):
        """Returns prepared data

        This mutates the raw and processed crashes in place.

        """
        # Massage the crash such that the date_processed field is formatted in the
        # fashion of our established mapping
        reconstitute_datetimes(processed_crash)

        # Truncate values that are too long
        truncate_keyword_field_values(FIELDS, raw_crash)
        truncate_string_field_values(FIELDS, raw_crash)
        truncate_keyword_field_values(FIELDS, processed_crash)
        truncate_string_field_values(FIELDS, processed_crash)

        # Convert pseudo-boolean values to boolean values
        convert_booleans(FIELDS, raw_crash)
        convert_booleans(FIELDS, processed_crash)

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save processed crash report to Elasticsearch"""
        # Generate indexable raw and processed crash data and leave everything not
        # listed in FIELDS out
        raw_crash = extract_indexable(FIELDS, "raw_crash", raw_crash)
        processed_crash = extract_indexable(FIELDS, "processed_crash", processed_crash)

        # Clean up and redact raw and processed crash data
        self.prepare_processed_crash(raw_crash, processed_crash)

        # Capture crash data size metrics--do this only after we've cleaned up
        # the crash data
        self.capture_crash_metrics(raw_crash, processed_crash)

        crash_document = {
            "crash_id": processed_crash["uuid"],
            "processed_crash": processed_crash,
            "raw_crash": raw_crash,
        }

        self._submit_crash_to_elasticsearch(crash_document)

    def capture_crash_metrics(self, raw_crash, processed_crash):
        """Capture metrics about crash data being saved to Elasticsearch"""
        try:
            self.metrics.histogram(
                "raw_crash_size", value=len(json.dumps(raw_crash, cls=JsonDTEncoder))
            )
        except Exception:
            # NOTE(willkg): An error here shouldn't screw up saving data. Log it so we can fix it
            # later.
            self.logger.exception("something went wrong when capturing raw_crash_size")

        try:
            self.metrics.histogram(
                "processed_crash_size",
                value=len(json.dumps(processed_crash, cls=JsonDTEncoder)),
            )
        except Exception:
            # NOTE(willkg): An error here shouldn't screw up saving data. Log it so we can fix it
            # later.
            self.logger.exception(
                "something went wrong when capturing processed_crash_size"
            )

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

    def _submit_crash_to_elasticsearch(self, crash_document):
        """Submit a crash report to elasticsearch"""
        index_name = self.get_index_for_crash(
            crash_document["processed_crash"]["date_processed"]
        )
        es_doctype = self.config.elasticsearch.elasticsearch_doctype
        crash_id = crash_document["crash_id"]

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


class ESCrashStorageRedactedSave(ESCrashStorage):
    required_config = Namespace()
    required_config.namespace("es_redactor")
    required_config.es_redactor.add_option(
        name="redactor_class",
        doc="the name of the class that implements a 'redact' method",
        default="socorro.external.crashstorage_base.Redactor",
        from_string_converter=class_converter,
    )
    required_config.es_redactor.add_option(
        name="forbidden_keys",
        doc="a list of keys not allowed in a redacted processed crash",
        default=(
            "json_dump, "
            "upload_file_minidump_flash1.json_dump, "
            "upload_file_minidump_flash2.json_dump, "
            "upload_file_minidump_browser.json_dump"
        ),
        reference_value_from="resource.redactor",
    )

    required_config.namespace("raw_crash_es_redactor")
    required_config.raw_crash_es_redactor.add_option(
        name="redactor_class",
        doc="the redactor class to use on the raw_crash",
        default="socorro.external.es.crashstorage.RawCrashRedactor",
        from_string_converter=class_converter,
    )

    def __init__(self, config, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.redactor = config.es_redactor.redactor_class(config.es_redactor)
        self.raw_crash_redactor = config.raw_crash_es_redactor.redactor_class(
            config.raw_crash_es_redactor
        )

    def prepare_processed_crash(self, raw_crash, processed_crash):
        self.raw_crash_redactor.redact(raw_crash)
        self.redactor.redact(processed_crash)

        super().prepare_processed_crash(raw_crash, processed_crash)


class ESCrashStorageRedactedJsonDump(ESCrashStorageRedactedSave):
    """This class stores redacted crash reports into Elasticsearch, but instead
    of removing the entire `json_dump`, it keeps only a subset of its keys.
    """

    required_config = Namespace()
    required_config.add_option(
        name="json_dump_allowlist_keys",
        doc="keys of the json_dump field to keep in the processed crash",
        default=[
            "largest_free_vm_block",
            "tiny_block_size",
            "write_combine_size",
            "system_info",
        ],
        from_string_converter=list_converter,
    )

    required_config.namespace("es_redactor")
    required_config.es_redactor.add_option(
        name="redactor_class",
        doc="the name of the class that implements a 'redact' method",
        default="socorro.external.crashstorage_base.Redactor",
        from_string_converter=class_converter,
    )
    required_config.es_redactor.add_option(
        name="forbidden_keys",
        doc="a list of keys not allowed in a redacted processed crash",
        default=(
            "memory_report, "
            "upload_file_minidump_flash1.json_dump, "
            "upload_file_minidump_flash2.json_dump, "
            "upload_file_minidump_browser.json_dump"
        ),
        reference_value_from="resource.redactor",
    )

    def prepare_processed_crash(self, raw_crash, processed_crash):
        # Replace the `json_dump` with an allowed subset.
        json_dump = processed_crash.get("json_dump", {})
        redacted_json_dump = {
            k: json_dump.get(k) for k in self.config.json_dump_allowlist_keys
        }
        processed_crash["json_dump"] = redacted_json_dump

        super().prepare_processed_crash(raw_crash, processed_crash)

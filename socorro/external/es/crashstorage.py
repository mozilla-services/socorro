# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import re
from threading import Thread
from Queue import Queue
from contextlib import contextmanager

import elasticsearch
from configman import Namespace
from configman.converters import class_converter, list_converter

from socorro.external.crashstorage_base import CrashStorageBase
from socorro.lib.converters import change_default
from socorro.lib.datetimeutil import JsonDTEncoder, string_to_datetime
from socorro.external.crashstorage_base import Redactor


class RawCrashRedactor(Redactor):
    """Remove some specific keys from a dict. The dict is modified.

    This is a special Redactor used on raw crashes before we send them
    to our Elasticsearch database. It is used to remove fields that we don't
    need to store, in order mostly to save some disk space and memory.

    Not that this overwrites the list of forbidden_keys that would be defined
    through configuration. That list is hard-coded in the __init__ function.
    """
    def __init__(self, config):
        super(RawCrashRedactor, self).__init__(config)

        # Overwrite the list of fields to redact away.
        self.forbidden_keys = [
            'StackTraces',
        ]


# Valid Elasticsearch keys contain one or more ascii alphanumeric characters, underscore, and hyphen
# and that's it.
VALID_KEY = re.compile(r'^[a-zA-Z0-9_-]+$')


def is_valid_key(key):
    """Validates an Elasticsearch document key

    :arg string key: the key to validate

    :returns: True if it's valid and False if not

    """
    return bool(VALID_KEY.match(key))


class ESCrashStorage(CrashStorageBase):
    """This sends raw and processed crash reports to Elasticsearch."""

    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithLimitedBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
    )
    required_config.add_option(
        'index_creator_class',
        doc='a class that can create Elasticsearch indices',
        default='socorro.external.es.index_creator.IndexCreator',
        from_string_converter=class_converter
    )

    required_config.elasticsearch = Namespace()
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.elasticsearch',
    )

    # This cache reduces attempts to create indices, thus lowering overhead
    # each time a document is indexed.
    indices_cache = set()

    # These regex will catch field names from Elasticsearch exceptions. They
    # have been tested with Elasticsearch 1.4.
    field_name_string_error_re = re.compile(r'field=\"([\w\-.]+)\"')
    field_name_number_error_re = re.compile(
        r'\[failed to parse \[([\w\-.]+)]]'
    )

    def __init__(self, config, quit_check_callback=None):
        super(ESCrashStorage, self).__init__(
            config,
            quit_check_callback
        )

        # Ok, it's sane, so let's continue.
        self.es_context = self.config.elasticsearch.elasticsearch_class(
            config=self.config.elasticsearch
        )

        self.transaction = config.transaction_executor_class(
            config,
            self.es_context,
            quit_check_callback
        )

    def get_index_for_crash(self, crash_date):
        """Return the submission URL for a crash; based on the submission URL
        from config and the date of the crash.
        If the index name contains a datetime pattern (ex. %Y%m%d) then the
        crash_date will be parsed and appended to the index name.
        """

        index = self.config.elasticsearch.elasticsearch_index

        if not index:
            return None
        elif '%' in index:
            # Note that crash_date must be a datetime object!
            index = crash_date.strftime(index)

        return index

    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        """This is the only write mechanism that is actually employed in normal
        usage.
        """

        crash_document = {
            'crash_id': crash_id,
            'processed_crash': processed_crash,
            'raw_crash': raw_crash
        }

        # NOTE(willkg): this is a hard-coded keyname to match what the statsdbenchmarkingwrapper
        # produces for processor crashstorage classes. This is only used in that context, so we're
        # hard-coding this now rather than figuring out a better way to carry that name through.
        try:
            self.config.metrics.histogram(
                'processor.es.raw_crash_size',
                len(json.dumps(raw_crash, cls=JsonDTEncoder))
            )
        except Exception:
            # NOTE(willkg): An error here shouldn't screw up saving data. Log it so we can fix it
            # later.
            self.config.logger.exception('something went wrong when capturing raw_crash_size')

        try:
            self.config.metrics.histogram(
                'processor.es.processed_crash_size',
                len(json.dumps(processed_crash, cls=JsonDTEncoder))
            )
        except Exception:
            # NOTE(willkg): An error here shouldn't screw up saving data. Log it so we can fix it
            # later.
            self.config.logger.exception('something went wrong when capturing raw_crash_size')

        self.transaction(
            self._submit_crash_to_elasticsearch,
            crash_document=crash_document
        )

    @staticmethod
    def reconstitute_datetimes(processed_crash):
        datetime_fields = [
            'submitted_timestamp',
            'date_processed',
            'client_crash_date',
            'started_datetime',
            'startedDateTime',
            'completed_datetime',
            'completeddatetime',
        ]
        for a_key in datetime_fields:
            try:
                processed_crash[a_key] = string_to_datetime(
                    processed_crash[a_key]
                )
            except KeyError:
                # not there? we don't care
                pass

    @staticmethod
    def remove_bad_keys(data):
        """Removes keys from the top-level of the dict that are bad

        Good keys satisfy the following properties:

        * have one or more characters
        * are composed of a-zA-Z0-9_-

        Anything else is a bad key and needs to be removed.

        This modifies the data dict in-place and only looks at the top level.

        :arg dict data: the data to remove bad keys from

        """
        if not data:
            return

        # Copy the list of things we're iterating over because we're mutating
        # the dict in place.
        for key in list(data.keys()):
            if not is_valid_key(key):
                del data[key]

    def _submit_crash_to_elasticsearch(self, connection, crash_document):
        """Submit a crash report to elasticsearch.
        """
        # Massage the crash such that the date_processed field is formatted
        # in the fashion of our established mapping.
        self.reconstitute_datetimes(crash_document['processed_crash'])

        # Remove bad keys from the raw crash.
        self.remove_bad_keys(crash_document['raw_crash'])

        # Obtain the index name.
        es_index = self.get_index_for_crash(
            crash_document['processed_crash']['date_processed']
        )
        es_doctype = self.config.elasticsearch.elasticsearch_doctype
        crash_id = crash_document['crash_id']

        # Attempt to create the index; it's OK if it already exists.
        if es_index not in self.indices_cache:
            index_creator = self.config.index_creator_class(config=self.config)
            index_creator.create_socorro_index(es_index)

        # Submit the crash for indexing.
        # Don't retry more than 5 times. That is to avoid infinite loops in
        # case of an unhandled exception.
        for attempt in range(5):
            try:
                connection.index(
                    index=es_index,
                    doc_type=es_doctype,
                    body=crash_document,
                    id=crash_id
                )
                break
            except elasticsearch.exceptions.TransportError as e:
                field_name = None

                if 'MaxBytesLengthExceededException' in e.error:
                    # This is caused by a string that is way too long for
                    # Elasticsearch.
                    matches = self.field_name_string_error_re.findall(e.error)
                    if matches:
                        field_name = matches[0]
                elif 'NumberFormatException' in e.error:
                    # This is caused by a number that is either too big for
                    # Elasticsearch or just not a number.
                    matches = self.field_name_number_error_re.findall(e.error)
                    if matches:
                        field_name = matches[0]

                if not field_name:
                    # We are unable to parse which field to remove, we cannot
                    # try to fix the document. Let it raise.
                    self.config.logger.critical(
                        'Submission to Elasticsearch failed for %s (%s)',
                        crash_id,
                        e,
                        exc_info=True
                    )
                    raise

                if field_name.endswith('.full'):
                    # Remove the `.full` at the end, that is a special mapping
                    # construct that is not part of the real field name.
                    field_name = field_name.rstrip('.full')

                # Now remove that field from the document before trying again.
                field_path = field_name.split('.')
                parent = crash_document
                for i, field in enumerate(field_path):
                    if i == len(field_path) - 1:
                        # This is the last level, so `field` contains the name
                        # of the field that we want to remove from `parent`.
                        del parent[field]
                    else:
                        parent = parent[field]

                # Add a note in the document that a field has been removed.
                if crash_document.get('removed_fields'):
                    crash_document['removed_fields'] = '{} {}'.format(
                        crash_document['removed_fields'],
                        field_name
                    )
                else:
                    crash_document['removed_fields'] = field_name
            except elasticsearch.exceptions.ElasticsearchException as e:
                self.config.logger.critical(
                    'Submission to Elasticsearch failed for %s (%s)',
                    crash_id,
                    e,
                    exc_info=True
                )
                raise


class ESCrashStorageRedactedSave(ESCrashStorage):
    required_config = Namespace()
    required_config.namespace('es_redactor')
    required_config.es_redactor.add_option(
        name="redactor_class",
        doc="the name of the class that implements a 'redact' method",
        default='socorro.external.crashstorage_base.Redactor',
        from_string_converter=class_converter,
    )
    required_config.es_redactor.forbidden_keys = change_default(
        Redactor,
        "forbidden_keys",
        "json_dump, "
        "upload_file_minidump_flash1.json_dump, "
        "upload_file_minidump_flash2.json_dump, "
        "upload_file_minidump_browser.json_dump"
    )

    required_config.namespace('raw_crash_es_redactor')
    required_config.raw_crash_es_redactor.add_option(
        name="redactor_class",
        doc="the redactor class to use on the raw_crash",
        default='socorro.external.es.crashstorage.RawCrashRedactor',
        from_string_converter=class_converter,
    )

    def __init__(self, config, quit_check_callback=None):
        super(ESCrashStorageRedactedSave, self).__init__(
            config,
            quit_check_callback
        )
        self.redactor = config.es_redactor.redactor_class(config.es_redactor)
        self.raw_crash_redactor = config.raw_crash_es_redactor.redactor_class(
            config.raw_crash_es_redactor
        )
        self.config.logger.warning(
            "Beware, this crashstorage class is destructive to the "
            "processed crash - if you're using a polycrashstore you may "
            "find the modified processed crash saved to the other crashstores."
        )

    def is_mutator(self):
        # This crash storage mutates the crash, so we mark it as such.
        return True

    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        """This is the only write mechanism that is actually employed in normal
        usage.
        """
        self.redactor.redact(processed_crash)
        self.raw_crash_redactor.redact(raw_crash)

        super(ESCrashStorageRedactedSave, self).save_raw_and_processed(
            raw_crash,
            dumps,
            processed_crash,
            crash_id
        )


class ESCrashStorageRedactedJsonDump(ESCrashStorageRedactedSave):
    """This class stores redacted crash reports into Elasticsearch, but instead
    of removing the entire `json_dump`, it keeps only a subset of its keys.
    """
    required_config = Namespace()
    required_config.add_option(
        name="json_dump_whitelist_keys",
        doc="keys of the json_dump field to keep in the processed crash",
        default=[
            "largest_free_vm_block",
            "tiny_block_size",
            "write_combine_size",
            "system_info",
        ],
        from_string_converter=list_converter,
    )

    required_config.namespace('es_redactor')
    required_config.es_redactor.add_option(
        name="redactor_class",
        doc="the name of the class that implements a 'redact' method",
        default='socorro.external.crashstorage_base.Redactor',
        from_string_converter=class_converter,
    )
    required_config.es_redactor.forbidden_keys = change_default(
        Redactor,
        "forbidden_keys",
        (
            "memory_report, "
            "upload_file_minidump_flash1.json_dump, "
            "upload_file_minidump_flash2.json_dump, "
            "upload_file_minidump_browser.json_dump"
        )
    )

    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        """This is the only write mechanism that is actually employed in normal
        usage.
        """
        # Replace the `json_dump` with a subset.
        json_dump = processed_crash.get('json_dump', {})
        redacted_json_dump = {
            k: json_dump.get(k)
            for k in self.config.json_dump_whitelist_keys
        }
        processed_crash['json_dump'] = redacted_json_dump

        super(ESCrashStorageRedactedJsonDump, self).save_raw_and_processed(
            raw_crash,
            dumps,
            processed_crash,
            crash_id
        )


class QueueWrapper(Queue):
    """this class allows a queue to be a standin for a connection to an
    external resource.  The queue then becomes compatible with the
    TransactionExecutor classes"""

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    @contextmanager
    def __call__(self):
        yield self


class QueueContextSource(object):
    """this class allows a queue to be a standin for a connection to an
    external resource.  The queue then becomes compatible with the
    TransactionExecutor classes"""
    def __init__(self, a_queue):
        self.queue = a_queue

    @contextmanager
    def __call__(self):
        yield self.queue

    operational_exceptions = ()
    conditional_exceptions = ()


def _create_bulk_load_crashstore(base_class):

    class ESBulkClassTemplate(base_class):
        required_config = Namespace()
        required_config.add_option(
            'items_per_bulk_load',
            default=500,
            doc="the number of crashes that triggers a flush to ES"
        )
        required_config.add_option(
            'maximum_queue_size',
            default=512,
            doc='the maximum size of the internal queue'
        )

        def __init__(self, config, quit_check_callback=None):
            super(ESBulkClassTemplate, self).__init__(
                config,
                quit_check_callback
            )

            self.task_queue = QueueWrapper(config.maximum_queue_size)
            self.consuming_thread = Thread(
                name="ConsumingThread",
                target=self._consuming_thread_func
            )

            # overwrites original
            self.transaction = config.transaction_executor_class(
                config,
                QueueContextSource(self.task_queue),
                quit_check_callback
            )
            self.done = False
            self.consuming_thread.start()

        def _submit_crash_to_elasticsearch(self, queue, crash_document):
            # Massage the crash such that the date_processed field is formatted
            # in the fashion of our established mapping.
            # First create a datetime object from the string in the crash
            # report.
            self.reconstitute_datetimes(crash_document['processed_crash'])

            # Obtain the index name.
            es_index = self.get_index_for_crash(
                crash_document['processed_crash']['date_processed']
            )
            es_doctype = self.config.elasticsearch.elasticsearch_doctype
            crash_id = crash_document['crash_id']

            # Attempt to create the index; it's OK if it already exists.
            if es_index not in self.indices_cache:
                index_creator = self.config.index_creator_class(
                    config=self.config
                )
                index_creator.create_socorro_index(es_index)

            action = {
                '_index': es_index,
                '_type': es_doctype,
                '_id': crash_id,
                '_source': crash_document,
            }
            queue.put(action)

        def _consumer_iter(self):
            while True:
                try:
                    crash_document = self.task_queue.get()
                except Exception:
                    self.config.logger.critical(
                        "Failure in ES Bulktask_queue",
                        exc_info=True
                    )
                    crash_document = None
                if crash_document is None:
                    self.done = True
                    break
                yield crash_document  # execute the task

        def close(self):
            self.task_queue.put(None)
            self.consuming_thread.join()

        def _consuming_thread_func(self):  # execute the bulk load
            with self.es_context() as es:
                try:
                    elasticsearch.helpers.bulk(
                        es,
                        self._consumer_iter(),
                        chunk_size=self.config.items_per_bulk_load
                    )
                except Exception:
                    self.config.logger.critical(
                        "Failure in ES elasticsearch.helpers.bulk",
                        exc_info=True
                    )

    return ESBulkClassTemplate


ESBulkCrashStorage = _create_bulk_load_crashstore(ESCrashStorage)


ESBulkCrashStorageRedactedSave = _create_bulk_load_crashstore(
    ESCrashStorageRedactedSave
)


ESCrashStorageNoStackwalkerOutput = ESCrashStorageRedactedSave

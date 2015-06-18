# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch

from socorro.external.crashstorage_base import CrashStorageBase
from socorro.external.es.index_creator import IndexCreator
from socorro.lib import datetimeutil

from configman import Namespace
from configman.converters import class_converter


#==============================================================================
class ESCrashStorage(CrashStorageBase):
    """This sends processed crash reports to Elasticsearch."""

    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithLimitedBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
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

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        """Init, you know.
        """

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

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
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

        self.transaction(
            self._submit_crash_to_elasticsearch,
            crash_document=crash_document
        )

    #--------------------------------------------------------------------------
    def _submit_crash_to_elasticsearch(self, connection, crash_document):
        """Submit a crash report to elasticsearch.
        """

        # Massage the crash such that the date_processed field is formatted
        # in the fashion of our established mapping.
        # First create a datetime object from the string in the crash report.
        crash_date = datetimeutil.string_to_datetime(
            crash_document['processed_crash']['date_processed']
        )
        # Then convert it back to a string with the expected formatting.
        crash_date_with_t = datetimeutil.date_to_string(crash_date)
        # Finally, re-insert that string back into the report for indexing.
        crash_document['processed_crash']['date_processed'] = crash_date_with_t

        # Obtain the index name.
        es_index = self.get_index_for_crash(crash_date)
        es_doctype = self.config.elasticsearch.elasticsearch_doctype
        crash_id = crash_document['crash_id']

        # Attempt to create the index; it's OK if it already exists.
        if es_index not in self.indices_cache:
            index_creator = IndexCreator(config=self.config)
            index_creator.create_socorro_index(es_index)

        # Submit the crash for indexing.
        try:
            connection.index(
                index=es_index,
                doc_type=es_doctype,
                body=crash_document,
                id=crash_id
            )

        except elasticsearch.exceptions.ElasticsearchException as e:
            self.config.logger.critical(
                'Submission to Elasticsearch failed for %s (%s)',
                crash_id,
                e,
                exc_info=True
            )
            raise


from socorro.lib.converters import change_default
from socorro.lib.datetimeutil import string_to_datetime
from socorro.external.crashstorage_base import Redactor


#==============================================================================
class ESCrashStorageNoStackwalkerOutput(ESCrashStorage):
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

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        """Init, you know.
        """
        super(ESCrashStorageNoStackwalkerOutput, self).__init__(
            config,
            quit_check_callback
        )
        self.redactor = config.es_redactor.redactor_class(config.es_redactor)
        self.config.logger.warning(
            "beware, this crashstorage class is destructive to the "
            "processed crash - if you're using a polycrashstore you may "
            "find the modified processed crash saved to the other crashstores"
        )

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        """This is the only write mechanism that is actually employed in normal
        usage.
        """
        self.reconstitute_datetimes(processed_crash)
        self.redactor.redact(processed_crash)

        super(ESCrashStorageNoStackwalkerOutput, self).save_raw_and_processed(
            raw_crash,
            dumps,
            processed_crash,
            crash_id
        )


from threading import Thread
from Queue import Queue


#==============================================================================
class ESCrashBulkStorageNoStackwalkerOutput(ESCrashStorageNoStackwalkerOutput):
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

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(ESCrashBulkStorageNoStackwalkerOutput, self).__init__(
            config,
            quit_check_callback
        )

        self.task_queue = Queue(config.maximum_queue_size)
        self.consuming_thread = Thread(
            name="ConsumingThread",
            target=self._consuming_thread_func
        )

        # overwrites original
        self.transaction = config.transaction_executor_class(
            config,
            lambda: self.task_queue,
            quit_check_callback
        )
        self.done = False
        self.consuming_thread.start()

    #--------------------------------------------------------------------------
    def _submit_crash_to_elasticsearch(self, queue, crash_document):
        crash_date = datetimeutil.string_to_datetime(
            crash_document['processed_crash']['date_processed']
        )

        # Obtain the index name.
        es_index = self.get_index_for_crash(crash_date)
        es_doctype = self.config.elasticsearch.elasticsearch_doctype
        crash_id = crash_document['crash_id']

        # Attempt to create the index; it's OK if it already exists.
        if es_index not in self.indices_cache:
            index_creator = IndexCreator(config=self.config)
            index_creator.create_socorro_index(es_index)

        action = {
            '_index': es_index,
            '_type': es_doctype,
            '_id': crash_id,
            '_source': crash_document,
        }
        queue.put(action)

    #--------------------------------------------------------------------------
    def _consumer_iter(self):
        try:
            while True:
                crash_document = self.task_queue.get()
                if crash_document is None:
                    self.done = True
                    break
                try:
                    yield crash_document  # execute the task
                except Exception:
                    self.config.logger.error(
                        "Error in processing a job",
                        exc_info=True
                    )
        except Exception:
            self.config.logger.critical(
                "Failure in ES Bulktask_queue",
                exc_info=True
            )

    #--------------------------------------------------------------------------
    def close(self):
        self.task_queue.put(None)
        self.consuming_thread.join()

    #--------------------------------------------------------------------------
    def _consuming_thread_func(self):  # execute the bulk load
        es = self.es_context()
        elasticsearch.helpers.streaming_bulk(
            es,
            self._consumer_iter,
            chunk_size=self.items_per_bulk_load
        )

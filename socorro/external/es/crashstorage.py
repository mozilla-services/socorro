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


from copy import deepcopy
from socorro.lib.converters import change_default
from socorro.external.crashstorage_base import Redactor


#==============================================================================
class ESCrashStorageNoStackwalkerOutput(ESCrashStorage):
    required_config = Namespace()
    required_config.namespace('es_redactor')
    required_config.es_redactor.add_option(
        name="redactor_class",
        doc="the name of the class that implements a 'redact' method",
        default='socorro.external.crashstorage_base.Redactor',
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

    #--------------------------------------------------------------------------
    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        """This is the only write mechanism that is actually employed in normal
        usage.
        """

        copied_processed_crash = deepcopy(processed_crash)
        self.redactor.redact(copied_processed_crash)

        super(ESCrashStorageNoStackwalkerOutput, self).save_raw_and_processed(
            raw_crash,
            dumps,
            copied_processed_crash,
            crash_id
        )

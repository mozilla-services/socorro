# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import json
import os
import pyelasticsearch

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound
)
from socorro.lib import datetimeutil

from configman import Namespace
from configman.converters import class_converter, list_converter


#==============================================================================
class ElasticSearchCrashStorage(CrashStorageBase):
    """This class sends processed crash reports to elasticsearch. It handles
    indices creation and type mapping. It cannot store raw dumps or raw crash
    reports as Socorro doesn't need those in elasticsearch at the moment.
    """

    required_config = Namespace()
    required_config.add_option('transaction_executor_class',
                               default="socorro.database.transaction_executor."
                               "TransactionExecutorWithLimitedBackoff",
                               doc='a class that will manage transactions',
                               from_string_converter=class_converter,
                               reference_value_from='resource.elasticsearch')
    required_config.add_option('elasticsearch_urls',
                               doc='the urls to the elasticsearch instances '
                               '(leave blank to disable)',
                               default=['http://localhost:9200'],
                               from_string_converter=list_converter,
                               reference_value_from='resource.elasticsearch')
    required_config.add_option('elasticsearch_index',
                               doc='an index to insert crashes in '
                               'elasticsearch '
                               "(use datetime's strftime format to have "
                               'daily, weekly or monthly indexes)',
                               default='socorro%Y%W',
                               reference_value_from='resource.elasticsearch')
    required_config.add_option('elasticsearch_doctype',
                               doc='a type to insert crashes in elasticsearch',
                               default='crash_reports',
                               reference_value_from='resource.elasticsearch')
    required_config.add_option('elasticsearch_index_settings',
                               doc='the mapping of crash reports to insert',
                               default='%s/socorro_index_settings.json' % (
                                   os.path.dirname(os.path.abspath(__file__))),
                               reference_value_from='resource.elasticsearch')
    required_config.add_option('timeout',
                               doc='how long to wait in seconds for '
                                   'confirmation of a submission',
                               default=2,
                               reference_value_from='resource.elasticsearch')

    operational_exceptions = (
        pyelasticsearch.exceptions.ConnectionError,
        pyelasticsearch.exceptions.Timeout
    )

    conditional_exceptions = ()

    indices_cache = set()

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(ElasticSearchCrashStorage, self).__init__(
            config,
            quit_check_callback
        )
        self.transaction = config.transaction_executor_class(
            config,
            self,
            quit_check_callback
        )
        if self.config.elasticsearch_urls:
            self.es = pyelasticsearch.ElasticSearch(
                self.config.elasticsearch_urls,
                timeout=self.config.timeout
            )

            settings_json = open(
                self.config.elasticsearch_index_settings
            ).read()
            self.index_settings = json.loads(
                settings_json % self.config.elasticsearch_doctype
            )
        else:
            config.logger.warning('elasticsearch crash storage is disabled.')

    #--------------------------------------------------------------------------
    def save_processed(self, processed_crash):
        crash_id = processed_crash['uuid']
        crash_document = {
            'crash_id': crash_id,
            'processed_crash': processed_crash,
            'raw_crash': None
        }
        try:
            # Why is the function specified as unbound?  The elastic search
            # crashstorage class serves as its own connection context object.
            # In otherwords, it has no actual connection class.  The
            # transaction executor passes a connection object as the first
            # paremeter to the function that it calls.  That means that it will
            # be passing the ElasticSearchCrashStorage instance as the self
            # parameter.  A bound function would already have that input
            # parameter and thus an exception would be raised. By using an
            # unbound function, we avoid this problem.
            self.transaction(
                self.__class__._submit_crash_to_elasticsearch,
                crash_id,
                crash_document
            )
        except KeyError, x:
            if x == 'uuid':
                raise CrashIDNotFound
            raise

    #--------------------------------------------------------------------------
    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        crash_document = {
            'crash_id': crash_id,
            'processed_crash': processed_crash,
            'raw_crash': raw_crash,
        }

        self.transaction(
            self.__class__._submit_crash_to_elasticsearch,
            crash_id,
            crash_document
        )

    #--------------------------------------------------------------------------
    def _submit_crash_to_elasticsearch(self, crash_id, crash_document):
        """submit a crash report to elasticsearch.

        Generate the index name from the date of the crash report, verify that
        index already exists, and if it doesn't create it and set its mapping.
        Lastly index the crash report.
        """
        if not self.config.elasticsearch_urls:
            return

        crash_date = datetimeutil.string_to_datetime(
            crash_document['processed_crash']['date_processed']
        )
        es_index = self.get_index_for_crash(crash_date)
        es_doctype = self.config.elasticsearch_doctype

        try:
            # We first need to ensure that the index already exists in ES.
            # If it doesn't, we create it and put its mapping.
            self.create_index(es_index)

            self.es.index(
                es_index,
                es_doctype,
                crash_document,
                id=crash_id,
                replication='async'
            )
        except pyelasticsearch.exceptions.ConnectionError:
            self.logger.critical('%s may not have been submitted to '
                                 'elasticsearch due to a connection error',
                                 crash_id)
            raise
        except pyelasticsearch.exceptions.Timeout:
            self.logger.critical('%s may not have been submitted to '
                                 'elasticsearch due to a timeout',
                                 crash_id)
            raise
        except pyelasticsearch.exceptions.ElasticHttpError, e:
            self.logger.critical(u'%s may not have been submitted to '
                                 'elasticsearch due to the following: %s',
                                 crash_id, e)
            raise
        except Exception:
            self.logger.critical('Submission to elasticsearch failed for %s',
                                 crash_id,
                                 exc_info=True)
            raise

    #--------------------------------------------------------------------------
    def get_index_for_crash(self, crash_date):
        """return the submission URL for a crash, based on the submission URL
        in config and the date of the crash"""
        index = self.config.elasticsearch_index

        if not index:
            return None
        elif '%' in index:
            index = crash_date.strftime(index)

        return index

    #--------------------------------------------------------------------------
    def create_index(self, es_index):
        # We first need to ensure that the index already exists in ES.
        # If it doesn't, we create it and put its mapping.
        if es_index not in self.indices_cache:
            try:
                self.es.status(es_index)
            except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
                try:
                    self.es.create_index(
                        es_index,
                        settings=self.index_settings
                    )
                except pyelasticsearch.exceptions.IndexAlreadyExistsError:
                    # If another processor concurrently created this
                    # index, swallow the error
                    pass

            # Cache the list of existing indices to avoid HTTP requests
            self.indices_cache.add(es_index)

    # TODO: Kill these connection-like methods.
    # What are they doing in a crash storage?
    #--------------------------------------------------------------------------
    def commit(self):
        """elasticsearch doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    def rollback(self):
        """elasticsearch doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self):
        """this class will serve as its own context manager.  That enables it
        to use the transaction_executor class for retries"""
        yield self

    #--------------------------------------------------------------------------
    def in_transaction(self, dummy):
        """elasticsearch doesn't support transactions, so it is never in
        a transaction."""
        return False

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        return False
    # Down to at least here^^^

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        pass

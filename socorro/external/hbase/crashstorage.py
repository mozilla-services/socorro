# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os

from socorro.external.crashstorage_base import (
    CrashStorageBase, CrashIDNotFound)
from socorro.external.hbase import hbase_client
from socorro.database.transaction_executor import TransactionExecutor
from socorro.external.hbase.connection_context import \
     HBaseConnectionContextPooled
from socorro.lib.util import DotDict
from configman import Namespace, class_converter


#==============================================================================
class HBaseCrashStorage(CrashStorageBase):

    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default=TransactionExecutor,
        doc='a class that will execute transactions',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'hbase_connection_pool_class',
        default=HBaseConnectionContextPooled,
        doc='the class responsible for pooling and giving out HBase'
            'connections'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(HBaseCrashStorage, self).__init__(config, quit_check_callback)

        self.logger.info('connecting to hbase')
        self.hbaseConnectionPool = config.hbase_connection_pool_class(config)

        self.transaction_executor = config.transaction_executor_class(
            config,
            self.hbaseConnectionPool,
            self.quit_check
        )

        self.exceptions_eligible_for_retry += \
            self.hbaseConnectionPool.operational_exceptions

    #--------------------------------------------------------------------------
    def close(self):
        self.hbaseConnectionPool.close()

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        # the transaction_executor will run the function given as the first
        # parameter.  To that function, the transaction_executor will pass
        # self.hbaseConnection, crash_id, raw_crash, dump, and
        # number_of_retries.
        # notice that the function is an unbound method.  Since
        # self.hbaseConnection is passed in as the first parameter, that
        # fills in the proper value for the function's 'self' parameter.
        # warning: this breaks inheritance if a subclass of
        # HBaseConnectionForCrashReports were desired instead.
        self.transaction_executor(
            hbase_client.HBaseConnectionForCrashReports.put_json_dump,
            crash_id,
            raw_crash,
            dumps,
            number_of_retries=self.config.number_of_retries
        )

        self.logger.info('saved - %s', crash_id)

    #--------------------------------------------------------------------------
    def save_processed(self, processed_crash):
        sanitized_processed_crash = self.sanitize_processed_crash(
          processed_crash,
          self.config.forbidden_keys
        )
        self._stringify_dates_in_dict(sanitized_processed_crash)
        self.transaction_executor(
          hbase_client.HBaseConnectionForCrashReports.put_processed_json,
          sanitized_processed_crash['uuid'],
          sanitized_processed_crash,
          number_of_retries=self.config.number_of_retries
        )

    #--------------------------------------------------------------------------
    def get_raw_crash(self, crash_id):
        return DotDict(self.transaction_executor(
            hbase_client.HBaseConnectionForCrashReports.get_json,
            crash_id,
            number_of_retries=self.config.number_of_retries
        ))

    #--------------------------------------------------------------------------
    def get_raw_dump(self, crash_id, name=None):
        return self.transaction_executor(
            hbase_client.HBaseConnectionForCrashReports.get_dump,
            crash_id,
            name,
            number_of_retries=self.config.number_of_retries
        )

    #--------------------------------------------------------------------------
    def get_raw_dumps(self, crash_id):
        return self.transaction_executor(
            hbase_client.HBaseConnectionForCrashReports.get_dumps,
            crash_id,
            number_of_retries=self.config.number_of_retries
        )
    #--------------------------------------------------------------------------
    def get_raw_dumps_as_files(self, crash_id):
        """this method fetches a set of dumps from HBase and writes each one
        to a temporary file.  The pathname for the dump includes the string
        'TEMPORARY' as a signal to the processor that it has the responsibilty
        to delete the file when it is done using it."""
        dumps_mapping = self.transaction_executor(
            hbase_client.HBaseConnectionForCrashReports.get_dumps,
            crash_id,
            number_of_retries=self.config.number_of_retries
        )
        name_to_pathname_mapping = {}
        for name, dump in dumps_mapping.iteritems():
            dump_pathname = os.path.join(
                self.config.temporary_file_system_storage_path,
                "%s.%s.TEMPORARY%s" % (crash_id,
                                       name,
                                       self.config.dump_file_suffix)
            )
            name_to_pathname_mapping[name] = dump_pathname
            with open(dump_pathname, 'wb') as f:
                f.write(dump)
        return name_to_pathname_mapping

    #--------------------------------------------------------------------------
    def get_processed(self, crash_id):
        try:
            return DotDict(self.transaction_executor(
               hbase_client.HBaseConnectionForCrashReports.get_processed_json,
               crash_id,
               number_of_retries=self.config.number_of_retries
            ))
        except hbase_client.OoidNotFoundException:
            # we want a consistent set of exceptions for the API
            raise CrashIDNotFound(crash_id)

    #--------------------------------------------------------------------------
    def new_crashes(self):
        connection = self.hbaseConnectionPool.connection()
        return connection.iterator_for_all_legacy_to_be_processed()

    #--------------------------------------------------------------------------
    @staticmethod
    def sanitize_processed_crash(processed_crash, forbidden_keys):
        """returns a copy of a processed_crash with the forbidden keys removed.

        parameters:
            processed_crash - the processed crash in the form of a mapping
            forbidden_keys - a list of strings to be removed from the
                             processed crash

        returns:
            a mapping that is a shallow copy of the original processed_crash
            minus the forbidden keys and values"""

        a_copy = processed_crash.copy()
        for a_forbidden_key in forbidden_keys:
            if a_forbidden_key in a_copy:
                del a_copy[a_forbidden_key]
        return a_copy

    #--------------------------------------------------------------------------
    @staticmethod
    def _stringify_dates_in_dict(a_dict):
        for name, value in a_dict.iteritems():
            if isinstance(value, datetime.datetime):
                a_dict[name] = ("%4d-%02d-%02d %02d:%02d:%02d.%d" %
                  (value.year,
                   value.month,
                   value.day,
                   value.hour,
                   value.minute,
                   value.second,
                   value.microsecond)
                )

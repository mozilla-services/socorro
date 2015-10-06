# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import os

from socorro.external.happybase.connection_context import \
    HappyBaseConnectionContext
from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    MemoryDumpsMapping,
    FileDumpsMapping
)
from socorro.lib.util import DotDict

from configman import Namespace, class_converter


class BadCrashIDException(ValueError):
    pass


def crash_id_to_row_id(crash_id):
    """
    Returns a row_id suitable for the HBase crash_reports table.
    The first hex character of the crash_id is used to "salt" the rowkey
    so that there should always be 16 HBase RegionServers responsible
    for dealing with the current stream of data.
    Then, we put the last six digits of the crash_id which represent the
    submission date. This lets us easily scan through the crash_reports
    table by day.
    Finally, we append the normal crash_id string.
    """
    try:
        return "%s%s%s" % (crash_id[0], crash_id[-6:], crash_id)
    except Exception, x:
        raise BadCrashIDException(x)


def row_id_to_crash_id(row_id):
    """
    Returns the natural ooid given an HBase row key.
    See ooid_to_row_id for structure of row_id.
    """
    try:
        return row_id[7:]
    except Exception, x:
        raise BadCrashIDException(x)


def crash_id_to_timestamped_row_id(crash_id, timestamp):
    """
    Returns a row_id suitable for the HBase crash_reports index tables.
    The first hex character of the ooid is used to "salt" the rowkey
    so that there should always be 16 HBase RegionServers responsible
    for dealing with the current stream of data.
    Then, we put the crash_report submission timestamp. This lets us
    easily scan through a time specific region of the index.
    Finally, we append the normal ooid string for uniqueness.
    """
    if timestamp[-6] in "-+":
        return "%s%s%s" % (crash_id[0], timestamp[:-6], crash_id)
    return "%s%s%s" % (crash_id[0], timestamp, crash_id)


class HBaseCrashStorage(CrashStorageBase):
    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
                "TransactionExecutorWithInfiniteBackoff",
        doc='a class that will execute transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.hb',
    )
    required_config.add_option(
        'hbase_connection_context_class',
        default=HappyBaseConnectionContext,
        doc='the class responsible for proving an hbase connection',
        reference_value_from='resource.hb',
    )

    def __init__(self, config, quit_check_callback=None):
        super(HBaseCrashStorage, self).__init__(
            config,
            quit_check_callback
        )
        self.logger.info('connecting to hbase via happybase')
        self.hbase = config.hbase_connection_context_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.hbase,
            quit_check_callback=quit_check_callback
        )

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        row_id = crash_id_to_row_id(crash_id)
        submitted_timestamp = raw_crash['submitted_timestamp']

        columns_and_values = {
            "flags:processed": "N",
            "meta_data:json": json.dumps(raw_crash),
            "timestamps:submitted": submitted_timestamp,
            "ids:ooid": crash_id,
        }
        # we don't know where the dumps came from, they could be in
        # in the form of names to binary blobs or names to pathnames.
        # this call ensures that we've got the former.
        in_memory_dumps = dumps.as_memory_dumps_mapping()
        for key, dump in in_memory_dumps.iteritems():
            if key in (None, '', 'upload_file_minidump'):
                key = 'dump'
            columns_and_values['raw_data:%s' % key] = dump

        def do_save(connection, raw_crash, in_memory_dumps, crash_id):
            crash_report_table = connection.table('crash_reports')
            crash_report_table.put(
                row_id,
                columns_and_values
            )
        self.transaction(do_save, raw_crash, in_memory_dumps, crash_id)

    def save_processed(self, processed_crash):
        crash_id = processed_crash['uuid']
        row_id = crash_id_to_row_id(crash_id)
        columns_and_values = {
            "timestamps:processed": processed_crash['completeddatetime'],
            "processed_data:signature": processed_crash['signature'],
            "processed_data:json": json.dumps(
                processed_crash
            ),
            "flags:processed": ""
        }

        def do_save(connection, processed_crash):
            crash_report_table = connection.table('crash_reports')
            crash_report_table.put(
                row_id,
                columns_and_values
            )

        self.transaction(do_save, processed_crash)

    def get_raw_crash(self, crash_id):
        row_id = crash_id_to_row_id(crash_id)

        def _do_get_raw_crash(connection, row_id):
            crash_report_table = connection.table('crash_reports')
            try:
                return crash_report_table.row(
                    row_id,
                    columns=['meta_data:json']
                )['meta_data:json']
            except KeyError:
                raise CrashIDNotFound(crash_id)
        raw_crash_json_str =  self.transaction(_do_get_raw_crash, row_id)
        raw_crash = json.loads(raw_crash_json_str, object_hook=DotDict)
        return raw_crash

    def get_raw_dump(self, crash_id, name=None):
        row_id = crash_id_to_row_id(crash_id)
        if name in (None, '', 'upload_file_minidump'):
            name = 'dump'
        column_name = 'raw_data:%s' % name
        def do_get(connection, row_id, name):
            crash_report_table = connection.table('crash_reports')
            try:
                return crash_report_table.row(
                    row_id,
                    columns=[column_name]
                )[column_name]
            except KeyError:
                raise CrashIDNotFound(crash_id)
        return self.transaction(do_get, row_id, name)

    @staticmethod
    def _make_dump_name(family_qualifier):
        name = family_qualifier.split(':')[1]
        if name == 'dump':
            name = 'upload_file_minidump'
        return name

    def get_raw_dumps(self, crash_id):
        row_id = crash_id_to_row_id(crash_id)

        def do_get(connection, row_id):
            try:
                crash_report_table = connection.table('crash_reports')
                dumps = crash_report_table.row(
                    row_id,
                    columns=['raw_data']
                )
                # ensure that we return a proper mapping of names to
                # binary blobs.
                return MemoryDumpsMapping(
                    (self._make_dump_name(k), v) for k, v in dumps.iteritems()
                )
            except KeyError:
                raise CrashIDNotFound(crash_id)

        return self.transaction(do_get, row_id)

    def get_raw_dumps_as_files(self, crash_id):
        in_memory_dumps = self.get_raw_dumps(crash_id)
        # convert our in memory name/blob data into name/pathname data
        return in_memory_dumps.as_file_dumps_mapping(
            crash_id,
            self.hbase.config.temporary_file_system_storage_path,
            self.hbase.config.dump_file_suffix
        )


    def get_unredacted_processed(self, crash_id):
        row_id = crash_id_to_row_id(crash_id)

        def do_get(connection, row_id):
            crash_report_table = connection.table('crash_reports')
            try:
                return crash_report_table.row(
                    row_id,
                    columns=['processed_data:json']
                )['processed_data:json']
            except KeyError:
                raise CrashIDNotFound(crash_id)
        processed_crash_json_str = self.transaction(do_get, row_id)
        processed_crash = json.loads(
            processed_crash_json_str,
            object_hook=DotDict
        )
        return processed_crash


# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import heapq
import itertools
import json
import os

from socorro.external.crashstorage_base import (
    CrashStorageBase, CrashIDNotFound)
from socorro.database.transaction_executor import TransactionExecutor
from socorro.external.hb.connection_context import \
     HBaseConnectionContext
from socorro.lib.util import DotDict
from configman import Namespace, class_converter

from hbase.Hbase import Client, ColumnDescriptor, Mutation


class BadCrashIDException(ValueError): pass


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
        'new_crash_limit',
        default=10 ** 6,
        doc='the maximum number of new crashes to yield at a time'
    )
    required_config.add_option(
        'transaction_executor_class',
        default=TransactionExecutor,
        doc='a class that will execute transactions',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'hbase_connection_context_class',
        default=HBaseConnectionContext,
        doc='the class responsible for proving an hbase connection'
    )

    def __init__(self, config, quit_check_callback=None):
        super(HBaseCrashStorage, self).__init__(config, quit_check_callback)
        self.logger.info('connecting to hbase')
        self.hbase = config.hbase_connection_context_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.hbase,
            quit_check_callback=quit_check_callback
        )

    def _wrap_in_transaction(self, f):
        """This decorator takes a function wraps it in a transaction context.
        The function being wrapped will take the connection as an argument."""
        return lambda: self.transaction(lambda conn_ctx: f(conn_ctx.client))

    def close(self):
        self.hbase.close()

    def _salted_scanner_iterable(self, client, salted_prefix, scanner):
        """Generator based iterable that runs over an HBase scanner
        yields a tuple of the un-salted rowkey and the nice format of the
        row."""
        self.logger.debug('Scanner %s generated', salted_prefix)
        raw_rows = client.scannerGet(scanner)
        while raw_rows:
            nice_row = self._make_row_nice(raw_rows[0])
            yield (nice_row['_rowkey'][1:], nice_row)
            raw_rows = client.scannerGet(scanner)
        self.logger.debug('Scanner %s exhausted' % salted_prefix)
        client.scannerClose(scanner)

    @staticmethod
    def _make_row_nice(client_row_object):
        columns = dict(
          ((x, y.value) for x, y in client_row_object.columns.items())
        )
        columns['_rowkey'] = client_row_object.row
        return columns

    def _get_report_processing_state(self, client, crash_id):
        """Return the current state of processing for this report and the
        submitted_timestamp needed. For processing queue manipulation.
        If the ooid doesn't exist, return an empty array"""
        raw_rows = client.getRowWithColumns('crash_reports',
                                          crash_id_to_row_id(crash_id),
                                          ['flags:processed',
                                           'flags:legacy_processing',
                                           'timestamps:submitted',
                                           'timestamps:processed'])

        if raw_rows:
            return self._make_row_nice(raw_rows[0])
        else:
            raise CrashIDNotFound(crash_id)

    def _put_crash_report_indices(self, client, crash_id, timestamp, indices):
        row_id = crash_id_to_timestamped_row_id(crash_id, timestamp)
        for index_name in indices:
            client.mutateRow(index_name, row_id,
                          [Mutation(column="ids:ooid", value=crash_id)])

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        @self._wrap_in_transaction
        def transaction(client):
            row_id = crash_id_to_row_id(crash_id)
            submitted_timestamp = raw_crash['submitted_timestamp']

            legacy_processing = raw_crash.get('legacy_processing', False)

            columns = [("flags:processed",       "N"),
                       ("meta_data:json",        json.dumps(raw_crash)),
                       ("timestamps:submitted",  submitted_timestamp),
                       ("ids:ooid",              crash_id)
                      ]

            for key, dump in dumps.iteritems():
                if key in (None, '', 'upload_file_minidump'):
                    key = 'dump'
                columns.append(('raw_data:%s' % key, dump))

            mutations = [Mutation(column=c, value=v)
                         for c, v in columns if v is not None]

            indices = [
              'crash_reports_index_submitted_time',
              'crash_reports_index_unprocessed_flag'
            ]

            if legacy_processing == 0:
                mutations.append(Mutation(column="flags:legacy_processing",
                                          value='Y'))
                indices.append('crash_reports_index_legacy_unprocessed_flag')
                indices.append('crash_reports_index_legacy_submitted_time')

            process_type = raw_crash.get('ProcessType', 'default')

            is_hang = 'HangID' in raw_crash

            if is_hang:
                hang_id = raw_crash['HangID']
                mutations.append(Mutation(column="ids:hang", value=hang_id))

            client.mutateRow('crash_reports', row_id, mutations)
            self._put_crash_report_indices(client, crash_id, submitted_timestamp,
                                           indices)

            if is_hang:
                # Put the hang's indices.
                ooid_column_name = "ids:ooid:" + process_type
                client.mutateRow(
                  'crash_reports_index_hang_id_submitted_time',
                  crash_id_to_timestamped_row_id(hang_id, submitted_timestamp),
                  [Mutation(column=ooid_column_name, value=crash_id)]
                )
                client.mutateRow(
                  'crash_reports_index_hang_id',
                  hang_id,
                  [Mutation(column=ooid_column_name, value=crash_id)]
                )

            # update the metrics
            time_levels = [
              submitted_timestamp[:16],  # minute yyyy-mm-ddTHH:MM
              submitted_timestamp[:13],  # hour   yyyy-mm-ddTHH
              submitted_timestamp[:10],  # day    yyyy-mm-dd
              submitted_timestamp[: 7],  # month  yyyy-mm
              submitted_timestamp[: 4]   # year   yyyy
            ]
            counter_increments = ['counters:submitted_crash_reports']
            counter_increments.append(
              "counters:submitted_crash_reports_legacy_throttle_%d"
              % legacy_processing
            )
            if process_type != 'default':
                if is_hang:
                    counter_increments.append(
                      "counters:submitted_crash_report_hang_pairs"
                    )
                else:
                    counter_increments.append(
                      "counters:submitted_oop_%s_crash_reports" % process_type
                    )

                client.atomicIncrement(
                  'metrics',
                  'crash_report_queue',
                  'counters:current_unprocessed_size',
                  1
                )
                if legacy_processing == 0:
                    client.atomicIncrement(
                      'metrics',
                      'crash_report_queue',
                      'counters:current_legacy_unprocessed_size',
                      1
                    )

            for rowkey in time_levels:
                for column in counter_increments:
                    client.atomicIncrement('metrics', rowkey, column, 1)

        self.logger.info('saved - %s', crash_id)
        return transaction()

    def save_processed(self, processed_crash):
        @self._wrap_in_transaction
        def transaction(client, processed_crash=processed_crash):
            processed_crash = processed_crash.copy()

            crash_id = processed_crash['uuid']

            for k in self.config.forbidden_keys:
                if k in processed_crash:
                    del processed_crash[k]

            self._stringify_dates_in_dict(processed_crash)

            row_id = crash_id_to_row_id(crash_id)

            processing_state = self._get_report_processing_state(client, crash_id)
            submitted_timestamp = processing_state.get(
              'timestamps:submitted',
              processed_crash.get('date_processed', 'unknown')
            )

            if processing_state.get('flags:processed', '?') == 'N':
                index_row_key = crash_id_to_timestamped_row_id(
                  crash_id,
                  submitted_timestamp
                )
                client.atomicIncrement('metrics',
                                     'crash_report_queue',
                                     'counters:current_unprocessed_size',
                                     -1)
                client.deleteAllRow('crash_reports_index_unprocessed_flag',
                                  index_row_key)

            processed_timestamp = processed_crash['completeddatetime']

            if 'signature' in processed_crash:
                if len(processed_crash['signature']) > 0:
                    signature = processed_crash['signature']
                else:
                    signature = '##empty##'
            else:
                signature = '##null##'

            mutations = []
            mutations.append(Mutation(column="timestamps:processed",
                                      value=processed_timestamp))
            mutations.append(Mutation(column="processed_data:signature",
                                      value=signature))
            mutations.append(Mutation(column="processed_data:json",
                                      value=json.dumps(processed_crash)))
            mutations.append(Mutation(column="flags:processed",
                                      value="Y"))

            client.mutateRow('crash_reports', row_id, mutations)

            sig_ooid_idx_row_key = signature + crash_id
            client.mutateRow(
              'crash_reports_index_signature_ooid',
              sig_ooid_idx_row_key,
              [Mutation(column="ids:ooid", value=crash_id)]
            )
        return transaction()

    def get_raw_crash(self, crash_id):
        @self._wrap_in_transaction
        def transaction(client):
            row_id = crash_id_to_row_id(crash_id)
            raw_rows = client.getRowWithColumns('crash_reports',
                                              row_id,
                                              ['meta_data:json'])
            try:
                if raw_rows:
                    row_column = raw_rows[0].columns["meta_data:json"].value
                else:
                    raise CrashIDNotFound(crash_id)
            except KeyError:
                self.logger.debug(
                  'key error trying to get "meta_data:json" for %s',
                  crash_id
                )
                raise

            return json.loads(row_column, object_hook=DotDict)
        return transaction()

    def get_raw_dump(self, crash_id, name=None):
        """Return the minidump for a given crash_id as a string of bytes
        If the crash_id doesn't exist, raise not found"""
        @self._wrap_in_transaction
        def transaction(client):
            if name in (None, '', 'upload_file_minidump'):
                name = 'dump'
            column_family_and_qualifier = 'raw_data:%s' % name
            row_id = crash_id_to_row_id(crash_id)
            raw_rows = client.getRowWithColumns('crash_reports',
                                              row_id,
                                              [column_family_and_qualifier])

            try:
                if raw_rows:
                    return raw_rows[0].columns[column_family_and_qualifier].value
                else:
                    raise CrashIDNotFound(crash_id)
            except KeyError:
                self.logger.debug(
                  'key error trying to get "%s" for %s',
                  (column_family_and_qualifier, crash_id)
                )
                raise
        return transaction()

    @staticmethod
    def _make_dump_name(family_qualifier):
        name = family_qualifier.split(':')[1]
        if name == 'dump':
            name = 'upload_file_minidump'
        return name

    def get_raw_dumps(self, crash_id):
        """Return the minidump for a given ooid as a string of bytes
        If the ooid doesn't exist, raise not found"""
        @self._wrap_in_transaction
        def transaction(client):
            row_id = crash_id_to_row_id(crash_id)
            raw_rows = client.getRowWithColumns('crash_reports',
                                              row_id,
                                              ['raw_data'])
            try:
                if raw_rows:
                    column_mapping = raw_rows[0].columns
                    d = dict([
                        (self._make_dump_name(k), v.value)
                            for k, v in column_mapping.iteritems()])
                    return d
                else:
                    raise CrashIDNotFound(crash_id)
            except KeyError:
                self.logger.debug(
                  'key error trying to get "raw_data" from %s',
                  crash_id
                )
                raise
        return transaction()

    def get_raw_dumps_as_files(self, crash_id):
        """this method fetches a set of dumps from HBase and writes each one
        to a temporary file.  The pathname for the dump includes the string
        'TEMPORARY' as a signal to the processor that it has the responsibilty
        to delete the file when it is done using it."""
        @self._wrap_in_transaction
        def transaction(client):
            dumps_mapping = self.get_raw_dumps(crash_id)

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
        return transaction()

    def get_processed(self, crash_id):
        """Return the cooked json (jsonz) for a given ooid as a string
        If the ooid doesn't exist, return an empty string."""
        @self._wrap_in_transaction
        def transaction(client):
            row_id = crash_id_to_row_id(crash_id)
            raw_rows = client.getRowWithColumns('crash_reports',
                                              row_id,
                                              ['processed_data:json'])

            if raw_rows:
                row_columns = raw_rows[0].columns["processed_data:json"].value
            else:
                raise CrashIDNotFound(crash_id)

            return json.loads(row_columns, object_hook=DotDict)
        return transaction()

    def new_crashes(self):
        try:
            with self.hbase() as context:
                for row in itertools.islice(
                  self._merge_scan_with_prefix(
                    context.client,
                    'crash_reports_index_legacy_unprocessed_flag',
                    '',
                    ['ids:ooid']
                  ),
                  self.config.new_crash_limit
                ):
                    self._delete_from_legacy_processing_index(context.client,
                                                              row['_rowkey'])
                    yield row['ids:ooid']
        except self.hbase.operational_exceptions:
            self.hbase.force_reconnect()
            self.config.logger.critical(
                'hbase is in trouble, forcing reconnect',
                exc_info=True
            )

    def _union_scan_with_prefix(self, client, table, prefix, columns):
        # TODO: Need assertion for columns contains at least 1 element
        """A lazy chain of iterators that yields unordered rows starting with
        a given prefix. The implementation opens up 16 scanners (one for each
        leading hex character of the salt) one at a time and returns all of
        the rows matching"""
        for salt in '0123456789abcdef':
            salted_prefix = "%s%s" % (salt, prefix)
            scanner = client.scannerOpenWithPrefix(table,
                                                 salted_prefix,
                                                 columns)
            for rowkey, row in self._salted_scanner_iterable(client,
                                                             salted_prefix,
                                                             scanner):
                yield row

    def _merge_scan_with_prefix(self, client, table, prefix, columns):
        # TODO: Need assertion that columns is array containing at least
        # one string
        """A generator based iterator that yields totally ordered rows starting
        with a given prefix. The implementation opens up 16 scanners (one for
        each leading hex character of the salt) simultaneously and then yields
        the next row in order from the pool on each iteration."""
        iterators = []
        next_items_queue = []
        for salt in '0123456789abcdef':
            salted_prefix = "%s%s" % (salt, prefix)
            scanner = client.scannerOpenWithPrefix(table,
                                                 salted_prefix,
                                                 columns)
            iterators.append(self._salted_scanner_iterable(client,
                                                           salted_prefix,
                                                           scanner))
        # The i below is so we can advance whichever scanner delivers us the
        # polled item.
        for i, it in enumerate(iterators):
            try:
                next = it.next
                next_items_queue.append([next(), i, next])
            except StopIteration:
                pass
        heapq.heapify(next_items_queue)

        while True:
            try:
                while True:
                    row_tuple, iter_index, next = s = next_items_queue[0]
                    # tuple[1] is the actual nice row.
                    yield row_tuple[1]
                    s[0] = next()
                    heapq.heapreplace(next_items_queue, s)
            except StopIteration:
                heapq.heappop(next_items_queue)
            except IndexError:
                return

    def _delete_from_legacy_processing_index(self, client, index_row_key):
        client.deleteAllRow('crash_reports_index_legacy_unprocessed_flag',
                          index_row_key)

        client.atomicIncrement('metrics',
                             'crash_report_queue',
                             'counters:current_legacy_unprocessed_size',
                             -1)

    @staticmethod
    def _stringify_dates_in_dict(items):
        for k, v in items.iteritems():
            if isinstance(v, datetime.datetime):
                items[k] = v.strftime("%Y-%m-%d %H:%M:%S.%f")
        return items

#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import itertools
import os
import gzip
import heapq
import time
import tarfile
import random
import contextlib

import socket

from thrift import Thrift  # get module
from thrift.transport import TSocket, TTransport  # get modules
from thrift.protocol import TBinaryProtocol  # get module
from hbase import ttypes  # get module
from hbase.Hbase import Client, ColumnDescriptor, Mutation  # get classes

import socorro.lib.util as utl
from socorro.lib.util import DotDict


class HBaseClientException(Exception):
    pass


class BadOoidException(HBaseClientException):
    def __init__(self, wrapped_exception_class, reason=''):
        HBaseClientException.__init__(
          self,
          "Bad OOID: %s-%s" % (str(wrapped_exception_class), str(reason))
        )


class OoidNotFoundException(HBaseClientException):
    def __init__(self, reason=''):
        HBaseClientException.__init__(self, "OOID not found: %s" % str(reason))


class FatalException(HBaseClientException):
    def __init__(self, wrapped_exception_class, reason=''):
        HBaseClientException.__init__(
          self,
          "the connection is not viable.  retries fail: %s" % str(reason)
        )


class NoConnectionException(FatalException):
    def __init__(self, wrapped_exception_class, reason='', tries=0):
        FatalException.__init__(
          self,
          NoConnectionException,
          "No connection was made to HBase (%d tries): %s-%s" % (
            tries,
            str(wrapped_exception_class),
            str(reason)
          )
        )


class UnhandledInternalException(HBaseClientException):
    def __init__(self, wrapped_exception_class, reason=''):
        HBaseClientException.__init__(
          self,
          "An internal exception was not handled: %s-%s" % (
            str(wrapped_exception_class),
            str(reason)
          )
        )


def exception_wrapper(xClass):
    """This decorator ensures that no exception escapes that isn't from the
    HBaseClientException hierarchy.  Any unexpected exceptions are wrapped in
    the exception class passed into this function.  The original exception is
    preserved as the text of the wrapping expression.  Traceback info of the
    original exception is also preserved as the traceback for the wrapping
    exception."""
    def wrapper(fn):
        def f(*args, **kwargs):
            try:
                result = fn(*args, **kwargs)
                return result
            except HBaseClientException:
                raise
            except Exception:
                txClass, tx, txtb = sys.exc_info()
                raise xClass, xClass(txClass, tx), txtb
        f.__name__ = fn.__name__
        return f
    return wrapper


def exception_wrapper_for_generators(xClass):
    """This decorator ensures that no exception escapes that isn't from the
    HBaseClientException hierarchy.  Any unexpected exceptions are wrapped in
    the exception class passed into this function.  The original exception is
    preserved as the text of the wrapping expression.  Traceback info of the
    original exception is also preserved as the traceback for the wrapping
    exception."""
    def wrapper(fn):
        def f(*args, **kwargs):
            try:
                for x in fn(*args, **kwargs):
                    yield x
            except HBaseClientException, x:
                raise
            except Exception, x:
                txClass, tx, txtb = sys.exc_info()
                raise xClass, xClass(txClass, tx), txtb
        f.__name__ = fn.__name__
        return f
    return wrapper


def retry_wrapper_for_generators(fn):
    """a decorator to add retry symantics to any generator that uses hbase.
    Don't wrap iterators that themselves wrap iterators.  In other words, don't
    nest these."""
    def f(self, *args, **kwargs):
        self.logger.debug(
          'retry_wrapper_for_generators: trying first time, %s',
          fn.__name__
        )
        fail_counter = 0
        while True:  # we have to loop forever, we don't know the length of the
                     # wrapped iterator
            try:
                for x in fn(self, *args, **kwargs):
                    fail_counter = 0
                    yield x
                self.logger.debug(
                  'retry_wrapper_for_generators: completed without '
                  'trouble, %s',
                  fn.__name__
                )
                break  # this is the sucessful exit from this function
            except self.hbaseThriftExceptions, x:
                self.logger.debug(
                  'retry_wrapper_for_generators: handled exception %s',
                  str(x)
                )
                fail_counter += 1
                if fail_counter > 1:
                    self.logger.error(
                      'retry_wrapper_for_generators: failed too many '
                      'times on this one operation, %s',
                      fn.__name__
                    )
                    txClass, tx, txtb = sys.exc_info()
                    raise FatalException, FatalException(tx), txtb
                try:
                    self.close()
                except self.hbaseThriftExceptions:
                    pass
                self.logger.debug(
                  'retry_wrapper_for_generators: about to retry connection'
                )
                self.make_connection(timeout=self.timeout)
                self.logger.debug(
                  'retry_wrapper_for_generators: about to retry function, %s',
                  fn.__name__
                )
            except Exception, x:
                self.logger.debug(
                  'retry_wrapper_for_generators: unhandled exception, %s',
                  str(x)
                )
                raise
    f.__name__ = fn.__name__
    return f


def optional_retry_wrapper(fn):
    """a decorator to add retry symantics to any method that uses hbase"""
    def f(self, *args, **kwargs):
        number_of_retries = kwargs.setdefault('number_of_retries', 1)
        del kwargs['number_of_retries']
        wait_between_retries = kwargs.setdefault('wait_between_retries', 6)
        del kwargs['wait_between_retries']
        countdown = number_of_retries + 1
        while countdown:
            countdown -= 1
            try:
                result = fn(self, *args, **kwargs)
                return result
            # drop and remake connection
            except self.hbaseThriftExceptions, x:
                self.logger.debug(
                  'retry_wrapper: handled exception, %s',
                  str(x)
                )
                if not countdown:
                    # we've gone through all the retries that we're allowed
                    txClass, tx, txtb = sys.exc_info()
                    raise FatalException, FatalException(tx), txtb
                try:
                    self.close()
                except self.hbaseThriftExceptions:
                    pass
                self.logger.debug('retry_wrapper: about to retry connection')
                self.make_connection(timeout=self.timeout)
            # unknown error - abort
            except Exception, x:
                self.logger.debug(
                  'retry_wrapper: unhandled exception, %s',
                  str(x)
                )
                raise
            if wait_between_retries:
                time.sleep(wait_between_retries)
    f.__name__ = fn.__name__
    return f


@exception_wrapper(BadOoidException)
def guid_to_timestamped_row_id(id, timestamp):
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
        return "%s%s%s" % (id[0], timestamp[:-6], id)
    return "%s%s%s" % (id[0], timestamp, id)


@exception_wrapper(BadOoidException)
def ooid_to_row_id(ooid, old_format=False):
    """
    Returns a row_id suitable for the HBase crash_reports table.
    The first hex character of the ooid is used to "salt" the rowkey
    so that there should always be 16 HBase RegionServers responsible
    for dealing with the current stream of data.
    Then, we put the last six digits of the ooid which represent the
    submission date. This lets us easily scan through the crash_reports
    table by day.
    Finally, we append the normal ooid string.
    """
    try:
        if old_format:
            return "%s%s" % (ooid[-6:], ooid)
        else:
            return "%s%s%s" % (ooid[0], ooid[-6:], ooid)
    except Exception, x:
        raise BadOoidException(x)


@exception_wrapper(BadOoidException)
def row_id_to_ooid(row_id):
    """
    Returns the natural ooid given an HBase row key.
    See ooid_to_row_id for structure of row_id.
    """
    try:
        return row_id[7:]
    except Exception, x:
        raise BadOoidException(x)


class HBaseConnection(object):
    """
    Base class for hbase connections.  Supplies methods for a few basic
    queries and methods for cleanup of thrift results.
    """
    def __init__(self, host, port, timeout,
                 thrift=Thrift,
                 tsocket=TSocket,
                 ttrans=TTransport,
                 protocol=TBinaryProtocol,
                 ttp=ttypes,
                 client=Client,
                 column=ColumnDescriptor,
                 mutation=Mutation,
                 logger=utl.SilentFakeLogger()):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.thriftModule = thrift
        self.tsocketModule = tsocket
        self.transportModule = ttrans
        self.protocolModule = protocol
        self.ttypesModule = ttp
        self.clientClass = client
        self.columnClass = column
        self.mutationClass = mutation
        self.logger = logger
        self.hbaseThriftExceptions = (self.ttypesModule.IOError,
                                      #self.ttypesModule.IllegalArgument,
                                      #self.ttypesModule.AlreadyExists,
                                      self.thriftModule.TException,
                                      #HBaseClientException,
                                      socket.timeout,
                                      socket.error
                                      )
        self.operational_exceptions = self.hbaseThriftExceptions
        self.conditional_exceptions = ()

        try:
            self.make_connection(timeout=self.timeout)
        except NoConnectionException:
            utl.reportExceptionAndContinue(logger=self.logger)

    def make_connection(self, retry=2, timeout=9000):
        """Establishes the underlying connection to hbase"""
        try:
            self.logger.debug('make_connection, timeout = %d', timeout)
        except Exception:
            pass
        count = retry
        while count:
            try:
                count -= 1
                # Make socket
                transport = self.tsocketModule.TSocket(self.host, self.port)
                transport.setTimeout(timeout)  # in ms
                # Buffering is critical. Raw sockets are very slow
                self.transport = \
                  self.transportModule.TBufferedTransport(transport)
                # Wrap in a protocol
                self.protocol = \
                  self.protocolModule.TBinaryProtocol(self.transport)
                # Create a client to use the protocol encoder
                self.client = self.clientClass(self.protocol)
                # Connect!
                self.transport.open()
                self.badConnection = False
                self.logger.debug('connection successful')
                return
            except self.hbaseThriftExceptions, x:
                self.logger.debug('connection fails: %s', str(x))
                self.badConnection = True
                pass
        exceptionType, exception, tracebackInfo = sys.exc_info()
        raise NoConnectionException, \
              NoConnectionException(exceptionType, exception, retry), \
              tracebackInfo

    def close(self):
        """Close the hbase connection"""
        self.transport.close()

    def _make_rows_nice(self, client_result_object):
        """Apply _make_row_nice to multiple rows"""
        res = [self._make_row_nice(row) for row in client_result_object]
        return res

    def _make_row_nice(self, client_row_object):
        """Pull out the contents of the thrift column result objects into a
        python dict"""
        return dict(
          ((x, y.value) for x, y in client_row_object.columns.items())
        )

    @optional_retry_wrapper
    def describe_table(self, table_name):
        return self.client.getColumnDescriptors(table_name)

    @optional_retry_wrapper
    def get_full_row(self, table_name, row_id):
        """Get back every column value for a specific row_id"""
        return self._make_rows_nice(self.client.getRow(table_name, row_id))

    def commit(self):
        pass

    def rollback(self):
        pass

    @contextlib.contextmanager
    def __call__(self):
        yield self

    def in_transaction(self, dummy):
        return False

    def is_operational_exception(self, msg):
        return False


class HBaseConnectionForCrashReports(HBaseConnection):
    """A subclass of the HBaseConnection class providing more crash report
    specific methods"""
    def __init__(self,
                 host,
                 port,
                 timeout,
                 thrift=Thrift,
                 tsocket=TSocket,
                 ttrans=TTransport,
                 protocol=TBinaryProtocol,
                 ttp=ttypes,
                 client=Client,
                 column=ColumnDescriptor,
                 mutation=Mutation,
                 logger=utl.SilentFakeLogger()):
        super(HBaseConnectionForCrashReports, self).__init__(
          host,
          port,
          timeout,
          thrift,
          tsocket,
          ttrans,
          protocol,
          ttp,
          client,
          column,
          mutation,
          logger
        )

    def _make_row_nice(self, client_row_object):
        """This method allows the CrashReports subclass to output an additional
        column called ooid which does not have the HBase row_key prefixing junk
        in the way."""
        columns = super(HBaseConnectionForCrashReports, self)._make_row_nice(
          client_row_object
        )
        columns['_rowkey'] = client_row_object.row
        return columns

    @optional_retry_wrapper
    def get_json_meta_as_string(self, ooid, old_format=False):
        """
        Return the json metadata for a given ooid as an unexpanded string.
        If the ooid doesn't exist, raise not found.
        """
        row_id = ooid_to_row_id(ooid, old_format)
        listOfRawRows = self.client.getRowWithColumns(
          'crash_reports',
          row_id,
          ['meta_data:json']
        )
        try:
            if listOfRawRows:
                return listOfRawRows[0].columns["meta_data:json"].value
            else:
                raise OoidNotFoundException("%s - %s" % (ooid, row_id))
        except KeyError:
            self.logger.debug(
              'key error trying to get "meta_data:json" from %s',
              str(listOfRawRows)
            )
            raise

    #@optional_retry_wrapper
    def get_json(self, ooid, old_format=False, number_of_retries=2):
        """Return the json metadata for a given ooid as an json data object"""
        jsonColumnOfRow = self.get_json_meta_as_string(
          ooid,
          old_format,
          number_of_retries=number_of_retries
        )
        json_data = json.loads(jsonColumnOfRow, object_hook=DotDict)
        return json_data

    @optional_retry_wrapper
    def get_dump(self, ooid):
        """Return the minidump for a given ooid as a string of bytes
        If the ooid doesn't exist, raise not found"""
        row_id = ooid_to_row_id(ooid)
        listOfRawRows = self.client.getRowWithColumns(
          'crash_reports',
          row_id,
          ['raw_data:dump']
        )
        try:
            if listOfRawRows:
                return listOfRawRows[0].columns["raw_data:dump"].value
            else:
                raise OoidNotFoundException(ooid)
        except KeyError:
            self.logger.debug(
              'key error trying to get "raw_data:dump" from %s',
              str(listOfRawRows)
            )
            raise

    @optional_retry_wrapper
    def get_raw_report(self, ooid):
        """Return the json and dump for a given ooid
        If the ooid doesn't exist, raise not found"""
        row_id = ooid_to_row_id(ooid)
        listOfRawRows = self.client.getRowWithColumns(
          'crash_reports',
          row_id,
          ['meta_data:json', 'raw_data:dump']
        )
        if listOfRawRows:
            return self._make_row_nice(listOfRawRows[0])
        else:
            raise OoidNotFoundException(ooid)

    @optional_retry_wrapper
    def get_processed_json_as_string(self, ooid):
        """Return the cooked json (jsonz) for a given ooid as a string
        If the ooid doesn't exist, return an empty string."""
        row_id = ooid_to_row_id(ooid)
        listOfRawRows = self.client.getRowWithColumns(
          'crash_reports',
          row_id,
          ['processed_data:json']
        )
        if listOfRawRows:
            return listOfRawRows[0].columns["processed_data:json"].value
        else:
            raise OoidNotFoundException(ooid)

    #@optional_retry_wrapper
    def get_processed_json(self, ooid, number_of_retries=2):
        """Return the cooked json (jsonz) for a given ooid as a json object
        If the ooid doesn't exist, return an empty string."""
        jsonColumnOfRow = self.get_processed_json_as_string(
          ooid,
          number_of_retries=number_of_retries
        )
        json_data = json.loads(jsonColumnOfRow, object_hook=DotDict)
        return json_data

    @optional_retry_wrapper
    def get_report_processing_state(self, ooid):
        """Return the current state of processing for this report and the
        submitted_timestamp needed. For processing queue manipulation.
        If the ooid doesn't exist, return an empty array"""
        row_id = ooid_to_row_id(ooid)
        listOfRawRows = self.client.getRowWithColumns(
          'crash_reports',
          row_id,
          ['flags:processed',
           'flags:legacy_processing',
           'timestamps:submitted',
           'timestamps:processed'
          ]
        )
        if listOfRawRows:
            return self._make_row_nice(listOfRawRows[0])
        else:
            raise OoidNotFoundException(ooid)

    def export_jsonz_for_date(self, date, path):
        """Iterates through all rows for a given date and dumps the
        processed_data:json out as a jsonz file.  The implementation opens up
        16 scanners (one for each leading hex character of the salt)
        one at a time and returns all of the rows matching"""
        for row in self.limited_iteration(
          self.union_scan_with_prefix(
            'crash_reports',
            date,
            ['processed_data:json']
          ),
          10
        ):
            ooid = row_id_to_ooid(row['_rowkey'])
            if row['processed_data:json']:
                file_name = os.path.join(path, ooid + '.jsonz')
                file_handle = gzip.open(file_name, 'w', 9)
                try:
                    json.dump(row['processed_data:json'], file_handle)
                finally:
                    file_handle.close()

    def export_jsonz_tarball_for_date(self, date, path, tarball_name):
        """
        Iterates through all rows for a given date and dumps the
        processed_data:json out as a jsonz file. The implementation opens up
        16 scanners (one for each leading hex character of the salt)
        one at a time and returns all of the rows matching
        """
        tf = tarfile.open(tarball_name, 'w:gz')
        try:
            for i, row in enumerate(
              self.limited_iteration(
                self.union_scan_with_prefix(
                  'crash_reports',
                  date,
                  ['processed_data:json']
                ),
                10)
              ):
                ooid = row_id_to_ooid(row['_rowkey'])
                if row['processed_data:json']:
                    file_name = os.path.join(path, ooid + '.jsonz')
                    file_handle = gzip.open(file_name, 'w', 9)
                    try:
                        json.dump(row['processed_data:json'], file_handle)
                    finally:
                        file_handle.close()
                    tf.add(
                      file_name,
                      os.path.join(ooid[:2], ooid[2:4], ooid + '.jsonz')
                    )
                    os.unlink(file_name)
        finally:
            tf.close()

    def export_jsonz_tarball_for_ooids(self, path, tarball_name):
        """Creates jsonz files for each ooid passed in on stdin and puts them
        all in a tarball"""
        tf = tarfile.open(tarball_name, 'w')
        try:
            for line in sys.stdin.readlines():
                ooid = line.strip()
                self.logger.debug('Ooid: "%s"', ooid)
                if len(ooid) == 36:
                    try:
                        json = self.get_processed_json_as_string(ooid)
                    except OoidNotFoundException:
                        self.logger.debug(
                          'OoidNotFound (No processed_data:json?): %s',
                          ooid
                        )
                        continue
                    file_name = os.path.join(path, ooid + '.jsonz')
                    file_handle = gzip.open(file_name, 'w', 9)
                    try:
                        file_handle.write(json)
                    finally:
                        file_handle.close()
                    tf.add(file_name, os.path.join(
                      ooid[:2],
                      ooid[2:4],
                      ooid + '.jsonz'
                    ))
                    os.unlink(file_name)
                else:
                    self.logger.debug('Skipping...')
        finally:
            tf.close()

    def union_scan_with_prefix(self, table, prefix, columns):
        # TODO: Need assertion for columns contains at least 1 element
        """A lazy chain of iterators that yields unordered rows starting with
        a given prefix. The implementation opens up 16 scanners (one for each
        leading hex character of the salt) one at a time and returns all of
        the rows matching"""
        for salt in '0123456789abcdef':
            salted_prefix = "%s%s" % (salt, prefix)
            scanner = self.client.scannerOpenWithPrefix(
              table,
              salted_prefix,
              columns
            )
            for rowkey, row in salted_scanner_iterable(
              self.logger,
              self.client,
              self._make_row_nice,
              salted_prefix,
              scanner
            ):
                yield row

    def merge_scan_with_prefix(self, table, prefix, columns):
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
            scanner = self.client.scannerOpenWithPrefix(
              table,
              salted_prefix,
              columns
            )
            iterators.append(salted_scanner_iterable(
              self.logger,
              self.client,
              self._make_row_nice,
              salted_prefix,
              scanner
            ))
        # The i below is so we can advance whichever scanner delivers us the
        # polled item.
        for i, it in enumerate(iterators):
            try:
                next = it.next
                next_items_queue.append([next(), i, next])
            except StopIteration:
                pass
        heapq.heapify(next_items_queue)

        while 1:
            try:
                while 1:
                    row_tuple, iter_index, next = s = next_items_queue[0]
                    # tuple[1] is the actual nice row.
                    yield row_tuple[1]
                    s[0] = next()
                    heapq.heapreplace(next_items_queue, s)
            except StopIteration:
                heapq.heappop(next_items_queue)
            except IndexError:
                return

    def limited_iteration(self, iterable, limit=10 ** 6):
        self.logger.debug('limit = %d' % limit)
        return itertools.islice(iterable, limit)

    @retry_wrapper_for_generators
    def iterator_for_all_legacy_to_be_processed(self):
        self.logger.debug('iterator_for_all_legacy_to_be_processed')
        for row in self.limited_iteration(
          self.merge_scan_with_prefix(
            'crash_reports_index_legacy_unprocessed_flag',
            '',
            ['ids:ooid']
          )
        ):
            self.delete_from_legacy_processing_index(row['_rowkey'])
            yield row['ids:ooid']

    #@retry_wrapper_for_generators
    @optional_retry_wrapper
    def acknowledge_ooid_as_legacy_priority_job(self, ooid):
        try:
            state = self.get_report_processing_state(ooid)
            if state:
                row_key = guid_to_timestamped_row_id(
                  ooid,
                  state['timestamps:submitted']
                )
                self.delete_from_legacy_processing_index(row_key)
            return bool(state)
        except OoidNotFoundException:
            return False

    @optional_retry_wrapper
    def delete_from_legacy_processing_index(self, index_row_key):
        self.client.deleteAllRow(
          'crash_reports_index_legacy_unprocessed_flag',
          index_row_key
        )
        self.client.atomicIncrement(
          'metrics',
          'crash_report_queue',
          'counters:current_legacy_unprocessed_size',
          -1
        )

    @optional_retry_wrapper
    def put_crash_report_indices(self, ooid, timestamp, indices):
        row_id = guid_to_timestamped_row_id(ooid, timestamp)
        for index_name in indices:
            self.client.mutateRow(
              index_name,
              row_id,
              [self.mutationClass(column="ids:ooid", value=ooid)]
            )

    @optional_retry_wrapper
    def put_crash_report_hang_indices(self, ooid, hang_id, process_type,
                                      timestamp):
        ooid_column_name = "ids:ooid:" + process_type
        self.client.mutateRow(
          'crash_reports_index_hang_id_submitted_time',
          guid_to_timestamped_row_id(hang_id, timestamp),
          [self.mutationClass(column=ooid_column_name, value=ooid)]
        )
        self.client.mutateRow(
          'crash_reports_index_hang_id',
          hang_id,
          [self.mutationClass(column=ooid_column_name, value=ooid)]
        )

    @optional_retry_wrapper
    def update_metrics_counters_for_submit(self,
                                           submitted_timestamp,
                                           legacy_processing,
                                           process_type,
                                           is_hang,
                                           add_to_unprocessed_queue):
        """Increments a series of counters in the 'metrics' table related to
        CR submission"""
        timeLevels = [
          submitted_timestamp[:16],  # minute yyyy-mm-ddTHH:MM
          submitted_timestamp[:13],  # hour   yyyy-mm-ddTHH
          submitted_timestamp[:10],  # day    yyyy-mm-dd
          submitted_timestamp[: 7],  # month  yyyy-mm
          submitted_timestamp[: 4]   # year   yyyy
        ]
        counterIncrementList = ['counters:submitted_crash_reports']
        counterIncrementList.append(
          "counters:submitted_crash_reports_legacy_throttle_%d"
          % legacy_processing
        )
        if process_type != 'default':
            if is_hang:
                counterIncrementList.append(
                  "counters:submitted_crash_report_hang_pairs"
                )
            else:
                counterIncrementList.append(
                  "counters:submitted_oop_%s_crash_reports" % process_type
                )

        if add_to_unprocessed_queue:
            self.client.atomicIncrement(
              'metrics',
              'crash_report_queue',
              'counters:current_unprocessed_size',
              1
            )
            if legacy_processing == 0:
                self.client.atomicIncrement(
                  'metrics',
                  'crash_report_queue',
                  'counters:current_legacy_unprocessed_size',
                  1
                )

        for rowkey in timeLevels:
            for column in counterIncrementList:
                self.client.atomicIncrement('metrics', rowkey, column, 1)

    @optional_retry_wrapper
    def put_json_dump(self, ooid, json_data, dump,
                      add_to_unprocessed_queue=True):
        """Create a crash report record in hbase from serialized json and
        bytes of the minidump"""
        row_id = ooid_to_row_id(ooid)
        submitted_timestamp = json_data['submitted_timestamp']
        json_string = json.dumps(json_data)

        # Extract ACCEPT(0), DEFER(1), DISCARD(2) enum or 0 if not found.
        legacy_processing = json_data.get('legacy_processing', 0)

        columns = [
          ("flags:processed", "N"),
          ("meta_data:json", json_string),
          ("timestamps:submitted", submitted_timestamp),
          ("ids:ooid", ooid),
          ("raw_data:dump", dump)
        ]
        mutationList = [
          self.mutationClass(column=c, value=v)
            for c, v in columns if v is not None
        ]

        indices = [
          'crash_reports_index_submitted_time',
          'crash_reports_index_unprocessed_flag'
        ]

        if legacy_processing == 0:
            mutationList.append(
              self.mutationClass(column="flags:legacy_processing", value='Y')
            )
            indices.append('crash_reports_index_legacy_unprocessed_flag')
            indices.append('crash_reports_index_legacy_submitted_time')

        # Use ProcessType value if exists, otherwise, default (i.e. a
        # standard application crash report)
        process_type = json_data.get('ProcessType', 'default')

        is_hang = 'HangID' in json_data
        if is_hang:
            hang_id = json_data['HangID']
            mutationList.append(
              self.mutationClass(column="ids:hang", value=hang_id)
            )

        # unit test marker 233
        self.client.mutateRow('crash_reports', row_id, mutationList)
        self.put_crash_report_indices(ooid, submitted_timestamp, indices)
        if is_hang:
            self.put_crash_report_hang_indices(
              ooid,
              hang_id,
              process_type,
              submitted_timestamp
            )

        self.update_metrics_counters_for_submit(
          submitted_timestamp,
          legacy_processing,
          process_type,
          is_hang,
          add_to_unprocessed_queue
        )

    def put_json_dump_from_files(self, ooid, json_path, dump_path,
                                 openFn=open):
        """Convenience method for creating an ooid from disk"""
        json_file = open(json_path, 'r')
        try:
            json = json_file.read()
        finally:
            json_file.close()
        # Apparently binary mode only matters in windows, but it won't hurt
        # anything on unix systems.
        dump_file = open(dump_path, 'rb')
        try:
            dump = dump_file.read()
        finally:
            dump_file.close()
        self.put_json_dump(ooid, json, dump)

    @optional_retry_wrapper
    def put_fixed_dump(self, ooid, dump, submitted_timestamp,
                       add_to_unprocessed_queue=True):
        """Update a crash report with a new dump file optionally queuing for
        processing"""
        row_id = ooid_to_row_id(ooid)

        columns = [
            ("raw_data:dump", dump)
        ]
        mutationList = [
          self.mutationClass(column=c, value=v)
            for c, v in columns if v is not None
        ]

        indices = []

        if add_to_unprocessed_queue:
            indices.append('crash_reports_index_legacy_unprocessed_flag')

        self.client.mutateRow('crash_reports', row_id, mutationList)

        self.put_crash_report_indices(ooid, submitted_timestamp, indices)

    @optional_retry_wrapper
    def put_processed_json(self, ooid, processed_json):
        """
        Create a crash report from the cooked json output of the processor
        """
        row_id = ooid_to_row_id(ooid)

        processing_state = self.get_report_processing_state(ooid)
        submitted_timestamp = processing_state.get(
          'timestamps:submitted',
          processed_json.get('date_processed', 'unknown')
        )

        if 'N' == processing_state.get('flags:processed', '?'):
            index_row_key = guid_to_timestamped_row_id(
              ooid,
              submitted_timestamp
            )
            self.client.atomicIncrement(
              'metrics',
              'crash_report_queue',
              'counters:current_unprocessed_size',
              -1
            )
            self.client.deleteAllRow(
              'crash_reports_index_unprocessed_flag',
              index_row_key
            )

        processed_timestamp = processed_json['completeddatetime']

        if 'signature' in processed_json:
            if len(processed_json['signature']) > 0:
                signature = processed_json['signature']
            else:
                signature = '##empty##'
        else:
            signature = '##null##'

        mutationList = []
        mutationList.append(
          self.mutationClass(
            column="timestamps:processed",
            value=processed_timestamp
          )
        )
        mutationList.append(
          self.mutationClass(
            column="processed_data:signature",
            value=signature
          )
        )
        mutationList.append(
          self.mutationClass(
            column="processed_data:json",
            value=json.dumps(processed_json)
          )
        )
        mutationList.append(
          self.mutationClass(
            column="flags:processed",
            value="Y"
          )
        )

        self.client.mutateRow('crash_reports', row_id, mutationList)

        sig_ooid_idx_row_key = signature + ooid
        self.client.mutateRow(
          'crash_reports_index_signature_ooid',
          sig_ooid_idx_row_key,
          [self.mutationClass(column="ids:ooid", value=ooid)]
        )

    def export_sampled_crashes_tarball_for_dates(self, sample_size, dates,
                                                 path, tarball_name):
        """Iterates through all rows for given dates and dumps json and dump
        for N random crashes. The implementation opens up 16 scanners (one for
        each leading hex character of the salt) one at a time and returns all
        of the rows randomly selected using a resovoir sampling algorithm"""
        sample_size = int(sample_size)
        dates = str.split(dates, ',')

        def gen():
            """generate all rows for given dates"""
            for date in dates:
                for id_row in self.union_scan_with_prefix(
                  'crash_reports',
                  date,
                  ['ids:ooid']
                ):
                    yield id_row['ids:ooid']
        row_gen = gen()  # start the generator
        # get inital sample
        ooids_to_export = [
          x for i, x in itertools.izip(xrange(sample_size), row_gen)
        ]
        # cycle through remaining rows
        for i, ooid in enumerate(row_gen):
            # Randomly replace elements with decreasing probability
            rand = random.randrange(i + sample_size)
            if rand < sample_size:
                ooids_to_export[rand] = ooid

        # open output tar file
        tf = tarfile.open(tarball_name, 'w:gz')
        try:
            for ooid in ooids_to_export:
                json_file_name = os.path.join(path, ooid + '.json')
                dump_file_name = os.path.join(path, ooid + '.dump')
                row = self.get_raw_report(ooid)
                json_file_handle = open(json_file_name, 'w')
                try:
                    json_file_handle.write(row['meta_data:json'])
                finally:
                    json_file_handle.close()
                dump_file_handle = open(dump_file_name, 'w')
                try:
                    dump_file_handle.write(row['raw_data:dump'])
                finally:
                    dump_file_handle.close()
                tf.add(json_file_name, os.path.join(
                  ooid[:2],
                  ooid[2:4],
                  ooid + '.json')
                       )
                tf.add(
                  dump_file_name,
                  os.path.join(ooid[:2], ooid[2:4], ooid + '.dump')
                )
                os.unlink(json_file_name)
                os.unlink(dump_file_name)
        finally:
            tf.close()


def salted_scanner_iterable(logger, client, make_row_nice, salted_prefix,
                            scanner):
    """Generator based iterable that runs over an HBase scanner
    yields a tuple of the un-salted rowkey and the nice format of the row."""
    logger.debug('Scanner %s generated', salted_prefix)
    raw_rows = client.scannerGet(scanner)
    while raw_rows:
        nice_row = make_row_nice(raw_rows[0])
        #logger.debug('Scanner %s returning nice_row (%s) for raw_rows (%s)' %
        #(self.salted_prefix,nice_row,raw_rows))
        yield (nice_row['_rowkey'][1:], nice_row)
        raw_rows = client.scannerGet(scanner)
    logger.debug('Scanner %s exhausted' % salted_prefix)
    client.scannerClose(scanner)

# TODO: Warning, the command line methods haven't been tested for bitrot
if __name__ == "__main__":
    import pprint
    import sys

    def ppjson(data, sort_keys=False, indent=4):
        print json.dumps(data, sort_keys, indent)

    def usage():
        print """
  Usage: %s [-h host[:port]] command [arg1 [arg2...]]

  Commands:
    Crash Report specific:
      get_report ooid
      get_json ooid
      get_dump ooid
      get_processed_json ooid
      get_report_processing_state ooid
      union_scan_with_prefix table prefix columns [limit]
      merge_scan_with_prefix table prefix columns [limit]
      put_json_dump ooid json dump
      put_json_dump_from_files ooid json_path dump_path
      export_jsonz_for_date YYMMDD export_path
      export_jsonz_tarball_for_date YYMMDD temp_path tarball_name
      export_jsonz_tarball_for_ooids temp_path tarball_name <stdin ooids list>
      export_sampled_crashes_tarball_for_dates sample_size
               YYMMDD,YYMMDD,... path tarball_name
    HBase generic:
      describe_table table_name
      get_full_row table_name row_id
  """ % sys.argv[0]

    if len(sys.argv) <= 1 or sys.argv[1] == '--help':
        usage()
        sys.exit(0)

    pp = pprint.PrettyPrinter(indent=2)
    host = 'cm-hadoop-dev02'
    port = 9090
    argi = 1

    if sys.argv[argi] == '-h':
        parts = sys.argv[argi + 1].split(':')
        host = parts[0]
        if len(parts) == 2:
            port = int(parts[1])
        argi += 2

    cmd = sys.argv[argi]
    args = sys.argv[argi + 1:]

    connection = HBaseConnectionForCrashReports(
      host,
      port,
      5000,
      logger=utl.FakeLogger()
    )

    if cmd == 'get_report':
        if len(args) != 1:
            usage()
            sys.exit(1)
        pp.pprint(connection.get_report(*args))

    elif cmd == 'get_json':
        if len(args) < 1:
            usage()
            sys.exit(1)
        old = len(args) == 2
        ppjson(connection.get_json(args[0], old))

    elif cmd == 'get_dump':
        if len(args) != 1:
            usage()
            sys.exit(1)
        print(connection.get_dump(*args))

    elif cmd == 'get_processed_json':
        if len(args) != 1:
            usage()
            sys.exit(1)
        ppjson(connection.get_processed_json(*args))

    elif cmd == 'get_report_processing_state':
        if len(args) != 1:
            usage()
            sys.exit(1)
        pp.pprint(connection.get_report_processing_state(*args))

    elif cmd == 'union_scan_with_prefix':
        if len(args) < 3:
            usage()
            sys.exit(1)
        columns = args[2].split(',')
        if len(args) > 3:
            limit = int(args[3])
        else:
            limit = 10
        for row in connection.limited_iteration(
          connection.union_scan_with_prefix(args[0], args[1], columns),
          limit
          ):
            ppjson(row)

    elif cmd == 'merge_scan_with_prefix':
        if len(args) < 3:
            usage()
            sys.exit(1)
        columns = args[2].split(',')
        if len(args) > 3:
            limit = int(args[3])
        else:
            limit = 10
        for row in connection.limited_iteration(
          connection.merge_scan_with_prefix(args[0], args[1], columns),
          limit
        ):
            ppjson(row)

    elif cmd == 'put_json_dump':
        if len(args) != 3:
            usage()
            sys.exit(1)
        ppjson(connection.put_json_dump(*args))

    elif cmd == 'put_json_dump_from_files':
        if len(args) != 3:
            usage()
            sys.exit(1)
        ppjson(connection.put_json_dump_from_files(*args))

    elif cmd == 'export_jsonz_for_date':
        if len(args) != 2:
            usage()
            sys.exit(1)
        connection.export_jsonz_for_date(*args)

    elif cmd == 'export_jsonz_tarball_for_date':
        if len(args) != 3:
            usage()
            sys.exit(1)
        connection.export_jsonz_tarball_for_date(*args)

    elif cmd == 'export_jsonz_tarball_for_ooids':
        if len(args) != 2:
            usage()
            sys.exit(1)
        connection.export_jsonz_tarball_for_ooids(*args)

    elif cmd == 'export_sampled_crashes_tarball_for_dates':
        if len(args) != 4:
            usage()
            sys.exit(1)
        connection.export_sampled_crashes_tarball_for_dates(*args)

    elif cmd == 'describe_table':
        if len(args) != 1:
            usage()
            sys.exit(1)
        pp.pprint(connection.describe_table(*args))

    elif cmd == 'get_full_row':
        if len(args) != 2:
            usage()
            sys.exit(1)
        pp.pprint(connection.get_full_row(*args))

    else:
        usage()
        sys.exit(1)

    connection.close()

# vi: sw=2 ts=2

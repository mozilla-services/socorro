#!/usr/bin/python
try:
  import json
except ImportError:
  import simplejson as json
import itertools
import os
import sys
import gzip
import heapq
import threading
import time
import tarfile
import struct
import datetime as dt
import socorro.lib.datetimeutil as sdt

import socket

from thrift import Thrift  #get Thrift modue
from thrift.transport import TSocket, TTransport #get modules
from thrift.protocol import TBinaryProtocol #get module
from hbase import ttypes #get module
from hbase.hbase import Client, ColumnDescriptor, Mutation #get classes from module

import socorro.lib.util as utl

#=================================================================================================================
class IterableJsonEncoder(json.JSONEncoder):
  """
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, *args, **kwargs):
    super(IterableJsonEncoder, self).__init__(*args, **kwargs)
  #-----------------------------------------------------------------------------------------------------------------
  def default(self, o):
    try:
      iterable = iter(o)
    except TypeError:
      pass
    else:
      return list(iterable)
    return JSONEncoder.default(self, o)

class HBaseClientException(Exception):
  pass

class BadOoidException(HBaseClientException):
  def __init__(self, wrapped_exception_class, reason=''):
    #super(BadOoidException, self).__init__("Bad OOID: %s-%s" % (str(wrapped_exception_class), str(reason)))
    HBaseClientException.__init__(self, "Bad OOID: %s-%s" % (str(wrapped_exception_class), str(reason)))

class OoidNotFoundException(HBaseClientException):
  def __init__(self, reason=''):
    #super(OoidNotFoundException, self).__init__("OOID not found: %s" % str(reason))
    HBaseClientException.__init__(self, "OOID not found: %s" % str(reason))

#class NotInJsonFormatException(HBaseClientException):
  #def __init__(self, wrapped_exception_class, reason=''):
    ##super(NotInJsonFormatException, self).__init__("Improper JSON format: %s" % str(reason))
    #HBaseClientException.__init__(self, "Improper JSON format: %s" % str(reason))

class FatalException(HBaseClientException):
  def __init__(self, wrapped_exception_class, reason=''):
    #super(FatalException, self).__init__("Improper JSON format: %s" % str(reason))
    HBaseClientException.__init__(self, "the connection is not viable.  retries fail: %s" % str(reason))

class NoConnectionException(FatalException):
  def __init__(self, wrapped_exception_class, reason='', tries=0):
    #super(NoConnectionException, self).__init__("No connection was made to HBase (%d tries): %s-%s" % (tries, str(wrapped_exception_class), str(reason)))
    FatalException.__init__(self, NoConnectionException, "No connection was made to HBase (%d tries): %s-%s" % (tries, str(wrapped_exception_class), str(reason)))

class UnhandledInternalException(HBaseClientException):
  def __init__(self, wrapped_exception_class, reason=''):
    #super(UnhandledInternalException, self).__init__("An internal exception was not handled: %s-%s" % (str(wrapped_exception_class), str(reason)))
    HBaseClientException.__init__(self, "An internal exception was not handled: %s-%s" % (str(wrapped_exception_class), str(reason)))

def exception_wrapper(xClass):
  """This decorator ensures that no exception escapes that isn't from the
  HBaseClientException hierarchy.  Any unexpected exceptions are wrapped in the
  exception class passed into this function.  The original exception is preserved
  as the text of the wrapping expression.  Traceback info of the original
  exception is also preserved as the traceback for the wrapping exception."""
  def wrapper (fn):
    def f(*args, **kwargs):
      try:
        result = fn(*args, **kwargs)
        return result
      except HBaseClientException, x:
        raise
      except Exception, x:
        txClass, tx, txtb = sys.exc_info()
        raise xClass, xClass(txClass,tx), txtb
    f.__name__ = fn.__name__
    return f
  return wrapper

def exception_wrapper_for_generators(xClass):
  """This decorator ensures that no exception escapes that isn't from the
  HBaseClientException hierarchy.  Any unexpected exceptions are wrapped in the
  exception class passed into this function.  The original exception is preserved
  as the text of the wrapping expression.  Traceback info of the original
  exception is also preserved as the traceback for the wrapping exception."""
  def wrapper (fn):
    def f(*args, **kwargs):
      try:
        for x in fn(*args, **kwargs):
          yield x
      except HBaseClientException, x:
        raise
      except Exception, x:
        txClass, tx, txtb = sys.exc_info()
        raise xClass, xClass(txClass,tx), txtb
    f.__name__ = fn.__name__
    return f
  return wrapper

def retry_wrapper_for_generators(fn):
  """a decorator to add retry symantics to any generator that uses hbase.  Don't wrap iterators
  that themselves wrap iterators.  In other words, don't nest these."""
  def f(self, *args, **kwargs):
    #self.logger.debug('retry_wrapper_for_generators: trying first time, %s', fn.__name__)
    fail_counter = 0
    while True:  #we have to loop forever, we don't know the length of the wrapped iterator
      try:
        for x in fn(self, *args, **kwargs):
          fail_counter = 0
          yield x
        #self.logger.debug('retry_wrapper_for_generators: completed without trouble, %s', fn.__name__)
        break # this is the sucessful exit from this function
      except self.hbaseThriftExceptions, x:
        self.logger.debug('retry_wrapper_for_generators: handled exception, %s', str(x))
        fail_counter += 1
        if fail_counter > 1:
          self.logger.error('retry_wrapper_for_generators: failed too many times on this one operation, %s', fn.__name__)
          txClass, tx, txtb = sys.exc_info()
          raise FatalException, FatalException(tx), txtb
        try:
          self.close()
        except self.hbaseThriftExceptions:
          pass
        self.logger.debug('retry_wrapper_for_generators: about to retry connection')
        self.make_connection(timeout=self.timeout)
        self.logger.debug('retry_wrapper_for_generators: about to retry function, %s', fn.__name__)
      except Exception, x:
        self.logger.debug('retry_wrapper_for_generators: unhandled exception, %s', str(x))
        raise
  f.__name__ = fn.__name__
  return f

def optional_retry_wrapper(fn):
  """a decorator to add retry symantics to any method that uses hbase"""
  def f(self, *args, **kwargs):
    number_of_retries = kwargs.setdefault('number_of_retries', 1)
    del kwargs['number_of_retries']
    wait_between_retries = kwargs.setdefault('wait_between_retries', 1)
    del kwargs['wait_between_retries']
    countdown = number_of_retries + 1
    while countdown:
      countdown -= 1
      try:
        #self.logger.debug('retry_wrapper: %s, try number %s', fn.__name__, number_of_retries + 1 - countdown)
        result = fn(self, *args, **kwargs)
        #self.logger.debug('retry_wrapper: completed without trouble, %s', fn.__name__)
        return result
      # drop and remake connection
      except self.hbaseThriftExceptions, x:
        self.logger.debug('retry_wrapper: handled exception, %s', str(x))
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
      except Exception, x:  #lars
        self.logger.debug('retry_wrapper(%s): unhandled exception, %s', fn.__name__, str(x))
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
  return "%s%s%s" % (id[0], timestamp, id)

@exception_wrapper(BadOoidException)
def ooid_to_row_id(ooid,old_format=False):
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
      return "%s%s" % (ooid[-6:],ooid)
    else:
      return "%s%s%s" % (ooid[0],ooid[-6:],ooid)
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
  def __init__(self,host,port,timeout,
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
    try:
      self.make_connection(timeout=self.timeout)
    except NoConnectionException, x:
      self.logger.error('cannot establish initial connection to hbase: %s',
                        str(x))

  def make_connection(self, retry=2, timeout=9000):
    """Establishes the underlying connection to hbase"""
    self.logger.debug('make_connection, timeout = %d', timeout)
    count = retry
    while count:
      count -= 1
      try:
        # Make socket
        transport = self.tsocketModule.TSocket(self.host, self.port)
        transport.setTimeout(timeout) #in ms
        # Buffering is critical. Raw sockets are very slow
        self.transport = self.transportModule.TBufferedTransport(transport)
        # Wrap in a protocol
        self.protocol = self.protocolModule.TBinaryProtocol(self.transport)
        # Create a client to use the protocol encoder
        self.client = self.clientClass(self.protocol)
        # Connect!
        self.transport.open()
        self.logger.debug('connection successful')
        return
      except self.hbaseThriftExceptions, x:
        self.logger.debug('connection fails: %s', str(x))
        pass
    exceptionType, exception, tracebackInfo = sys.exc_info()
    raise NoConnectionException, NoConnectionException(exceptionType, exception, retry), tracebackInfo

  def close(self):
    """
    Close the hbase connection
    """
    self.transport.close()

  def _make_rows_nice(self,client_result_object):
    """
    Apply _make_row_nice to multiple rows
    """
    res = [self._make_row_nice(row) for row in client_result_object]
    return res

  def _make_row_nice(self,client_row_object):
    """
    Pull out the contents of the thrift column result objects into a python dict
    """
    return dict(((x,y.value) for x,y in client_row_object.columns.items()))

  @optional_retry_wrapper
  def describe_table(self,table_name):
    return self.client.getColumnDescriptors(table_name)

  @optional_retry_wrapper
  def get_full_row(self,table_name, row_id):
    """
    Get back every column value for a specific row_id
    """
    return self._make_rows_nice(self.client.getRow(table_name, row_id))

class HBaseConnectionForCrashReports(HBaseConnection):
  """
  A subclass of the HBaseConnection class providing more crash report specific methods
  """
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
    super(HBaseConnectionForCrashReports,self).__init__(host,port,timeout,thrift,tsocket,ttrans,
                                                        protocol,ttp,client,column,
                                                        mutation,logger)

  def _make_row_nice(self,client_row_object):
    """
    This method allows the CrashReports subclass to output an additional column called ooid
    which does not have the HBase row_key prefixing junk in the way.
    """
    columns = super(HBaseConnectionForCrashReports,self)._make_row_nice(client_row_object)
    columns['_rowkey'] = client_row_object.row
    return columns

  @optional_retry_wrapper
  def get_queue_statistics(self):
    """
    Get a set of statistics from the HBase metrics table regarding processing queues
    """
    aggStats = {}
    try:
      rawQueueStats = self._make_row_nice(self.client.getRow('metrics', 'crash_report_queues')[0])
      if rawQueueStats.get('counters:inserts_unprocessed_legacy'):
        inserts_unprocessed_legacy = long(struct.unpack('>q', rawQueueStats['counters:inserts_unprocessed_legacy'])[0])
      else:
        inserts_unprocessed_legacy = 0
      if rawQueueStats.get('counters:deletes_unprocessed_legacy'):
        deletes_unprocessed_legacy = long(struct.unpack('>q', rawQueueStats['counters:deletes_unprocessed_legacy'])[0])
      else:
        deletes_unprocessed_legacy = 0
      if rawQueueStats.get('counters:inserts_unprocessed_priority'):
        inserts_unprocessed_priority = long(struct.unpack('>q', rawQueueStats['counters:inserts_unprocessed_priority'])[0])
      else:
        inserts_unprocessed_priority = 0
      if rawQueueStats.get('counters:deletes_unprocessed_priority'):
        deletes_unprocessed_priority = long(struct.unpack('>q', rawQueueStats['counters:deletes_unprocessed_priority'])[0])
      else:
        deletes_unprocessed_priority = 0
      if rawQueueStats.get('counters:inserts_unprocessed'):
        inserts_unprocessed = long(struct.unpack('>q', rawQueueStats['counters:inserts_unprocessed'])[0])
      else:
        inserts_unprocessed = 0
      if rawQueueStats.get('counters:deletes_unprocessed'):
        deletes_unprocessed = long(struct.unpack('>q', rawQueueStats['counters:deletes_unprocessed'])[0])
      else:
        deletes_unprocessed = 0
      if rawQueueStats.get('counters:inserts_processed_legacy'):
        inserts_processed_legacy = long(struct.unpack('>q', rawQueueStats['counters:inserts_processed_legacy'])[0])
      else:
        inserts_processed_legacy = 0
      if rawQueueStats.get('counters:deletes_processed_legacy'):
        deletes_processed_legacy = long(struct.unpack('>q', rawQueueStats['counters:deletes_processed_legacy'])[0])
      else:
        deletes_processed_legacy = 0
      if rawQueueStats.get('counters:inserts_processed_priority'):
        inserts_processed_priority = long(struct.unpack('>q', rawQueueStats['counters:inserts_processed_priority'])[0])
      else:
        inserts_processed_priority = 0
      if rawQueueStats.get('counters:deletes_processed_priority'):
        deletes_processed_priority = long(struct.unpack('>q', rawQueueStats['counters:deletes_processed_priority'])[0])
      else:
        deletes_processed_priority = 0
    except IndexError:
      inserts_unprocessed_legacy = 0
      deletes_unprocessed_legacy = 0
      inserts_unprocessed_priority = 0
      deletes_unprocessed_priority = 0
      inserts_unprocessed = 0
      deletes_unprocessed = 0
      inserts_processed_legacy = 0
      deletes_processed_legacy = 0
      inserts_processed_priority = 0
      deletes_processed_priority = 0

    aggStats['active_raw_reports_in_queue'] = inserts_unprocessed_legacy - deletes_unprocessed_legacy
    aggStats['priority_raw_reports_in_queue'] = inserts_unprocessed_priority - deletes_unprocessed_priority
    aggStats['throttled_raw_reports_in_queue'] = inserts_unprocessed - deletes_unprocessed
    aggStats['processed_reports_in_dbfeeder_queue'] = inserts_processed_legacy - deletes_processed_legacy
    aggStats['priority_processed_reports_in_dbfeeder_queue'] = inserts_processed_priority - deletes_processed_priority

    for row in self.limited_iteration(self.merge_scan_with_prefix('crash_reports_index_legacy_unprocessed_flag',
                                                                  '', ['ids:ooid', 'processor_state:name', 'processor_state:post_timestamp']), 1):
      aggStats['oldest_active_report'] = row['_rowkey'][1:20]
      aggStats['oldest_active_report_details'] = "%s: processor_state: %s - %s" % (row['ids:ooid'], row.get('processor_state:name', ''), row.get('processor_state:post_timestamp', ''))
      break
    for row in self.limited_iteration(self.merge_scan_with_prefix('crash_reports_index_unprocessed_flag',
                                                                  '', ['ids:ooid', 'processor_state:name', 'processor_state:post_timestamp']), 1):
      aggStats['oldest_throttled_report'] = row['_rowkey'][1:20]
      aggStats['oldest_throttled_report_details'] = "%s: processor_state: %s - %s" % (row['ids:ooid'], row.get('processor_state:name', ''), row.get('processor_state:post_timestamp', ''))
      break
    for row in self.limited_iteration(self.merge_scan_with_prefix('crash_reports_index_legacy_processed',
                                                                  '', ['ids:ooid']), 1):
      aggStats['oldest_processed_report'] = row['_rowkey'][1:20]
      break
    for row in self.limited_iteration(self.merge_scan_with_prefix('crash_reports_index_priority_processed',
                                                                  '', ['ids:ooid']), 1):
      aggStats['oldest_priority_processed_report'] = row['_rowkey'][1:20]
      break
    return aggStats

  def get_json_meta_as_string(self,ooid,old_format=False):
    """
    Return the json metadata for a given ooid as an unexpanded string.
    If the ooid doesn't exist, raise not found.
    """
    row_id = ooid_to_row_id(ooid,old_format)
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['meta_data:json'])
    #return listOfRawRows[0].columns["meta_data:json"].value if listOfRawRows else ""
    try:
      if listOfRawRows:
        return listOfRawRows[0].columns["meta_data:json"].value
      else:
        raise OoidNotFoundException("%s - %s" % (ooid, row_id))
    except KeyError, k:
      self.logger.debug('key error trying to get "meta_data:json" from %s', str(listOfRawRows))
      raise

  @optional_retry_wrapper
  def get_json(self,ooid,old_format=False):
    """Return the json metadata for a given ooid as an json data object"""
    jsonColumnOfRow = self.get_json_meta_as_string(ooid,old_format)
    #self.logger.debug('jsonColumnOfRow: %s', jsonColumnOfRow)
    json_data = json.loads(jsonColumnOfRow)
    return json_data

  @optional_retry_wrapper
  def get_dump(self,ooid):
    """
    Return the minidump for a given ooid as a string of bytes
    If the ooid doesn't exist, raise not found
    """
    row_id = ooid_to_row_id(ooid)
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['raw_data:dump'])
    #return listOfRawRows[0].columns["raw_data:dump"].value if listOfRawRows else ""
    try:
      if listOfRawRows:
        return listOfRawRows[0].columns["raw_data:dump"].value
      else:
        raise OoidNotFoundException(ooid)
    except KeyError, k:
      self.logger.debug('key error trying to get "raw_data:dump" from %s', str(listOfRawRows))
      raise

  @optional_retry_wrapper
  def get_raw_report(self,ooid):
    """
    Return the json and dump for a given ooid
    If the ooid doesn't exist, raise not found
    """
    row_id = ooid_to_row_id(ooid)
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['meta_data:json', 'raw_data:dump'])
    #return self._make_row_nice(listOfRawRows[0]) if listOfRawRows else []
    if listOfRawRows:
      return self._make_row_nice(listOfRawRows[0])
    else:
      raise OoidNotFoundException(ooid)

  def get_processed_json_as_string (self,ooid):
    """
    Return the cooked json (jsonz) for a given ooid as a string
    If the ooid doesn't exist, return an empty string.
    """
    row_id = ooid_to_row_id(ooid)
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['processed_data:json'])
    #return listOfRawRows[0].columns["processed_data:json"].value if listOfRawRows else ""
    if listOfRawRows:
      return listOfRawRows[0].columns["processed_data:json"].value
    else:
      raise OoidNotFoundException(ooid)

  @optional_retry_wrapper
  def get_processed_json(self,ooid):
    """
    Return the cooked json (jsonz) for a given ooid as a json object
    If the ooid doesn't exist, return an empty string.
    """
    jsonColumnOfRow = self.get_processed_json_as_string(ooid)
    json_data = json.loads(jsonColumnOfRow)
    return json_data

  @optional_retry_wrapper
  def get_report_processing_state(self,ooid):
    """
    Return the current state of processing for this report and the submitted_timestamp needed
    For processing queue manipulation.
    If the ooid doesn't exist, return an empty array
    """
    row_id = ooid_to_row_id(ooid)
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,
        ['flags:processed', 'flags:priority_processing', 'flags:legacy_processing', 'timestamps:submitted', 'timestamps:processed'])
    #return self._make_row_nice(listOfRawRows[0]) if listOfRawRows else []
    if listOfRawRows:
      return self._make_row_nice(listOfRawRows[0])
    else:
      raise OoidNotFoundException(ooid)

  def export_jsonz_for_date(self,date,path):
    """
    Iterates through all rows for a given date and dumps the processed_data:json out as a jsonz file.
    The implementation opens up 16 scanners (one for each leading hex character of the salt)
    one at a time and returns all of the rows matching
    """

    for row in self.limited_iteration(self.union_scan_with_prefix('crash_reports', date, ['processed_data:json']),10):
      ooid = row_id_to_ooid(row['_rowkey'])
      if row['processed_data:json']:
        file_name = os.path.join(path,ooid+'.jsonz')
        file_handle = None
        try:
          file_handle = gzip.open(file_name,'w',9)
        except IOError,x:
          raise
        try:
          json.dump(row['processed_data:json'],file_handle)
        finally:
          file_handle.close()

  def export_jsonz_tarball_for_date(self,date,path,tarball_name):
    """
    Iterates through all rows for a given date and dumps the processed_data:json out as a jsonz file.
    The implementation opens up 16 scanners (one for each leading hex character of the salt)
    one at a time and returns all of the rows matching
    """
    tf = tarfile.open(tarball_name, 'w:gz')
    try:
      for i, row in enumerate(self.limited_iteration(self.union_scan_with_prefix('crash_reports', date, ['processed_data:json']),10)):
        #if i > 10: break
        ooid = row_id_to_ooid(row['_rowkey'])
        if row['processed_data:json']:
          file_name = os.path.join(path, ooid+'.jsonz')
          file_handle = None
          try:
            file_handle = gzip.open(file_name,'w',9)
          except IOError,x:
            raise
          try:
            json.dump(row['processed_data:json'],file_handle)
          finally:
            file_handle.close()
          tf.add(file_name, os.path.join(ooid[:2], ooid[2:4], ooid +'.jsonz'))
          os.unlink(file_name)
    finally:
      tf.close()

  def export_jsonz_tarball_for_ooids(self,path,tarball_name):
    """
    Creates jsonz files for each ooid passed in on stdin and puts them all in a tarball
    """
    tf = tarfile.open(tarball_name, 'w')
    try:
      for line in sys.stdin.readlines():
        ooid = line.strip()
        self.logger.debug('Ooid: "%s"', ooid)
        if len(ooid) == 36:
          try:
            json = self.get_processed_json_as_string(ooid)
          except OoidNotFoundException, e:
            self.logger.debug('OoidNotFound (No processed_data:json?): %s', ooid)
            continue
          file_name = os.path.join(path, ooid+'.jsonz')
          try:
            file_handle = gzip.open(file_name,'w',9)
          except IOError,x:
            raise
          try:
            file_handle.write(json)
          finally:
            file_handle.close()
          tf.add(file_name, os.path.join(ooid[:2], ooid[2:4], ooid +'.jsonz'))
          os.unlink(file_name)
        else:
          self.logger.debug('Skipping...')
    finally:
      tf.close()

  def resubmit_to_processor(self,
                          processorHostNames,
                          limit='1000',
                          from_queue_table='crash_reports_index_legacy_submitted_time',
                          timestamp_prefix=''):
    limit = int(limit)

    import urllib
    import urllib2
    #TODO move this up to not be a nested method
    def circular_sequence(seq):
      i = 0
      while True:
        yield seq[i]
        i = (i + 1)%len(seq)
    urls = circular_sequence(["http://%s:8881/201006/priority/process/ooid"%processorHostName for processorHostName in processorHostNames.split(',')])

    for row in self.limited_iteration(self.merge_scan_with_prefix(from_queue_table, timestamp_prefix,
                                                                  ['ids:ooid']),limit):
      ooid = row['ids:ooid']

      try:
        params = urllib.urlencode({'ooid':ooid})
        post_result = urllib2.urlopen(urls.next(), params)
        processor_name = post_result.read()
        self.logger.debug('Submitted %s for reprocessing to %s', ooid, processor_name)
      except urllib2.URLError, e:
        self.logger.warning('could not submit %s for processing - %s', ooid, str(e))
      except Exception, e:
        self.logger.warning('something has gone wrong in the submission for %s - %s', ooid, str(e))

  def submit_to_processor(self,
                          processorHostNames,
                          limit='1000',
                          bad_queue_entry_handling='delete', # delete|skip|resubmit
                          legacy_flag='0',
                          from_queue_table='crash_reports_index_legacy_unprocessed_flag',
                          resubmitTimeDeltaThreshold=dt.timedelta(seconds=300)):
    legacy_flag = int(legacy_flag)
    limit = int(limit)

    import urllib
    import urllib2
    #TODO move this up to not be a nested method
    def circular_sequence(seq):
      i = 0
      while True:
        yield seq[i]
        i = (i + 1)%len(seq)
    urls = circular_sequence(["http://%s:8881/201006/process/ooid"%processorHostName for processorHostName in processorHostNames.split(',')])

    for row in self.limited_iteration(self.merge_scan_with_prefix(from_queue_table, '',
                                                                  ['ids:ooid','processor_state:']),limit):
      rowkey = row['_rowkey']
      try:
        ooid = row['ids:ooid']
      except KeyError:
        self.logger.debug('Half deleted row - removing - %s', rowkey)
        self.client.deleteAllRow(from_queue_table, rowkey)
        continue

      try:
        post_timestamp = sdt.datetimeFromISOdateString(row['processor_state:post_timestamp'])
        delta = dt.datetime.now() - post_timestamp
        self.logger.debug('delta: %s; resubmitTimeDeltaThreshold: %s', str(delta), str(resubmitTimeDeltaThreshold))
        self.logger.debug('delta > resubmitTimeDeltaThreshold: %s', delta > resubmitTimeDeltaThreshold)
        doSubmit = delta > resubmitTimeDeltaThreshold
      except (KeyError, ValueError):
        doSubmit = True
      if not doSubmit:
        self.logger.debug('avoiding potential resubmit on %s', ooid)
        continue


      report_row_id = ooid_to_row_id(ooid)
      listOfRawRows = self.client.getRowWithColumns('crash_reports',report_row_id,['meta_data:json', 'raw_data:dump', 'flags:processed'])
      if listOfRawRows:
        report = self._make_row_nice(listOfRawRows[0])
      else:
        if bad_queue_entry_handling == 'delete':
          self.client.deleteAllRow(from_queue_table, rowkey)
        self.logger.debug('OoidNotFound %s - %s', ooid, bad_queue_entry_handling)
        continue

      if report.get('flags:processed', 'N') == 'Y':
        self.logger.debug('OoidPreviouslyProcessed %s - %s', ooid, bad_queue_entry_handling)
        if bad_queue_entry_handling == 'delete':
          self.client.deleteAllRow(from_queue_table, rowkey)
          continue
        elif bad_queue_entry_handling == 'skip':
          continue

      if report.get('meta_data:json', '') == '':
        self.logger.debug('OoidMissingJSON %s - %s', ooid, bad_queue_entry_handling)
        if bad_queue_entry_handling == 'delete':
          self.client.deleteAllRow(from_queue_table, rowkey)
          continue
        elif bad_queue_entry_handling == 'skip':
          continue

      if report.get('raw_data:dump', '') == '':
        self.logger.debug('OoidMissingDump %s - %s', ooid, bad_queue_entry_handling)
        if bad_queue_entry_handling == 'delete':
          self.client.deleteAllRow(from_queue_table, rowkey)
          continue
        elif bad_queue_entry_handling == 'skip':
          continue

      try:
        params = urllib.urlencode({'ooid':ooid})
        post_result = urllib2.urlopen(urls.next(), params)
        processor_name = post_result.read()
        self.update_unprocessed_queue_with_processor_state(
                rowkey,
                dt.datetime.now().isoformat(),
                processor_name,
                legacy_flag)
      except urllib2.URLError, e:
        self.logger.warning('could not submit %s for processing - %s', ooid, str(e))
      except Exception, e:
        self.logger.warning('something has gone wrong in the submission for %s - %s', ooid, str(e))

  def union_scan_with_prefix(self,table,prefix,columns):
    #TODO: Need assertion for columns contains at least 1 element
    """
    A lazy chain of iterators that yields unordered rows starting with a given prefix.
    The implementation opens up 16 scanners (one for each leading hex character of the salt)
    one at a time and returns all of the rows matching
    """

    for salt in '0123456789abcdef':
      salted_prefix = "%s%s" % (salt,prefix)
      scanner = self.client.scannerOpenWithPrefix(table, salted_prefix, columns)
      for rowkey,row in salted_scanner_iterable(self.logger,self.client,self._make_row_nice,salted_prefix,scanner):
        yield row

  def merge_scan_with_prefix(self,table,prefix,columns,salts='0123456789abcdef'):
    #TODO: Need assertion that columns is array containing at least one string
    """
    A generator based iterator that yields totally ordered rows starting with a given prefix.
    The implementation opens up 16 scanners (one for each leading hex character of the salt)
    simultaneously and then yields the next row in order from the pool on each iteration.
    """

    iterators = []
    next_items_queue = []
    for salt in salts:
      salted_prefix = "%s%s" % (salt,prefix)
      scanner = self.client.scannerOpenWithPrefix(table, salted_prefix, columns)
      iterators.append(salted_scanner_iterable(self.logger,self.client,self._make_row_nice,salted_prefix,scanner))
    # The i below is so we can advance whichever scanner delivers us the polled item.
    for i,it in enumerate(iterators):
      try:
        next = it.next
        next_items_queue.append([next(),i,next])
      except StopIteration:
        pass
    heapq.heapify(next_items_queue)

    while 1:
      try:
        while 1:
          row_tuple,iter_index,next = s = next_items_queue[0]
          #tuple[1] is the actual nice row.
          yield row_tuple[1]
          s[0] = next()
          heapq.heapreplace(next_items_queue, s)
      except StopIteration:
        heapq.heappop(next_items_queue)
      except IndexError:
        return

  def limited_iteration(self,iterable,limit=10**6):
    #self.logger.debug('limit = %d' % limit)
    return itertools.islice(iterable,limit)

  @retry_wrapper_for_generators
  def deleting_iterator_for_table(self, table_name, queue_type, limit=10**6, salts='0123456789abcdef'):
    #self.logger.debug('deleting_iterator_for_table %s' % table_name)
    for row in self.limited_iteration(self.merge_scan_with_prefix(table_name,
                                                                  '',
                                                                  ['ids:ooid'],
                                                                  salts), limit):
      yield row['ids:ooid']
      # Delete the row after the feeder has returned from processing it.
      self.client.deleteAllRow(table_name, row['_rowkey'])
      self.update_metrics_counters_current_queue_size([queue_type])

  def iterator_for_legacy_db_feeder_queue(self,limit=10**6, salts='0123456789abcdef'):
    return self.deleting_iterator_for_table('crash_reports_index_legacy_processed', 'deletes_processed_legacy', limit, salts)

  def insert_to_legacy_db_feeder_queue(self,ooid,timestamp):
    self.put_crash_report_indices(ooid,timestamp,['crash_reports_index_legacy_processed'])

  def iterator_for_priority_db_feeder_queue(self,limit=10**6, salts='0123456789abcdef'):
    return self.deleting_iterator_for_table('crash_reports_index_priority_processed', 'deletes_processed_priority', limit, salts)

  def insert_to_priority_db_feeder_queue(self,ooid,timestamp):
    self.put_crash_report_indices(ooid,timestamp,['crash_reports_index_priority_processed'])

  @optional_retry_wrapper
  def put_crash_report_indices(self,ooid,timestamp,indices):
    row_id = guid_to_timestamped_row_id(ooid,timestamp)
    for index_name in indices:
      self.client.mutateRow(index_name,row_id,[self.mutationClass(column="ids:ooid",value=ooid)])

  @optional_retry_wrapper
  def put_crash_report_hang_indices(self,ooid,hang_id,process_type,timestamp):
    ooid_column_name = "ids:ooid:"+process_type
    self.client.mutateRow('crash_reports_index_hang_id_submitted_time',
                          guid_to_timestamped_row_id(hang_id,timestamp),
                          [self.mutationClass(column=ooid_column_name,value=ooid)])
    self.client.mutateRow('crash_reports_index_hang_id',
                          hang_id,
                          [self.mutationClass(column=ooid_column_name,value=ooid)])

  def update_metrics_counters_current_queue_size(self, queue_types):
    for queueType in queue_types:
      self.client.atomicIncrement('metrics','crash_report_queues',("counters:%s"%queueType),1)

  @optional_retry_wrapper
  def update_metrics_counters_for_process(self, processed_timestamp, priority_processing, legacy_processing, is_oob_signature, signature):
    """
    Increments a series of counters in the 'metrics' table related to CR processing
    """

    timeLevels = [ processed_timestamp[:16], # minute yyyy-mm-ddTHH:MM
                   processed_timestamp[:13], # hour   yyyy-mm-ddTHH
                   processed_timestamp[:10], # day    yyyy-mm-dd
                   processed_timestamp[: 7], # month  yyyy-mm
                   processed_timestamp[: 4]  # year   yyyy
                 ]
    counterIncrementList = [ 'counters:processed_crash_reports' ]
    queueTypes = ['deletes_unprocessed','inserts_processed']

    if priority_processing == 'Y':
      counterIncrementList.append("counters:processed_crash_reports_priority")
      queueTypes.append('deletes_unprocessed_priority')
      queueTypes.append('inserts_processed_priority')
      if legacy_processing == 'Y':
        queueTypes.append('deletes_unprocessed_legacy')
    elif legacy_processing == 'Y':
      counterIncrementList.append("counters:processed_crash_reports_legacy")
      queueTypes.append('deletes_unprocessed_legacy')
      queueTypes.append('inserts_processed_legacy')

    if is_oob_signature:
      counterIncrementList.append("counters:processed_crash_reports_oob_signature_%s" % signature)

    self.update_metrics_counters_current_queue_size(queueTypes)
    for rowkey in timeLevels:
      for column in counterIncrementList:
        self.client.atomicIncrement('metrics',rowkey,column,1)

  @optional_retry_wrapper
  def update_metrics_counters_for_submit(self, submitted_timestamp,
                                         legacy_processing, process_type,is_hang):
    """
    Increments a series of counters in the 'metrics' table related to CR submission
    """

    timeLevels = [ submitted_timestamp[:16], # minute yyyy-mm-ddTHH:MM
                   submitted_timestamp[:13], # hour   yyyy-mm-ddTHH
                   submitted_timestamp[:10], # day    yyyy-mm-dd
                   submitted_timestamp[: 7], # month  yyyy-mm
                   submitted_timestamp[: 4]  # year   yyyy
                 ]
    counterIncrementList = [ 'counters:submitted_crash_reports',
                             ("counters:submitted_crash_reports_legacy_throttle_%d" % legacy_processing)
                           ]
    queueTypes = ['inserts_unprocessed']

    if legacy_processing == 0:
      queueTypes.append('inserts_unprocessed_legacy')

    if process_type != 'default':
      if is_hang:
        counterIncrementList.append("counters:submitted_crash_report_hang_pairs")
      else:
        counterIncrementList.append("counters:submitted_oop_%s_crash_reports" % process_type)

    self.update_metrics_counters_current_queue_size(queueTypes)
    for rowkey in timeLevels:
      for column in counterIncrementList:
        self.client.atomicIncrement('metrics',rowkey,column,1)

  @optional_retry_wrapper
  def put_json_dump(self, ooid, json_data, dump):
    """
    Create a crash report record in hbase from serialized json and
    bytes of the minidump
    """
    row_id = ooid_to_row_id(ooid)
    submitted_timestamp = json_data['submitted_timestamp']
    json_string = json.dumps(json_data)

    # Extract ACCEPT(0), DEFER(1), DISCARD(2) enum or 0 if not found.
    legacy_processing = json_data.get('legacy_processing', 0)

    columns =  [ ("flags:processed", "N"),
                 ("meta_data:json", json_string),
                 ("timestamps:submitted", submitted_timestamp),
                 ("ids:ooid", ooid),
                 ("raw_data:dump", dump)
               ]
    mutationList = [ self.mutationClass(column=c, value=v)
                         for c, v in columns if v is not None]

    indices = ['crash_reports_index_submitted_time', 'crash_reports_index_unprocessed_flag']

    if legacy_processing == 0:
      mutationList.append(self.mutationClass(column="flags:legacy_processing",value='Y'))
      indices.append('crash_reports_index_legacy_unprocessed_flag')
      indices.append('crash_reports_index_legacy_submitted_time')

    # Use ProcessType value if exists, otherwise, default (i.e. a standard application crash report)
    process_type = json_data.get('ProcessType','default')

    is_hang = 'HangID' in json_data
    if is_hang:
      hang_id = json_data['HangID']
      mutationList.append(self.mutationClass(column="ids:hang",value=hang_id))

    self.client.mutateRow('crash_reports', row_id, mutationList) # unit test marker 233

    self.put_crash_report_indices(ooid,submitted_timestamp,indices)
    if is_hang:
      self.put_crash_report_hang_indices(ooid,hang_id,process_type,submitted_timestamp)

    self.update_metrics_counters_for_submit(submitted_timestamp,legacy_processing,process_type,is_hang)

    return (guid_to_timestamped_row_id(ooid,submitted_timestamp), legacy_processing)

  def update_unprocessed_queue_with_processor_state(self, queue_row_id, processor_post_timestamp, processor_name, legacy_processing):
    mutationList = [
        self.mutationClass(column="processor_state:name",value=processor_name),
        self.mutationClass(column="processor_state:post_timestamp",value=processor_post_timestamp)]

    indices = ['crash_reports_index_unprocessed_flag']
    if legacy_processing == 0:
      indices.append('crash_reports_index_legacy_unprocessed_flag')

    for index_name in indices:
      self.client.mutateRow(index_name,queue_row_id,mutationList)

  def put_json_dump_from_files(self,ooid,json_path,dump_path,openFn=open):
    """
    Convenience method for creating an ooid from disk
    """
    json_file = open(json_path,'r')
    try:
      json = json_file.read()
    finally:
      json_file.close()
    #Apparently binary mode only matters in windows, but it won't hurt anything on unix systems.
    dump_file = open(dump_path,'rb')
    try:
      dump = dump_file.read()
    finally:
      dump_file.close()
    self.put_json_dump(ooid,json,dump)

  @optional_retry_wrapper
  def put_priority_flag(self,ooid):
    """
    Add the priority processing flag to a crash report
    This flag will cause a processed report to be added to the priority dbfeeder queue
    """
    self.client.mutateRow('crash_reports', ooid_to_row_id(ooid),
        [self.mutationClass(column="flags:priority_processing",value='Y')])
    self.update_metrics_counters_current_queue_size(['inserts_unprocessed_priority'])

  @optional_retry_wrapper
  def put_processed_json(self,ooid,processed_json):
    """
    Create a crash report from the cooked json output of the processor
    """
    row_id = ooid_to_row_id(ooid)

    processing_state = self.get_report_processing_state(ooid)
    submitted_timestamp = processing_state.get('timestamps:submitted', processed_json.get('date_processed','unknown'))
    legacy_processing = processing_state.get('flags:legacy_processing', 'Y')
    priority_processing = processing_state.get('flags:priority_processing', 'N')

    index_row_key = guid_to_timestamped_row_id(ooid, submitted_timestamp)
    self.client.deleteAllRow('crash_reports_index_unprocessed_flag', index_row_key)
    self.client.deleteAllRow('crash_reports_index_legacy_unprocessed_flag', index_row_key)

    processed_timestamp = processed_json['completed_datetime']

    is_oob_signature = False
    if 'signature' in processed_json:
      if len(processed_json['signature']) > 0:
        signature = processed_json['signature']
      else:
        signature = '##empty##'
        is_oob_signature = True
    else:
      signature = '##null##'
      is_oob_signature = True

    processed_json = json.dumps(processed_json, cls=IterableJsonEncoder)

    mutationList = []
    mutationList.append(self.mutationClass(column="timestamps:processed",value=processed_timestamp))
    mutationList.append(self.mutationClass(column="processed_data:signature",value=signature))
    mutationList.append(self.mutationClass(column="processed_data:json",value=processed_json))
    mutationList.append(self.mutationClass(column="flags:processed",value="Y"))

    self.client.mutateRow('crash_reports',row_id,mutationList)

    # Supply Socorro 1.8 DB Feeder with data it needs
    if priority_processing == 'Y':
      self.insert_to_priority_db_feeder_queue(ooid,submitted_timestamp)
    elif legacy_processing == 'Y':
      self.insert_to_legacy_db_feeder_queue(ooid,submitted_timestamp)

    sig_ooid_idx_row_key = signature + ooid
    self.client.mutateRow('crash_reports_index_signature_ooid', sig_ooid_idx_row_key,
                          [self.mutationClass(column="ids:ooid",value=ooid)])

    self.update_metrics_counters_for_process(processed_timestamp, priority_processing, legacy_processing, is_oob_signature, signature)

def salted_scanner_iterable(logger,client,make_row_nice,salted_prefix,scanner):
  """
  Generator based iterable that runs over an HBase scanner
  yields a tuple of the un-salted rowkey and the nice format of the row.
  """
  #logger.debug('Scanner %s generated', salted_prefix)
  raw_rows = client.scannerGet(scanner)
  while raw_rows:
    nice_row = make_row_nice(raw_rows[0])
    #logger.debug('Scanner %s returning nice_row (%s) for raw_rows (%s)' % (self.salted_prefix,nice_row,raw_rows))
    yield (nice_row['_rowkey'][1:], nice_row)
    raw_rows = client.scannerGet(scanner)
  #logger.debug('Scanner %s exhausted' % salted_prefix)
  client.scannerClose(scanner)

# TODO: Warning, the command line methods haven't been tested for bitrot
if __name__=="__main__":
  import pprint
  import sys

  def ppjson(data, sort_keys=False, indent=4):
    print json.dumps(data, sort_keys, indent)

  def usage():
    print """
  Usage: %s [-h host[:port]] command [arg1 [arg2...]]

  Commands:
    Crash Report specific:
      get_queue_statistics
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
      export_jsonz_tarball_for_ooids temp_path tarball_name <stdin list of ooids>
      submit_to_processor processor_host_name [limit=1000 [bad_queue_entry_handling=delete(delete|skip|resubmit) [legacy_flag=0(0|1) [from_queue_table=crash_reports_index_legacy_unprocessed_flag]]]]
      resubmit_to_processor processor_host_name [limit=1000 [from_queue_table=crash_reports_index_legacy_unprocessed_flag]]
    HBase generic:
      describe_table table_name
      get_full_row table_name row_id
  """ % sys.argv[0]

  if len(sys.argv) <= 1 or sys.argv[1] == '--help':
    usage()
    sys.exit(0)

  pp = pprint.PrettyPrinter(indent = 2)
  host = 'cm-hadoop-dev02'
  port = 9090
  argi = 1

  if sys.argv[argi] == '-h':
    parts = sys.argv[argi+1].split(':')
    host = parts[0]
    if len(parts) == 2:
      port = int(parts[1])
    argi += 2


  cmd = sys.argv[argi]
  args = sys.argv[argi+1:]

  connection = HBaseConnectionForCrashReports(host, port, 5000, logger=utl.FakeLogger())


  if cmd == 'get_queue_statistics':
    if len(args) != 0:
      usage()
      sys.exit(1)
    pp.pprint(connection.get_queue_statistics())
  elif cmd == 'get_report':
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
    for row in connection.limited_iteration(connection.union_scan_with_prefix(args[0],args[1],columns),limit):
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
    for row in connection.limited_iteration(connection.merge_scan_with_prefix(args[0],args[1],columns),limit):
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

  elif cmd == 'resubmit_to_processor':
    if len(args) == 0 or len(args) > 4:
      usage()
      sys.exit(1)
    connection.resubmit_to_processor(*args)

  elif cmd == 'submit_to_processor':
    if len(args) == 0 or len(args) > 5:
      usage()
      sys.exit(1)
    connection.submit_to_processor(*args)

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

# vi: expandtab sw=2 ts=2

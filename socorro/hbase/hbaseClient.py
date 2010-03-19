#!/usr/bin/python
try:
  import json
except ImportError:
  import simplejson as json

import sys

from thrift import Thrift
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from hbase import ttypes
from hbase.hbasethrift import Client, ColumnDescriptor, Mutation

def retry_wrapper(fn):
  """a decorator to add retry symantics to any method that uses hbase"""
  def f(self, *args, **kwargs):
    try:
      return fn(self, *args, **kwargs)
    except self.hbaseThriftExceptions:
      try:
        self.close()
      except self.hbaseThriftExceptions:
        pass
      self.make_connection()
      return fn(self, *args, **kwargs)
  return f

def ooid_to_row_id(ooid):
  return ooid[-6:]+ooid

class HBaseConnection(object):
  """
  Base class for hbase connections.  Supplies methods for a few basic
  queries and methods for cleanup of thrift results.
  """
  def __init__(self,host,port,
               thrift=Thrift,
               tsocket=TSocket,
               ttrans=TTransport,
               protocol=TBinaryProtocol,
               ttp=ttypes,
               client=Client,
               column=ColumnDescriptor,
               mutation=Mutation):
    self.host = host
    self.port = port
    self.thriftModule = thrift
    self.tsocketModule = tsocket
    self.transportModule = ttrans
    self.protocolModule = protocol
    self.ttypesModule = ttp
    self.clientClass = client
    self.columnClass = column
    self.mutationClass = mutation
    self.hbaseThriftExceptions = (self.ttypesModule.IOError,
                                  self.ttypesModule.IllegalArgument,
                                  self.ttypesModule.AlreadyExists,
                                  self.thriftModule.TException)

    self.make_connection()

  def make_connection(self, retry=2):
    """Establishes the underlying connection to hbase"""
    while retry:
      retry -= 1
      try:
        # Make socket
        transport = self.tsocketModule.TSocket(self.host, self.port)
        # Buffering is critical. Raw sockets are very slow
        self.transport = self.transportModule.TBufferedTransport(transport)
        # Wrap in a protocol
        self.protocol = self.protocolModule.TBinaryProtocol(self.transport)
        # Create a client to use the protocol encoder
        self.client = self.clientClass(self.protocol)
        # Connect!
        self.transport.open()
        return
      except self.hbaseThriftExceptions, x:
        pass
    exceptionType, exception, tracebackInfo = sys.exc_info()
    raise exception

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
    #res = (self._make_row_nice(row) for row in client_result_object)
    return res

  def _make_row_nice(self,client_row_object):
    """
    Pull out the contents of the thrift column result objects into a python dict
    """
    return dict(((x,y.value) for x,y in client_row_object.columns.items()))
    #columns = {}
    #for column in client_row_object.columns.keys():
      #columns[column]=client_row_object.columns[column].value
    #return columns

  @retry_wrapper
  def describe_table(self,table_name):
    return self.client.getColumnDescriptors(table_name)

  @retry_wrapper
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
               thrift=Thrift,
               tsocket=TSocket,
               ttrans=TTransport,
               protocol=TBinaryProtocol,
               ttp=ttypes,
               client=Client,
               column=ColumnDescriptor,
               mutation=Mutation):
    super(HBaseConnectionForCrashReports,self).__init__(host,port,thrift,tsocket,ttrans,
                                                        protocol,ttp,client,column,
                                                        mutation)

  def _make_row_nice(self,client_row_object):
    columns = super(HBaseConnectionForCrashReports,self)._make_row_nice(client_row_object)
    columns['ooid'] = client_row_object.row[6:]
    return columns

  def get_report(self,ooid):
    """
    Return the full row for a given ooid
    """
    row_id = ooid_to_row_id(ooid)
    return self.get_full_row('crash_reports',row_id)[0]

  @retry_wrapper
  def get_json_meta_as_string(self,ooid):
    """Return the json metadata for a given ooid as an unexpanded string"""
    row_id = ooid_to_row_id(ooid)
    # original code
    #return json.loads(self._make_rows_nice(self.client.getRowWithColumns('crash_reports',row_id,['meta_data:json']))[0]["meta_data:json"])

    # original code expanded for readability:
    #listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['meta_data:json'])
    #listOfRows = self._make_rows_nice(listOfRawRows)
    #aRow = listOfRows[0]
    #jsonColumnOfRow = aRow["meta_data:json"]
    #jsonData = json.loads(jsonColumnOfRow)
    #return jsonData

    # code made more efficient:
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['meta_data:json'])
    aRow = listOfRawRows[0]
    return aRow.columns["meta_data:json"]

  def get_json(self,ooid):
    """Return the json metadata for a given ooid as an json data object"""
    jsonColumnOfRow = self.get_json_meta_as_string(ooid)
    try:
      jsonData = json.loads(jsonColumnOfRow.value)
    except ValueError:
      raise
      #jsonData = eval(jsonColumnOfRow.value)  #dangerous but required for Bug 552539
    return jsonData

  @retry_wrapper
  def get_dump(self,ooid):
    """
    Return the minidump for a given ooid
    """
    row_id = ooid_to_row_id(ooid)
    # original code
    #return self.client.getRowWithColumns('crash_reports',row_id,['raw_data:dump'])[0].columns['raw_data:dump'].value

    # original code expanded for readability
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['raw_data:dump'])
    aRow = listOfRawRows[0]
    aRowAsDict = aRow.columns
    return aRowAsDict['raw_data:dump'].value

  @retry_wrapper
  def get_jsonz_as_string (self,ooid):
    """Return the cooked json for a given ooid"""
    row_id = ooid_to_row_id(ooid)
    # original code:
    #return json.loads(self._make_rows_nice(self.client.getRowWithColumns('crash_reports',row_id,['processed_data:json']))[0]["processed_data:json"])

    # original code expanded for readability:
    #listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['processed_data:json'])
    #listOfRows = self._make_rows_nice(listOfRawRows)
    #aRow = listOfRows[0]
    #jsonColumnOfRow = aRow["processed_data:json"]
    #jsonData = json.loads(jsonColumnOfRow)
    #return jsonData

    # code made more efficient:
    listOfRawRows = self.client.getRowWithColumns('crash_reports',row_id,['processed_data:json'])
    aRow = listOfRawRows[0]
    return aRow.columns["processed_data:json"]

  def get_jsonz(self,ooid):
    """Return the cooked json for a given ooid"""
    jsonColumnOfRow = self.get_jsonz_as_string(ooid)
    jsonData = json.loads(jsonColumnOfRow.value)
    return jsonData

  #@retry_wrapper
  def scan_starting_with(self,prefix,limit=None):
    """
    Reurns a generator yield rows starting with prefix.  Remember
    that ooids are stored internally with their 6 digit date used as a prefix!
    """
    scanner = self.client.scannerOpenWithPrefix('crash_reports', prefix, ['meta_data:json'])
    i = 1
    r = self.client.scannerGet(scanner)
    while r and (not limit or i < int(limit)):
      yield self._make_row_nice(r[0])
      r = self.client.scannerGet(scanner)
      i+=1
    self.client.scannerClose(scanner)

  @retry_wrapper
  def put_json_dump(self,ooid,jsonString,dump):
    """
    Create a crash report record in hbase from serialized json and
    bytes of the minidump
    """
    row_id = ooid_to_row_id(ooid)
    jsonMutationObject = self.mutationClass(column="meta_data:json",value=jsonString)
    dumpMutationObject = self.mutationClass(column="raw_data:dump",value=dump)
    self.client.mutateRow('crash_reports',row_id,[jsonMutationObject, dumpMutationObject])
  create_ooid = put_json_dump  # backward compatabity

  def put_json_data_dump(self,ooid,jsonData,dump):
    """
    Create a crash report record in hbase from json data object and
    bytes of the minidump
    """
    jsonAsString = json.dumps(jsonData)
    self.put_json_dump(ooid, jsonAsString, dump)

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
  create_ooid_from_file = put_json_dump_from_files  # backward compatabity

  @retry_wrapper
  def put_jsonz(self,ooid,jsonz_string):
    """
    Create a crash report from the cooked json output of the processor
    """
    row_id = ooid_to_row_id(ooid)
    self.client.mutateRow('crash_reports',row_id,[self.mutationClass(column="processed_data:json",value=jsonz_string)])
  create_ooid_from_jsonz = put_jsonz

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
      get_report ooid
      get_json ooid
      get_dump ooid
      scan_starting_with YYMMDD [limit]
      create_ooid ooid json dump
      create_ooid_from_file ooid json_path dump_path
      test
    HBase generic:
      describe_table table_name
      get_full_row table_name row_id
  """ % sys.argv[0]

  if len(sys.argv) <= 1 or sys.argv[1] == '--help':
    usage()
    sys.exit(0)

  pp = pprint.PrettyPrinter(indent = 2)
  host = 'localhost'
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

  connection = HBaseConnectionForCrashReports(host, port)

  if cmd == 'get_report':
    if len(args) != 1:
      usage()
      sys.exit(1)
    pp.pprint(connection.get_report(*args))

  elif cmd == 'get_json':
    if len(args) != 1:
      usage()
      sys.exit(1)
    ppjson(connection.get_json(*args))

  elif cmd == 'get_dump':
    if len(args) != 1:
      usage()
      sys.exit(1)
    print(connection.get_dump(*args))

  elif cmd == 'scan_starting_with':
    if len(args) < 1:
      usage()
      sys.exit(1)
    for row in connection.scan_starting_with(*args):
      ppjson(row)

  elif cmd == 'create_ooid':
    if len(args) != 3:
      usage()
      sys.exit(1)
    ppjson(connection.create_ooid(*args))

  elif cmd == 'create_ooid_from_file':
    if len(args) != 3:
      usage()
      sys.exit(1)
    ppjson(connection.create_ooid_from_file(*args))

  elif cmd == 'describe_table':
    if len(args) != 1:
      usage()
      sys.exit(1)
    ppjson(connection.describe_table(*args))

  elif cmd == 'get_full_row':
    if len(args) != 2:
      usage()
      sys.exit(1)
    pp.pprint(connection.get_full_row(*args))

  connection.close()

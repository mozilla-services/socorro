#!/usr/bin/python
import simplejson as json

from thrift import Thrift
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from hbase import ttypes
from hbase.hbasethrift import Client, ColumnDescriptor, Mutation

class HBaseConnection(object):
  def __init__(self,host,port):
    # Make socket
    transport = TSocket.TSocket(host, port)
    # Buffering is critical. Raw sockets are very slow
    self.transport = TTransport.TBufferedTransport(transport)
    # Wrap in a protocol
    self.protocol = TBinaryProtocol.TBinaryProtocol(self.transport)
    # Create a client to use the protocol encoder
    self.client = Client(self.protocol)
    # Connect!
    self.transport.open()

  def close(self):
    self.transport.close()

  def _make_rows_nice(self,client_result_object):
    res = [self._make_row_nice(row) for row in client_result_object]
    return res

  def _make_row_nice(self,client_row_object):
    columns = {}
    for column in client_row_object.columns.keys():
      columns[column]=client_row_object.columns[column].value
    return columns

  def describe_table(self,table_name):
    return self.client.getColumnDescriptors(table_name)

  def get_full_row(self,table_name, row_id):
    return self._make_rows_nice(self.client.getRow(table_name, row_id))

class HBaseConnectionForCrashReports(HBaseConnection):
  def __init__(self,host,port):
    super(HBaseConnectionForCrashReports,self).__init__(host,port)

  def _make_row_nice(self,client_row_object):
    columns = super(HBaseConnectionForCrashReports,self)._make_row_nice(client_row_object)
    columns['ooid'] = client_row_object.row[6:]
    return columns

  def get_report(self,ooid):
    return self.get_full_row('crash_reports',ooid[-6:]+ooid)[0]

  def get_json(self,ooid):
    return json.loads(self._make_rows_nice(self.client.getRowWithColumns('crash_reports',ooid[-6:]+ooid,['meta_data:json']))[0]["meta_data:json"])

  def get_dump(self,ooid):
    return self.client.getRowWithColumns('crash_reports',ooid[-6:]+ooid,['raw_data:dump'])[0].columns['raw_data:dump'].value

  def scan_starting_with(self,prefix,limit=None):
    scanner = self.client.scannerOpenWithPrefix('crash_reports', prefix, ['meta_data:json'])
    i = 0
    r = self.client.scannerGet(scanner)
    while r and (not limit or i < int(limit)):
      yield self._make_row_nice(r[0])
      r = self.client.scannerGet(scanner)
      i+=1
    self.client.scannerClose(scanner)

  def create_ooid(self,ooid,json,dump):
    row_id = ooid[-6:]+ooid
    self.client.mutateRow('crash_reports',row_id,[Mutation(column="meta_data:json",value=json), Mutation(column="raw_data:dump",value=dump)])

  def create_ooid_from_file(self,ooid,json_path,dump_path):
    json_file = open(json_path,'r')
    #Apparently binary mode only matters in windows, but it won't hurt anything on unix systems.
    dump_file = open(dump_path,'rb')
    json = json_file.read()
    dump = dump_file.read()
    json_file.close()
    dump_file.close()
    self.create_ooid(ooid,json,dump)

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

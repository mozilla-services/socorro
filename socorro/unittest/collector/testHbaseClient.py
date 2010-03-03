import socorro.collector.hbaseClient as hbc
import socorro.unittest.testlib.expectations as exp

try:
  import json as js
except ImportError:
  import simplejson as js

class ValueObject(object):
  def __init__(self, value):
    self.value = value

def testHBaseConnection_constructor_1():
  dummy_thriftModule = exp.DummyObjectWithExpectations('dummy_thriftModule')
  dummy_tsocketModule = exp.DummyObjectWithExpectations('dummy_tsocketModule')
  dummy_transportModule = exp.DummyObjectWithExpectations('dummy_transportModule')
  dummy_protocolModule = exp.DummyObjectWithExpectations('dummy_protocolModule')
  dummy_ttypesModule = exp.DummyObjectWithExpectations('dummy_ttypesModule')
  dummy_clientClass = exp.DummyObjectWithExpectations('dummy_clientClass')
  dummy_columnClass = exp.DummyObjectWithExpectations('dummy_columnClass')
  dummy_mutationClass = exp.DummyObjectWithExpectations('dummy_mutationClass')

  class FakeIOError(Exception):
    pass
  class FakeIllegalArgument(Exception):
    pass
  class FakeAlreadyExists(Exception):
    pass
  class FakeTException(Exception):
    pass

  dummy_ttypesModule.expect('IOError', None, None, FakeIOError, None)
  dummy_ttypesModule.expect('IllegalArgument', None, None, FakeIllegalArgument, None)
  dummy_ttypesModule.expect('AlreadyExists', None, None, FakeAlreadyExists, None)
  dummy_thriftModule.expect('TException', None, None, FakeTException, None)

  dummy_transportObject = exp.DummyObjectWithExpectations('dummy_transportObject')
  dummy_protocolObject = exp.DummyObjectWithExpectations('dummy_protocolObject')
  dummy_clientObject = exp.DummyObjectWithExpectations('dummy_clientObject')

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  dummy_transportObject.expect('open', (), {})
  dummy_transportObject.expect('close', (), {})

  conn = hbc.HBaseConnection('somehostname', 666,
                             thrift=dummy_thriftModule,
                             tsocket=dummy_tsocketModule,
                             ttrans=dummy_transportModule,
                             protocol=dummy_protocolModule,
                             ttp=dummy_ttypesModule,
                             client=dummy_clientClass,
                             column=dummy_columnClass,
                             mutation=dummy_mutationClass)
  conn.close()

def testHBaseConnection_constructor_2():
  dummy_thriftModule = exp.DummyObjectWithExpectations('dummy_thriftModule')
  dummy_tsocketModule = exp.DummyObjectWithExpectations('dummy_tsocketModule')
  dummy_transportModule = exp.DummyObjectWithExpectations('dummy_transportModule')
  dummy_protocolModule = exp.DummyObjectWithExpectations('dummy_protocolModule')
  dummy_ttypesModule = exp.DummyObjectWithExpectations('dummy_ttypesModule')
  dummy_clientClass = exp.DummyObjectWithExpectations('dummy_clientClass')
  dummy_columnClass = exp.DummyObjectWithExpectations('dummy_columnClass')
  dummy_mutationClass = exp.DummyObjectWithExpectations('dummy_mutationClass')

  class FakeIOError(Exception):
    pass
  class FakeIllegalArgument(Exception):
    pass
  class FakeAlreadyExists(Exception):
    pass
  class FakeTException(Exception):
    pass

  dummy_ttypesModule.expect('IOError', None, None, FakeIOError, None)
  dummy_ttypesModule.expect('IllegalArgument', None, None, FakeIllegalArgument, None)
  dummy_ttypesModule.expect('AlreadyExists', None, None, FakeAlreadyExists, None)
  dummy_thriftModule.expect('TException', None, None, FakeTException, None)

  dummy_transportObject = exp.DummyObjectWithExpectations('dummy_transportObject')
  dummy_protocolObject = exp.DummyObjectWithExpectations('dummy_protocolObject')
  dummy_clientObject = exp.DummyObjectWithExpectations('dummy_clientObject')

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  dummy_transportObject.expect('open', (), {}, None, FakeTException('bad news'))  #transport fails 1st time

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  dummy_transportObject.expect('open', (), {}) #transport succeeds
  dummy_transportObject.expect('close', (), {})

  conn = hbc.HBaseConnection('somehostname', 666,
                             thrift=dummy_thriftModule,
                             tsocket=dummy_tsocketModule,
                             ttrans=dummy_transportModule,
                             protocol=dummy_protocolModule,
                             ttp=dummy_ttypesModule,
                             client=dummy_clientClass,
                             column=dummy_columnClass,
                             mutation=dummy_mutationClass)
  conn.close()


def testHBaseConnection_constructor_3():
  dummy_thriftModule = exp.DummyObjectWithExpectations('dummy_thriftModule')
  dummy_tsocketModule = exp.DummyObjectWithExpectations('dummy_tsocketModule')
  dummy_transportModule = exp.DummyObjectWithExpectations('dummy_transportModule')
  dummy_protocolModule = exp.DummyObjectWithExpectations('dummy_protocolModule')
  dummy_ttypesModule = exp.DummyObjectWithExpectations('dummy_ttypesModule')
  dummy_clientClass = exp.DummyObjectWithExpectations('dummy_clientClass')
  dummy_columnClass = exp.DummyObjectWithExpectations('dummy_columnClass')
  dummy_mutationClass = exp.DummyObjectWithExpectations('dummy_mutationClass')

  class FakeIOError(Exception):
    pass
  class FakeIllegalArgument(Exception):
    pass
  class FakeAlreadyExists(Exception):
    pass
  class FakeTException(Exception):
    pass

  dummy_ttypesModule.expect('IOError', None, None, FakeIOError, None)
  dummy_ttypesModule.expect('IllegalArgument', None, None, FakeIllegalArgument, None)
  dummy_ttypesModule.expect('AlreadyExists', None, None, FakeAlreadyExists, None)
  dummy_thriftModule.expect('TException', None, None, FakeTException, None)

  dummy_transportObject = exp.DummyObjectWithExpectations('dummy_transportObject')
  dummy_protocolObject = exp.DummyObjectWithExpectations('dummy_protocolObject')
  dummy_clientObject = exp.DummyObjectWithExpectations('dummy_clientObject')

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  dummy_transportObject.expect('open', (), {}, None, FakeTException('bad news'))  #transport fails 1st time

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  theExpectedException = FakeTException('bad news')

  dummy_transportObject.expect('open', (), {}, None, theExpectedException)  #transport fails 2nd time
  dummy_transportObject.expect('close', (), {})

  try:
    conn = hbc.HBaseConnection('somehostname', 666,
                               thrift=dummy_thriftModule,
                               tsocket=dummy_tsocketModule,
                               ttrans=dummy_transportModule,
                               protocol=dummy_protocolModule,
                               ttp=dummy_ttypesModule,
                               client=dummy_clientClass,
                               column=dummy_columnClass,
                               mutation=dummy_mutationClass)
  except Exception, x:
    assert x == theExpectedException, "expected %s, but got %s" % (str(theExpectedException), str(x))
  else:
    assert False, "expected the exception %s, but no exception was raised" % str(theExpectedException)

class UsefulHbaseConnection(object):
  def __init__(self):
    self.dummy_thriftModule = exp.DummyObjectWithExpectations('dummy_thriftModule')
    self.dummy_tsocketModule = exp.DummyObjectWithExpectations('dummy_tsocketModule')
    self.dummy_transportModule = exp.DummyObjectWithExpectations('dummy_transportModule')
    self.dummy_protocolModule = exp.DummyObjectWithExpectations('dummy_protocolModule')
    self.dummy_ttypesModule = exp.DummyObjectWithExpectations('dummy_ttypesModule')
    self.dummy_clientClass = exp.DummyObjectWithExpectations('dummy_clientClass')
    self.dummy_columnClass = exp.DummyObjectWithExpectations('dummy_columnClass')
    self.dummy_mutationClass = exp.DummyObjectWithExpectations('dummy_mutationClass')

    class FakeIOError(Exception):
      pass
    self.FakeIOError = FakeIOError
    class FakeIllegalArgument(Exception):
      pass
    self.FakeIllegalArgument = FakeIllegalArgument
    class FakeAlreadyExists(Exception):
      pass
    self.FakeAlreadyExists = FakeAlreadyExists
    class FakeTException(Exception):
      pass
    self.FakeTException = FakeTException

    self.dummy_ttypesModule.expect('IOError', None, None, self.FakeIOError, None)
    self.dummy_ttypesModule.expect('IllegalArgument', None, None, self.FakeIllegalArgument, None)
    self.dummy_ttypesModule.expect('AlreadyExists', None, None, self.FakeAlreadyExists, None)
    self.dummy_thriftModule.expect('TException', None, None, self.FakeTException, None)

    self.dummy_transportObject = exp.DummyObjectWithExpectations('dummy_transportObject')
    self.dummy_protocolObject = exp.DummyObjectWithExpectations('dummy_protocolObject')
    self.dummy_clientObject = exp.DummyObjectWithExpectations('dummy_clientObject')

    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)

    self.dummy_transportObject.expect('open', (), {})

    self.conn = hbc.HBaseConnection('somehostname', 666,
                                    thrift=self.dummy_thriftModule,
                                    tsocket=self.dummy_tsocketModule,
                                    ttrans=self.dummy_transportModule,
                                    protocol=self.dummy_protocolModule,
                                    ttp=self.dummy_ttypesModule,
                                    client=self.dummy_clientClass,
                                    column=self.dummy_columnClass,
                                    mutation=self.dummy_mutationClass)
  def retry(self):
    self.dummy_transportObject.expect('close', (), {})
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('open', (), {})

  def retry2(self):
    self.dummy_transportObject.expect('close', (), {}, None, self.FakeTException('hidden bad exception'))
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('open', (), {})


def test_make_row_nice():
  conn = UsefulHbaseConnection().conn
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = {'a':ValueObject(1), 'b':ValueObject(2.1), 'c':ValueObject('C')}
  dummy_client_row_object.expect('columns', None, None, d)
  expectedDict = {'a':1, 'b':2.1, 'c':'C'}
  result = conn._make_row_nice(dummy_client_row_object)
  assert result == expectedDict, "expected %s but got %s" % (str(expectedDict), str(result))

def test_make_rows_nice():
  listOfRows = []
  expectedListOfRows = []
  for x in range(3):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  conn = UsefulHbaseConnection().conn
  result = conn._make_rows_nice(listOfRows)
  for a, b in zip(result, expectedListOfRows):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

def test_describe_table_1():
  usefulConn = UsefulHbaseConnection()
  conn = usefulConn.conn
  dummy_clientObject = usefulConn.dummy_clientObject
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  result = conn.describe_table('fred')
  assert result == 'fred', 'expected %s, but got %s' % ('fred', result)

def test_describe_table_2():
  """this test also exercises the retry"""
  usefulConn = UsefulHbaseConnection()
  usefulConn.retry()
  conn = usefulConn.conn
  dummy_clientObject = usefulConn.dummy_clientObject
  expectedException = usefulConn.FakeTException('bad news')
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, None, expectedException)
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  result = conn.describe_table('fred')
  assert result == 'fred', 'expected %s, but got %s' % ('fred', result)

def test_describe_table_3():
  """this test also exercises the retry with a second failure within the retry"""
  usefulConn = UsefulHbaseConnection()
  usefulConn.retry2()
  conn = usefulConn.conn
  dummy_clientObject = usefulConn.dummy_clientObject
  expectedException = usefulConn.FakeTException('bad news')
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, None, expectedException)
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  result = conn.describe_table('fred')
  assert result == 'fred', 'expected %s, but got %s' % ('fred', result)

def test_get_full_row():
  listOfRows = []
  expectedListOfRows = []
  for x in range(3):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  uhbc = UsefulHbaseConnection()
  conn = uhbc.conn
  dummy_clientObject = uhbc.dummy_clientObject
  dummy_clientObject.expect('getRow', ('fred', '22'), {}, listOfRows)
  result = conn.get_full_row('fred', '22')
  for a, b in zip(result, expectedListOfRows):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

class UsefulHBaseConnectionForCrashReports(object):
  def __init__(self):
    self.dummy_thriftModule = exp.DummyObjectWithExpectations('dummy_thriftModule')
    self.dummy_tsocketModule = exp.DummyObjectWithExpectations('dummy_tsocketModule')
    self.dummy_transportModule = exp.DummyObjectWithExpectations('dummy_transportModule')
    self.dummy_protocolModule = exp.DummyObjectWithExpectations('dummy_protocolModule')
    self.dummy_ttypesModule = exp.DummyObjectWithExpectations('dummy_ttypesModule')
    self.dummy_clientClass = exp.DummyObjectWithExpectations('dummy_clientClass')
    self.dummy_columnClass = exp.DummyObjectWithExpectations('dummy_columnClass')
    self.dummy_mutationClass = exp.DummyObjectWithExpectations('dummy_mutationClass')

    class FakeIOError(Exception):
      pass
    self.FakeIOError = FakeIOError
    class FakeIllegalArgument(Exception):
      pass
    self.FakeIllegalArgument = FakeIllegalArgument
    class FakeAlreadyExists(Exception):
      pass
    self.FakeAlreadyExists = FakeAlreadyExists
    class FakeTException(Exception):
      pass
    self.FakeTException = FakeTException

    self.dummy_ttypesModule.expect('IOError', None, None, self.FakeIOError, None)
    self.dummy_ttypesModule.expect('IllegalArgument', None, None, self.FakeIllegalArgument, None)
    self.dummy_ttypesModule.expect('AlreadyExists', None, None, self.FakeAlreadyExists, None)
    self.dummy_thriftModule.expect('TException', None, None, self.FakeTException, None)

    self.dummy_transportObject = exp.DummyObjectWithExpectations('dummy_transportObject')
    self.dummy_protocolObject = exp.DummyObjectWithExpectations('dummy_protocolObject')
    self.dummy_clientObject = exp.DummyObjectWithExpectations('dummy_clientObject')

    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)

    self.dummy_transportObject.expect('open', (), {})

    self.conn = hbc.HBaseConnectionForCrashReports('somehostname', 666,
                                                   thrift=self.dummy_thriftModule,
                                                   tsocket=self.dummy_tsocketModule,
                                                   ttrans=self.dummy_transportModule,
                                                   protocol=self.dummy_protocolModule,
                                                   ttp=self.dummy_ttypesModule,
                                                   client=self.dummy_clientClass,
                                                   column=self.dummy_columnClass,
                                                   mutation=self.dummy_mutationClass)

  def retry(self):
    self.dummy_transportObject.expect('close', (), {})
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('open', (), {})

def test_HBaseConnectionForCrashReports():
  hbcfcr = UsefulHBaseConnectionForCrashReports()

def test_ooid():
  ooid = 'abcdefghijklmnopqrstuvwxy20100102'
  expectedOoid = '100102abcdefghijklmnopqrstuvwxy20100102'
  result = hbc.HBaseConnectionForCrashReports.ooid(ooid)
  assert result == expectedOoid, 'expected %s, but got %s' % (expectedOoid, result)

def test_make_row_nice_2():
  """indirect test by invoking a base class method that exercises HBaseConnectionForCrashReports._make_row_nice"""
  listOfRows = []
  expectedListOfRows = []
  for x in range(3):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    ooid = '******%s100102' % (str(x) * 26)
    expectedOoid = '%s100102' % (str(x) * 26)
    dummy_client_row_object.expect('row', None, None, ooid)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, 'ooid':expectedOoid}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  result = conn._make_rows_nice(listOfRows)
  for a, b in zip(result, expectedListOfRows):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

def test_get_report_1():
  listOfRows = []
  expectedListOfRows = []
  for x in range(3):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    ooid = '******%s100102' % (str(x) * 26)
    expectedOoid = '%s100102' % (str(x) * 26)
    dummy_client_row_object.expect('row', None, None, ooid)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, 'ooid':expectedOoid}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102'), {}, listOfRows)
  result = conn.get_report('abcdefghijklmnopqrstuvwxyz100102')
  assert result == expectedListOfRows[0], 'expected %s, but got %s' % (str(result), str(expectedListOfRows[0]))

def test_get_report_1():
  """test of failure needing a retry"""
  listOfRows = []
  expectedListOfRows = []
  for x in range(3):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    ooid = '******%s100102' % (str(x) * 26)
    expectedOoid = '%s100102' % (str(x) * 26)
    dummy_client_row_object.expect('row', None, None, ooid)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, 'ooid':expectedOoid}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  expectedException = hbcfcr.FakeTException('bad news')
  dummy_clientObject.expect('getRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102'), {}, None, expectedException)
  hbcfcr.retry()
  dummy_clientObject.expect('getRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102'), {}, listOfRows)
  result = conn.get_report('abcdefghijklmnopqrstuvwxyz100102')
  assert result == expectedListOfRows[0], 'expected %s, but got %s' % (str(result), str(expectedListOfRows[0]))

def test_get_json():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  expectedJson = js.loads(jsonDataAsString)
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, jsonDataAsString)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'meta_data:json':dummyColumn})
  dummyClientRowObject.expect('row', None, None, '100102abcdefghijklmnopqrstuvwxyz100102')
  getRowWithColumnsReturnValue = [dummyClientRowObject]
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', ['meta_data:json']),
                            {}, getRowWithColumnsReturnValue)
  result = conn.get_json('abcdefghijklmnopqrstuvwxyz100102')
  assert result == expectedJson, 'expected %s, but got %s' % (str(expectedJson), str(result))

def test_get_dump():
  dumpDataAsString = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, dumpDataAsString)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'raw_data:dump':dummyColumn})
  getRowWithColumnsReturnValue = [dummyClientRowObject]
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', ['raw_data:dump']),
                            {}, getRowWithColumnsReturnValue)
  result = conn.get_dump('abcdefghijklmnopqrstuvwxyz100102')
  assert result == dumpDataAsString, 'expected %s, but got %s' % (dumpDataAsString, str(result))

def test_get_jsonz():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  expectedJson = js.loads(jsonDataAsString)
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, jsonDataAsString)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'processed_data:json':dummyColumn})
  dummyClientRowObject.expect('row', None, None, '100102abcdefghijklmnopqrstuvwxyz100102')
  getRowWithColumnsReturnValue = [dummyClientRowObject]
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', ['processed_data:json']),
                            {}, getRowWithColumnsReturnValue)
  result = conn.get_jsonz('abcdefghijklmnopqrstuvwxyz100102')
  assert result == expectedJson, 'expected %s, but got %s' % (str(expectedJson), str(result))

def test_scan_starting_with_1():
  listOfRows = []
  expectedListOfRows = []
  for x in range(5):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    ooid = '******%s100102' % (str(x) * 26)
    expectedOoid = '%s100102' % (str(x) * 26)
    dummy_client_row_object.expect('row', None, None, ooid)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, 'ooid':expectedOoid}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('scannerOpenWithPrefix', ('crash_reports', '******', ['meta_data:json']), {}, 0)
  dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[0]])
  dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[1]])
  dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[2]])
  dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[3]])
  dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[4]])
  dummy_clientObject.expect('scannerGet', (0,), {}, [])
  dummy_clientObject.expect('scannerClose', (0,), {})
  for i, x in enumerate(conn.scan_starting_with('******')):
    assert x == expectedListOfRows[i], '%s expected %s, but got %s' % (i, str(expectedListOfRows[i]), str(x))

def test_scan_starting_with_2():
  listOfRows = []
  expectedListOfRows = []
  for x in range(5):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    ooid = '******%s100102' % (str(x) * 26)
    expectedOoid = '%s100102' % (str(x) * 26)
    dummy_client_row_object.expect('row', None, None, ooid)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, 'ooid':expectedOoid}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('scannerOpenWithPrefix', ('crash_reports', '******', ['meta_data:json']), {}, 0)
  dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[0]])
  dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[1]])
  dummy_clientObject.expect('scannerClose', (0,), {})
  for i, x in enumerate(conn.scan_starting_with('******', 2)):
    assert x == expectedListOfRows[i], '%s expected %s, but got %s' % (i, str(expectedListOfRows[i]), str(x))

def test_put_json_dump():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  dumpDataAsString = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummyMutationClass = hbcfcr.dummy_mutationClass
  dummyMutationClass.expect('__call__', (), {'column': "meta_data:json", 'value':jsonDataAsString}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "raw_data:dump", 'value':dumpDataAsString}, 0)
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('mutateRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', [0,0]), {})
  conn.put_json_dump('abcdefghijklmnopqrstuvwxyz100102', jsonDataAsString, dumpDataAsString)

def test_put_json_dump_from_files():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  dumpDataAsString = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  fake_open = exp.DummyObjectWithExpectations('fake_open')
  fake_jsonFile = exp.DummyObjectWithExpectations('fake_jsonFile')
  fake_dumpFile = exp.DummyObjectWithExpectations('fake_dumpFile')
  fake_open.expect('__call__', ('/myJson.json', 'r'), {}, fake_jsonFile)
  fake_jsonFile.expect('read', (), {}, jsonDataAsString)
  fake_jsonFile.expect('close', (), {})
  fake_dumpFile.expect('read', (), {}, dumpDataAsString)
  fake_dumpFile.expect('close', (), {})
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummyMutationClass = hbcfcr.dummy_mutationClass
  dummyMutationClass.expect('__call__', (), {'column': "meta_data:json", 'value':jsonDataAsString}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "raw_data:dump", 'value':dumpDataAsString}, 0)
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('mutateRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', [0,0]), {})
  conn.put_json_dump('abcdefghijklmnopqrstuvwxyz100102', jsonDataAsString, dumpDataAsString)

def test_put_jsonz():
  jsonzDataAsString = '{"a": 1, "b": "hello"}'
  hbcfcr = UsefulHBaseConnectionForCrashReports()
  conn = hbcfcr.conn
  dummyMutationClass = hbcfcr.dummy_mutationClass
  dummyMutationClass.expect('__call__', (), {'column': "processed_data:json", 'value':jsonzDataAsString}, 0)
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('mutateRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', [0]), {})
  conn.put_jsonz('abcdefghijklmnopqrstuvwxyz100102', jsonzDataAsString)

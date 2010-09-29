import socorro.storage.hbaseClient as hbc
import socorro.lib.util as utl
import socorro.unittest.testlib.expectations as exp

import datetime as dt

try:
  import json as js
except ImportError:
  import simplejson as js

class ValueObject(object):
  def __init__(self, value):
    self.value = value

class FakeUrllib2Exception(Exception):
  pass

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

  dummy_transportObject.expect('setTimeout', (9000,), {})
  dummy_transportObject.expect('open', (), {})
  dummy_transportObject.expect('close', (), {})

  conn = hbc.HBaseConnection('somehostname', 666, 9000,
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

  dummy_transportObject.expect('setTimeout', (9000,), {})
  dummy_transportObject.expect('open', (), {}, None, FakeTException('bad news'))  #transport fails 1st time

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  dummy_transportObject.expect('setTimeout', (9000,), {})
  dummy_transportObject.expect('open', (), {}) #transport succeeds
  dummy_transportObject.expect('close', (), {})

  conn = hbc.HBaseConnection('somehostname', 666, 9000,
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

  dummy_transportObject.expect('setTimeout', (9000,), {})
  dummy_transportObject.expect('open', (), {}, None, FakeTException('bad news'))  #transport fails 1st time

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  theCauseException = FakeTException('bad news')
  theExpectedExceptionAsString = "the connection is not viable.  retries fail: No connection was made to HBase (2 tries): <class 'socorro.unittest.storage.testHbaseClient.FakeTException'>-bad news"
  dummy_transportObject.expect('setTimeout', (9000,), {})
  dummy_transportObject.expect('open', (), {}, None, theCauseException)  #transport fails 2nd time
  dummy_transportObject.expect('close', (), {})

  try:
    conn = hbc.HBaseConnection('somehostname', 666, 9000,
                               thrift=dummy_thriftModule,
                               tsocket=dummy_tsocketModule,
                               ttrans=dummy_transportModule,
                               protocol=dummy_protocolModule,
                               ttp=dummy_ttypesModule,
                               client=dummy_clientClass,
                               column=dummy_columnClass,
                               mutation=dummy_mutationClass)
  except Exception, x:
    assert str(x) == theExpectedExceptionAsString, "expected %s, but got %s" % (theExpectedExceptionAsString, str(x))
  else:
    assert False, "expected the exception %s, but no exception was raised" % theExpectedExceptionAsString

class HBaseConnectionWithPresetExpectationsFactory(object):
  def __init__(self, hbaseConnectionClass=hbc.HBaseConnection):
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
    self.dummy_transportObject.expect('setTimeout', (9000,), {})
    self.dummy_transportObject.expect('open', (), {})

    self.conn = hbaseConnectionClass('somehostname', 666, 9000,
                                    thrift=self.dummy_thriftModule,
                                    tsocket=self.dummy_tsocketModule,
                                    ttrans=self.dummy_transportModule,
                                    protocol=self.dummy_protocolModule,
                                    ttp=self.dummy_ttypesModule,
                                    client=self.dummy_clientClass,
                                    column=self.dummy_columnClass,
                                    mutation=self.dummy_mutationClass,
                                    logger=utl.StdoutLogger())
  def retry(self):
    self.dummy_transportObject.expect('close', (), {})
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('setTimeout', (9000,), {})
    self.dummy_transportObject.expect('open', (), {})

  def retry2(self):
    self.dummy_transportObject.expect('close', (), {}, None, self.FakeTException('hidden bad exception'))
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('setTimeout', (9000,), {})
    self.dummy_transportObject.expect('open', (), {})

  def retry3(self):
    self.dummy_transportObject.expect('close', (), {})
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('setTimeout', (9000,), {})
    self.dummy_transportObject.expect('open', (), {}, None, self.FakeTException("I won't connect!"))
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('setTimeout', (9000,), {})
    self.dummy_transportObject.expect('open', (), {}, None, self.FakeTException("I still won't connect!"))
    #failed twice in trying to reopen


def test_make_row_nice_1():
  conn = HBaseConnectionWithPresetExpectationsFactory().conn
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = {'a':ValueObject(1), 'b':ValueObject(2.1), 'c':ValueObject('C')}
  dummy_client_row_object.expect('columns', None, None, d)
  expectedDict = {'a':1, 'b':2.1, 'c':'C'}
  result = conn._make_row_nice(dummy_client_row_object)
  assert result == expectedDict, "expected %s but got %s" % (str(expectedDict), str(result))

def test_make_row_nice_2():
  conn = HBaseConnectionWithPresetExpectationsFactory().conn
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = {'a':ValueObject(1), 'b':ValueObject(2.1), 'c':'C'}
  dummy_client_row_object.expect('columns', None, None, d)
  expectedDict = {'a':1, 'b':2.1, 'c':'C'}
  try:
    result = conn._make_row_nice(dummy_client_row_object)
  except Exception, x:
    expected_exception_string = "'str' object has no attribute 'value'"
    actual_exception_string = str(x)
  assert expected_exception_string == actual_exception_string, "expected %s but got %s" % (expected_exception_string, actual_exception_string)

def test_make_rows_nice_1():
  listOfRows = []
  expectedListOfRows = []
  for x in range(3):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  conn = HBaseConnectionWithPresetExpectationsFactory().conn
  result = conn._make_rows_nice(listOfRows)
  for a, b in zip(result, expectedListOfRows):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

def test_describe_table_1():
  testHBaseConn = HBaseConnectionWithPresetExpectationsFactory()
  conn = testHBaseConn.conn
  dummy_clientObject = testHBaseConn.dummy_clientObject
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  result = conn.describe_table('fred')
  assert result == 'fred', 'expected %s, but got %s' % ('fred', result)

def test_describe_table_2():
  """this test also exercises the retry"""
  testHBaseConn = HBaseConnectionWithPresetExpectationsFactory()
  testHBaseConn.retry()
  conn = testHBaseConn.conn
  dummy_clientObject = testHBaseConn.dummy_clientObject
  unexpectedException = testHBaseConn.FakeTException('bad news')
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, None, unexpectedException)
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  result = conn.describe_table('fred')
  assert result == 'fred', 'expected %s, but got %s' % ('fred', result)

def test_describe_table_2b():
  """this test also exercises the retry but with a different internal exception"""
  testHBaseConn = HBaseConnectionWithPresetExpectationsFactory()
  testHBaseConn.retry()
  conn = testHBaseConn.conn
  dummy_clientObject = testHBaseConn.dummy_clientObject
  unexpectedException = ValueError('bad news')
  resultExceptionAsString = "bad news"
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, None, unexpectedException)
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  try:
    result = conn.describe_table('fred')
    assert False, 'an exception should have been raised, but was not'
  except Exception, x:
    assert resultExceptionAsString == str(x), 'expected %s, but got %s' % (str(resultException), str(x))

def test_describe_table_3():
  """this test exercises a connection failure within the retry"""
  testHBaseConn = HBaseConnectionWithPresetExpectationsFactory()
  testHBaseConn.retry3()
  conn = testHBaseConn.conn
  dummy_clientObject = testHBaseConn.dummy_clientObject
  unexpectedException = testHBaseConn.FakeTException('bad news')
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, None, unexpectedException)
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, None, unexpectedException)
  try:
    result = conn.describe_table('fred')
    assert False, 'an exception should have been raised, but was not'
  except Exception, x:
    expected_exception_string = "the connection is not viable.  retries fail: No connection was made to HBase (2 tries): <class 'socorro.unittest.storage.testHbaseClient.FakeTException'>-I still won't connect!"
    actual_exception_string = str(x)
    assert expected_exception_string == actual_exception_string, 'expected %s, but got %s' % (expected_exception_string, actual_exception_string)

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
  uhbc = HBaseConnectionWithPresetExpectationsFactory()
  conn = uhbc.conn
  dummy_clientObject = uhbc.dummy_clientObject
  dummy_clientObject.expect('getRow', ('fred', '22'), {}, listOfRows)
  result = conn.get_full_row('fred', '22')
  for a, b in zip(result, expectedListOfRows):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

def test_HBaseConnectionForCrashReports():
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)

def test_ooid_to_row_id():
  ooid = 'abcdefghijklmnopqrstuvwxy20100102'
  expectedOoid = 'a100102abcdefghijklmnopqrstuvwxy20100102'
  result = hbc.ooid_to_row_id(ooid)
  assert result == expectedOoid, 'expected %s, but got %s' % (expectedOoid, result)

def test_make_row_nice_3():
  """indirect test by invoking a base class method that exercises HBaseConnectionForCrashReports._make_row_nice"""
  listOfRows = []
  expectedListOfRows = []
  for x in range(3):
    dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    dummy_client_row_object.expect('columns', None, None, d)
    ooid = '%s100102' % (str(x) * 26)
    expectedOoid = '%s100102' % (str(x) * 26)
    dummy_client_row_object.expect('row', None, None, ooid)
    expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, '_rowkey':expectedOoid}
    listOfRows.append(dummy_client_row_object)
    expectedListOfRows.append(expectedDict)
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  conn = hbcfcr.conn
  result = conn._make_rows_nice(listOfRows)
  for a, b in zip(expectedListOfRows, result):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

def test_get_json_meta_as_string():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, jsonDataAsString)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'meta_data:json':dummyColumn})
  dummyClientRowObject.expect('row', None, None, 'a100102abcdefghijklmnopqrstuvwxyz100102')
  getRowWithColumnsReturnValue = [dummyClientRowObject]
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', 'a100102abcdefghijklmnopqrstuvwxyz100102', ['meta_data:json']),
                            {}, getRowWithColumnsReturnValue)
  result = conn.get_json_meta_as_string('abcdefghijklmnopqrstuvwxyz100102')
  assert result == jsonDataAsString, 'expected %s, but got %s' % (jsonDataAsString, str(result))

def test_get_json_1():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  expectedJson = js.loads(jsonDataAsString)
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, jsonDataAsString)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'meta_data:json':dummyColumn})
  dummyClientRowObject.expect('row', None, None, 'a100102abcdefghijklmnopqrstuvwxyz100102')
  getRowWithColumnsReturnValue = [dummyClientRowObject]
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', 'a100102abcdefghijklmnopqrstuvwxyz100102', ['meta_data:json']),
                            {}, getRowWithColumnsReturnValue)
  result = conn.get_json('abcdefghijklmnopqrstuvwxyz100102')
  assert result == expectedJson, 'expected %s, but got %s' % (str(expectedJson), str(result))

def test_get_json_2():
  """that ooid doesn't exist"""
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  expectedJson = js.loads(jsonDataAsString)
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, jsonDataAsString)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'meta_data:json':dummyColumn})
  dummyClientRowObject.expect('row', None, None, 'a100102abcdefghijklmnopqrstuvwxyz100102')
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', 'a100102abcdefghijklmnopqrstuvwxyz100102', ['meta_data:json']),
                            {}, [])
  try:
    result = conn.get_json('abcdefghijklmnopqrstuvwxyz100102')
  except Exception, x:
    expected_exception_as_string = 'OOID not found: abcdefghijklmnopqrstuvwxyz100102 - a100102abcdefghijklmnopqrstuvwxyz100102'
    actual_exception_as_string = str(x)
    assert expected_exception_as_string == actual_exception_as_string, 'expected %s, but got %s' % (expected_exception_as_string, actual_exception_as_string)

def test_get_dump():
  dumpBlob = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, dumpBlob)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'raw_data:dump':dummyColumn})
  getRowWithColumnsReturnValue = [dummyClientRowObject]
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', 'a100102abcdefghijklmnopqrstuvwxyz100102', ['raw_data:dump']),
                            {}, getRowWithColumnsReturnValue)
  result = conn.get_dump('abcdefghijklmnopqrstuvwxyz100102')
  assert result == dumpBlob, 'expected %s, but got %s' % (dumpBlob, str(result))

#def test_get_jsonz():
  #jsonDataAsString = '{"a": 1, "b": "hello"}'
  #expectedJson = js.loads(jsonDataAsString)
  #dummyColumn = exp.DummyObjectWithExpectations()
  #dummyColumn.expect('value', None, None, jsonDataAsString)
  #dummyClientRowObject = exp.DummyObjectWithExpectations()
  #dummyClientRowObject.expect('columns', None, None, {'processed_data:json':dummyColumn})
  #dummyClientRowObject.expect('row', None, None, '100102abcdefghijklmnopqrstuvwxyz100102')
  #getRowWithColumnsReturnValue = [dummyClientRowObject]
  #hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  #conn = hbcfcr.conn
  #dummy_clientObject = hbcfcr.dummy_clientObject
  #dummy_clientObject.expect('getRowWithColumns',
                            #('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', ['processed_data:json']),
                            #{}, getRowWithColumnsReturnValue)
  #result = conn.get_jsonz('abcdefghijklmnopqrstuvwxyz100102')
  #assert result == expectedJson, 'expected %s, but got %s' % (str(expectedJson), str(result))

#def test_scan_starting_with_1():
  #listOfRows = []
  #expectedListOfRows = []
  #for x in range(5):
    #dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    #d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    #dummy_client_row_object.expect('columns', None, None, d)
    #ooid = '******%s100102' % (str(x) * 26)
    #expectedOoid = '%s100102' % (str(x) * 26)
    #dummy_client_row_object.expect('row', None, None, ooid)
    #expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, 'ooid':expectedOoid}
    #listOfRows.append(dummy_client_row_object)
    #expectedListOfRows.append(expectedDict)
  #hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  #conn = hbcfcr.conn
  #dummy_clientObject = hbcfcr.dummy_clientObject
  #dummy_clientObject.expect('scannerOpenWithPrefix', ('crash_reports', '******', ['meta_data:json']), {}, 0)
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[0]])
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[1]])
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[2]])
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[3]])
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[4]])
  #dummy_clientObject.expect('scannerGet', (0,), {}, [])
  #dummy_clientObject.expect('scannerClose', (0,), {})
  #for i, x in enumerate(conn.scan_starting_with('******')):
    #assert x == expectedListOfRows[i], '%s expected %s, but got %s' % (i, str(expectedListOfRows[i]), str(x))

#def test_scan_starting_with_2():
  #listOfRows = []
  #expectedListOfRows = []
  #for x in range(5):
    #dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
    #d = {'a':ValueObject(x), 'b':ValueObject(x * 10.0), 'c':ValueObject('C'*x)}
    #dummy_client_row_object.expect('columns', None, None, d)
    #ooid = '******%s100102' % (str(x) * 26)
    #expectedOoid = '%s100102' % (str(x) * 26)
    #dummy_client_row_object.expect('row', None, None, ooid)
    #expectedDict = {'a':x, 'b':x * 10.0, 'c':'C'*x, 'ooid':expectedOoid}
    #listOfRows.append(dummy_client_row_object)
    #expectedListOfRows.append(expectedDict)
  #hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  #conn = hbcfcr.conn
  #dummy_clientObject = hbcfcr.dummy_clientObject
  #dummy_clientObject.expect('scannerOpenWithPrefix', ('crash_reports', '******', ['meta_data:json']), {}, 0)
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[0]])
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[1]])
  #dummy_clientObject.expect('scannerClose', (0,), {})
  #for i, x in enumerate(conn.scan_starting_with('******', 2)):
    #assert x == expectedListOfRows[i], '%s expected %s, but got %s' % (i, str(expectedListOfRows[i]), str(x))

def test_put_json_dump_1():
  jsonData = {"a": 1, "b": "hello", "submitted_timestamp":'2010-05-04T03:10:00'}
  jsonDataAsString = js.dumps(jsonData)
  dumpBlob = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(hbc.HBaseConnectionForCrashReports)
  conn = hbcfcr.conn
  dummyMutationClass = hbcfcr.dummy_mutationClass
  dummyMutationClass.expect('__call__', (), {'column': "flags:processed", 'value':"N"}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "meta_data:json", 'value':jsonDataAsString}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "timestamps:submitted", 'value':'2010-05-04T03:10:00'}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "ids:ooid", 'value':'abcdefghijklmnopqrstuvwxyz100102'}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "raw_data:dump", 'value':dumpBlob}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "flags:legacy_processing", 'value':"Y"}, 0)
  dummy_clientObject = hbcfcr.dummy_clientObject
  # unit test marker 233
  dummy_clientObject.expect('mutateRow', ('crash_reports', 'a100102abcdefghijklmnopqrstuvwxyz100102', [0,0,0,0,0,0]), {})
  # setup for put_crash_report_indices
  dummyMutationClass.expect('__call__', (), {'column': "ids:ooid", 'value':'abcdefghijklmnopqrstuvwxyz100102'}, 0)
  dummy_clientObject.expect('mutateRow', ('crash_reports_index_submitted_time', 'a2010-05-04T03:10:00abcdefghijklmnopqrstuvwxyz100102', [0]), {})
  dummyMutationClass.expect('__call__', (), {'column': "ids:ooid", 'value':'abcdefghijklmnopqrstuvwxyz100102'}, 0)
  dummy_clientObject.expect('mutateRow', ('crash_reports_index_unprocessed_flag', 'a2010-05-04T03:10:00abcdefghijklmnopqrstuvwxyz100102', [0]), {})
  dummyMutationClass.expect('__call__', (), {'column': "ids:ooid", 'value':'abcdefghijklmnopqrstuvwxyz100102'}, 0)
  dummy_clientObject.expect('mutateRow', ('crash_reports_index_legacy_unprocessed_flag', 'a2010-05-04T03:10:00abcdefghijklmnopqrstuvwxyz100102', [0]), {})
  dummyMutationClass.expect('__call__', (), {'column': "ids:ooid", 'value':'abcdefghijklmnopqrstuvwxyz100102'}, 0)
  dummy_clientObject.expect('mutateRow', ('crash_reports_index_legacy_submitted_time', 'a2010-05-04T03:10:00abcdefghijklmnopqrstuvwxyz100102', [0]), {})
  # setup for atomic increments
  dummy_clientObject.expect('atomicIncrement', ('metrics','crash_report_queues','counters:inserts_unprocessed',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','crash_report_queues','counters:inserts_unprocessed_legacy',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05-04T03:10','counters:submitted_crash_reports',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05-04T03:10','counters:submitted_crash_reports_legacy_throttle_0',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05-04T03','counters:submitted_crash_reports',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05-04T03','counters:submitted_crash_reports_legacy_throttle_0',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05-04','counters:submitted_crash_reports',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05-04','counters:submitted_crash_reports_legacy_throttle_0',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05','counters:submitted_crash_reports',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010-05','counters:submitted_crash_reports_legacy_throttle_0',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010','counters:submitted_crash_reports',1), {})
  dummy_clientObject.expect('atomicIncrement', ('metrics','2010','counters:submitted_crash_reports_legacy_throttle_0',1), {})

  conn.put_json_dump('abcdefghijklmnopqrstuvwxyz100102', jsonData, dumpBlob)

class SubmitToProcessorTestingHBaseConnection(hbc.HBaseConnectionForCrashReports):
  def __init__(self,
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
               logger=utl.SilentFakeLogger()):
    super(SubmitToProcessorTestingHBaseConnection,self).__init__(host,port,timeout,thrift,tsocket,ttrans,
                                                        protocol,ttp,client,column,
                                                        mutation,logger)
    self.merge_scan_with_prefix_return_sequence = []
    self.update_unprocessed_queue_with_processor_state_expectations = \
           exp.DummyObjectWithExpectations('update_unprocessed_queue_with_processor_state_expectations')
  def merge_scan_with_prefix(self, dummy1, dummy2, dummy3):
    for x in self.merge_scan_with_prefix_return_sequence:
      yield x
  def update_unprocessed_queue_with_processor_state(self,
                                                    rowkey,
                                                    now,
                                                    processor_name,
                                                    legacy_flag):
    self.update_unprocessed_queue_with_processor_state_expectations(rowkey,
                                                    now,
                                                    processor_name,
                                                    legacy_flag)


def test_submit_to_processor_0():
  """test_submit_to_processor_0 - nothing to do"""
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(SubmitToProcessorTestingHBaseConnection)
  conn = hbcfcr.conn
  conn.submit_to_processor('fred,ethel,wilma')

def test_submit_to_processor_1():
  """test_submit_to_processor_1 - one half deleted entry"""
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(SubmitToProcessorTestingHBaseConnection)
  conn = hbcfcr.conn
  conn.merge_scan_with_prefix_return_sequence = [{'_rowkey':'aaa'}]
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('deleteAllRow',
                            ('crash_reports_index_legacy_unprocessed_flag',
                             'aaa'),
                            {},
                            None,
                            None)
  conn.submit_to_processor('fred,ethel,wilma')

def test_submit_to_processor_2():
  """test_submit_to_processor_2 - four don't submit, one do submit"""
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(SubmitToProcessorTestingHBaseConnection)
  dummy_clientObject = hbcfcr.dummy_clientObject
  conn = hbcfcr.conn
  conn.merge_scan_with_prefix_return_sequence = [{'_rowkey':'aaa',
                                                  'ids:ooid':'19f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-10-01 00:01:00',
                                                 },
                                                 {'_rowkey':'bbb',
                                                  'ids:ooid':'29f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-10-01 00:00:59',
                                                 },
                                                 {'_rowkey':'ccc',
                                                  'ids:ooid':'39f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-10-01 00:00:01',
                                                 },
                                                 {'_rowkey':'ddd',
                                                  'ids:ooid':'49f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-10-01 00:00:00',
                                                 },
                                                 {'_rowkey':'eee',
                                                  'ids:ooid':'59f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-09-30 23:59:59',
                                                 },
                                                ]
  nowFunction = exp.DummyObjectWithExpectations('nowFunction')
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = { 'flags:processed': ValueObject('N'),
        'meta_data:json': ValueObject('"json stuff"'),
        'raw_data:dump': ValueObject('binary dump'),
      }
  dummy_client_row_object.expect('columns', None, None, d)
  dummy_client_row_object.expect('row', None, None, 'eee')
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports',
                             '510100159f56181-6fff-4f27-a263-548242101001',
                             ['meta_data:json', 'raw_data:dump', 'flags:processed']),
                            {},
                            [dummy_client_row_object],
                            None
                           )
  post_result = exp.DummyObjectWithExpectations('post_result')
  post_result.expect('read', (), {}, 'fred', None)
  urllib2Module = exp.DummyObjectWithExpectations('urllib2Module')
  urllib2Module.expect('urlopen',
                       ("http://fred:8881/201006/process/ooid",
                        'ooid=59f56181-6fff-4f27-a263-548242101001'),
                       {},
                       post_result,
                       None)
  conn.update_unprocessed_queue_with_processor_state_expectations.expect('__call__',
                                                                         ('eee',
                                                                          '2010-10-01T00:01:00',
                                                                          'fred',
                                                                          0),
                                                                         {},
                                                                         None
                                                                        )
  urllib2Module.expect('URLError', None, None, FakeUrllib2Exception)
  conn.submit_to_processor('fred,ethel,wilma',
                           resubmitTimeDeltaThreshold=dt.timedelta(seconds=60),
                           urllib2Module=urllib2Module,
                           nowFunction=nowFunction)

def test_submit_to_processor_3():
  """test_submit_to_processor_3 - one do submit, but ooid not found, should delete"""
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(SubmitToProcessorTestingHBaseConnection)
  dummy_clientObject = hbcfcr.dummy_clientObject
  conn = hbcfcr.conn
  conn.merge_scan_with_prefix_return_sequence = [{'_rowkey':'eee',
                                                  'ids:ooid':'59f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-09-30 23:59:59',
                                                 },
                                                ]
  nowFunction = exp.DummyObjectWithExpectations('nowFunction')
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports',
                             '510100159f56181-6fff-4f27-a263-548242101001',
                             ['meta_data:json', 'raw_data:dump', 'flags:processed']),
                            {},
                            [],
                            None
                           )
  dummy_clientObject.expect('deleteAllRow',
                            ('crash_reports_index_legacy_unprocessed_flag',
                             'eee'),
                            {},
                            None,
                            None
                           )
  urllib2Module = exp.DummyObjectWithExpectations('urllib2Module')
  urllib2Module.expect('URLError', None, None, FakeUrllib2Exception)
  conn.submit_to_processor('fred,ethel,wilma',
                           resubmitTimeDeltaThreshold=dt.timedelta(seconds=60),
                           urllib2Module=urllib2Module,
                           nowFunction=nowFunction)

def test_submit_to_processor_4():
  """test_submit_to_processor_4 - one do submit, but previously processed, should delete"""
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(SubmitToProcessorTestingHBaseConnection)
  dummy_clientObject = hbcfcr.dummy_clientObject
  conn = hbcfcr.conn
  conn.merge_scan_with_prefix_return_sequence = [{'_rowkey':'eee',
                                                  'ids:ooid':'59f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-09-30 23:59:59',
                                                 },
                                                ]
  nowFunction = exp.DummyObjectWithExpectations('nowFunction')
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = { 'flags:processed': ValueObject('Y'),
        'meta_data:json': ValueObject('"json stuff"'),
        'raw_data:dump': ValueObject('binary dump'),
      }
  dummy_client_row_object.expect('columns', None, None, d)
  dummy_client_row_object.expect('row', None, None, 'eee')
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports',
                             '510100159f56181-6fff-4f27-a263-548242101001',
                             ['meta_data:json', 'raw_data:dump', 'flags:processed']),
                            {},
                            [dummy_client_row_object],
                            None
                           )
  dummy_clientObject.expect('deleteAllRow',
                            ('crash_reports_index_legacy_unprocessed_flag',
                             'eee'),
                            {},
                            None,
                            None
                           )
  urllib2Module = exp.DummyObjectWithExpectations('urllib2Module')
  urllib2Module.expect('URLError', None, None, FakeUrllib2Exception)
  conn.submit_to_processor('fred,ethel,wilma',
                           resubmitTimeDeltaThreshold=dt.timedelta(seconds=60),
                           urllib2Module=urllib2Module,
                           nowFunction=nowFunction)

def test_submit_to_processor_5():
  """test_submit_to_processor_5 - one do submit, but json metadata empty, should delete"""
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(SubmitToProcessorTestingHBaseConnection)
  dummy_clientObject = hbcfcr.dummy_clientObject
  conn = hbcfcr.conn
  conn.merge_scan_with_prefix_return_sequence = [{'_rowkey':'eee',
                                                  'ids:ooid':'59f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-09-30 23:59:59',
                                                 },
                                                ]
  nowFunction = exp.DummyObjectWithExpectations('nowFunction')
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = { 'flags:processed': ValueObject('Y'),
        'meta_data:json': ValueObject(''),
        'raw_data:dump': ValueObject('binary dump'),
      }
  dummy_client_row_object.expect('columns', None, None, d)
  dummy_client_row_object.expect('row', None, None, 'eee')
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports',
                             '510100159f56181-6fff-4f27-a263-548242101001',
                             ['meta_data:json', 'raw_data:dump', 'flags:processed']),
                            {},
                            [dummy_client_row_object],
                            None
                           )
  dummy_clientObject.expect('deleteAllRow',
                            ('crash_reports_index_legacy_unprocessed_flag',
                             'eee'),
                            {},
                            None,
                            None
                           )
  urllib2Module = exp.DummyObjectWithExpectations('urllib2Module')
  urllib2Module.expect('URLError', None, None, FakeUrllib2Exception)
  conn.submit_to_processor('fred,ethel,wilma',
                           resubmitTimeDeltaThreshold=dt.timedelta(seconds=60),
                           urllib2Module=urllib2Module,
                           nowFunction=nowFunction)


def test_submit_to_processor_6():
  """test_submit_to_processor_6 - one do submit, but dump empty, should delete"""
  hbcfcr = HBaseConnectionWithPresetExpectationsFactory(SubmitToProcessorTestingHBaseConnection)
  dummy_clientObject = hbcfcr.dummy_clientObject
  conn = hbcfcr.conn
  conn.merge_scan_with_prefix_return_sequence = [{'_rowkey':'eee',
                                                  'ids:ooid':'59f56181-6fff-4f27-a263-548242101001',
                                                  'processor_state:post_timestamp': '2010-09-30 23:59:59',
                                                 },
                                                ]
  nowFunction = exp.DummyObjectWithExpectations('nowFunction')
  nowFunction.expect('__call__', (), {}, dt.datetime(2010,10,1,0,1,0), None)
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = { 'flags:processed': ValueObject('Y'),
        'meta_data:json': ValueObject('"json stuff"'),
        'raw_data:dump': ValueObject(''),
      }
  dummy_client_row_object.expect('columns', None, None, d)
  dummy_client_row_object.expect('row', None, None, 'eee')
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports',
                             '510100159f56181-6fff-4f27-a263-548242101001',
                             ['meta_data:json', 'raw_data:dump', 'flags:processed']),
                            {},
                            [dummy_client_row_object],
                            None
                           )
  dummy_clientObject.expect('deleteAllRow',
                            ('crash_reports_index_legacy_unprocessed_flag',
                             'eee'),
                            {},
                            None,
                            None
                           )
  urllib2Module = exp.DummyObjectWithExpectations('urllib2Module')
  urllib2Module.expect('URLError', None, None, FakeUrllib2Exception)
  conn.submit_to_processor('fred,ethel,wilma',
                           resubmitTimeDeltaThreshold=dt.timedelta(seconds=60),
                           urllib2Module=urllib2Module,
                           nowFunction=nowFunction)


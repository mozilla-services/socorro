import socorro.hbase.hbaseClient as hbc
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

  dummy_transportObject.expect('setTimeout', (1000,), {})
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

  dummy_transportObject.expect('setTimeout', (1000,), {})
  dummy_transportObject.expect('open', (), {}, None, FakeTException('bad news'))  #transport fails 1st time

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  dummy_transportObject.expect('setTimeout', (1000,), {})
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

  dummy_transportObject.expect('setTimeout', (1000,), {})
  dummy_transportObject.expect('open', (), {}, None, FakeTException('bad news'))  #transport fails 1st time

  dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, dummy_transportObject)
  dummy_transportModule.expect('TBufferedTransport', (dummy_transportObject,), {}, dummy_transportObject)
  dummy_protocolModule.expect('TBinaryProtocol', (dummy_transportObject,), {}, dummy_protocolObject)
  dummy_clientClass.expect('__call__', (dummy_protocolObject,), {}, dummy_clientObject)

  theCauseException = FakeTException('bad news')
  theExpectedException = hbc.NoConnectionException(str(theCauseException), 2)
  dummy_transportObject.expect('setTimeout', (1000,), {})
  dummy_transportObject.expect('open', (), {}, None, theCauseException)  #transport fails 2nd time
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
    assert str(x) == str(theExpectedException), "expected %s, but got %s" % (str(theExpectedException), str(x))
  else:
    assert False, "expected the exception %s, but no exception was raised" % str(theExpectedException)

class HBaseConnectionWithPresetExpectations(object):
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
    self.dummy_transportObject.expect('setTimeout', (1000,), {})
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
    self.dummy_transportObject.expect('setTimeout', (1000,), {})
    self.dummy_transportObject.expect('open', (), {})

  def retry2(self):
    self.dummy_transportObject.expect('close', (), {}, None, self.FakeTException('hidden bad exception'))
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('setTimeout', (1000,), {})
    self.dummy_transportObject.expect('open', (), {})

  def retry3(self):
    self.dummy_transportObject.expect('close', (), {})
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('setTimeout', (1000,), {})
    self.dummy_transportObject.expect('open', (), {}, None, self.FakeTException("I won't connect!"))
    self.dummy_tsocketModule.expect('TSocket', ('somehostname', 666), {}, self.dummy_transportObject)
    self.dummy_transportModule.expect('TBufferedTransport', (self.dummy_transportObject,), {}, self.dummy_transportObject)
    self.dummy_protocolModule.expect('TBinaryProtocol', (self.dummy_transportObject,), {}, self.dummy_protocolObject)
    self.dummy_clientClass.expect('__call__', (self.dummy_protocolObject,), {}, self.dummy_clientObject)
    self.dummy_transportObject.expect('setTimeout', (1000,), {})
    self.dummy_transportObject.expect('open', (), {}, None, self.FakeTException("I still won't connect!"))
    #failed twice in trying to reopen


def test_make_row_nice_1():
  conn = HBaseConnectionWithPresetExpectations().conn
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = {'a':ValueObject(1), 'b':ValueObject(2.1), 'c':ValueObject('C')}
  dummy_client_row_object.expect('columns', None, None, d)
  expectedDict = {'a':1, 'b':2.1, 'c':'C'}
  result = conn._make_row_nice(dummy_client_row_object)
  assert result == expectedDict, "expected %s but got %s" % (str(expectedDict), str(result))

def test_make_row_nice_2():
  conn = HBaseConnectionWithPresetExpectations().conn
  dummy_client_row_object = exp.DummyObjectWithExpectations('dummy_client_row_object')
  d = {'a':ValueObject(1), 'b':ValueObject(2.1), 'c':'C'}
  dummy_client_row_object.expect('columns', None, None, d)
  expectedDict = {'a':1, 'b':2.1, 'c':'C'}
  try:
    result = conn._make_row_nice(dummy_client_row_object)
  except Exception, x:
    expected_exception_string = "An internal exception was not handled: <type 'exceptions.AttributeError'>-'str' object has no attribute 'value'"
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
  conn = HBaseConnectionWithPresetExpectations().conn
  result = conn._make_rows_nice(listOfRows)
  for a, b in zip(result, expectedListOfRows):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

def test_describe_table_1():
  testHBaseConn = HBaseConnectionWithPresetExpectations()
  conn = testHBaseConn.conn
  dummy_clientObject = testHBaseConn.dummy_clientObject
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  result = conn.describe_table('fred')
  assert result == 'fred', 'expected %s, but got %s' % ('fred', result)

def test_describe_table_2():
  """this test also exercises the retry"""
  testHBaseConn = HBaseConnectionWithPresetExpectations()
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
  testHBaseConn = HBaseConnectionWithPresetExpectations()
  testHBaseConn.retry()
  conn = testHBaseConn.conn
  dummy_clientObject = testHBaseConn.dummy_clientObject
  unexpectedException = ValueError('bad news')
  resultException = hbc.UnhandledInternalException(ValueError, unexpectedException)
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, None, unexpectedException)
  dummy_clientObject.expect('getColumnDescriptors', ('fred',), {}, 'fred')
  try:
    result = conn.describe_table('fred')
    assert False, 'an exception should have been raised, but was not'
  except Exception, x:
    assert str(resultException) == str(x), 'expected %s, but got %s' % (str(resultException), str(x))

def test_describe_table_3():
  """this test exercises a connection failure within the retry"""
  testHBaseConn = HBaseConnectionWithPresetExpectations()
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
    expected_exception_string = """No connection was made to HBase (2 tries): <class 'socorro.unittest.hbase.testHbaseClient.FakeTException'>-I still won't connect!"""
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
  uhbc = HBaseConnectionWithPresetExpectations()
  conn = uhbc.conn
  dummy_clientObject = uhbc.dummy_clientObject
  dummy_clientObject.expect('getRow', ('fred', '22'), {}, listOfRows)
  result = conn.get_full_row('fred', '22')
  for a, b in zip(result, expectedListOfRows):
    assert a == b, 'expected %s, but got %s' % (str(a), str(b))

class HBaseConnectionForCrashReportsWithPresetExpectations(object):
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

    self.dummy_transportObject.expect('setTimeout', (1000,), {})
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
    self.dummy_transportObject.expect('setTimeout', (1000,), {})
    self.dummy_transportObject.expect('open', (), {})

def test_HBaseConnectionForCrashReports():
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()

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
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
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
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
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
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
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
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
  conn = hbcfcr.conn
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('getRowWithColumns',
                            ('crash_reports', 'a100102abcdefghijklmnopqrstuvwxyz100102', ['meta_data:json']),
                            {}, [])
  try:
    result = conn.get_json('abcdefghijklmnopqrstuvwxyz100102')
  except Exception, x:
    expected_exception_as_string = 'OOID not found: abcdefghijklmnopqrstuvwxyz100102'
    actual_exception_as_string = str(x)
    assert expected_exception_as_string == actual_exception_as_string, 'expected %s, but got %s' % (expected_exception_as_string, actual_exception_as_string)

def test_get_dump():
  dumpBlob = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  dummyColumn = exp.DummyObjectWithExpectations()
  dummyColumn.expect('value', None, None, dumpBlob)
  dummyClientRowObject = exp.DummyObjectWithExpectations()
  dummyClientRowObject.expect('columns', None, None, {'raw_data:dump':dummyColumn})
  getRowWithColumnsReturnValue = [dummyClientRowObject]
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
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
  #hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
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
  #hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
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
  #hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
  #conn = hbcfcr.conn
  #dummy_clientObject = hbcfcr.dummy_clientObject
  #dummy_clientObject.expect('scannerOpenWithPrefix', ('crash_reports', '******', ['meta_data:json']), {}, 0)
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[0]])
  #dummy_clientObject.expect('scannerGet', (0,), {}, [listOfRows[1]])
  #dummy_clientObject.expect('scannerClose', (0,), {})
  #for i, x in enumerate(conn.scan_starting_with('******', 2)):
    #assert x == expectedListOfRows[i], '%s expected %s, but got %s' % (i, str(expectedListOfRows[i]), str(x))

def test_put_json_dump_1():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  dumpBlob = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
  conn = hbcfcr.conn
  dummyMutationClass = hbcfcr.dummy_mutationClass
  dummyMutationClass.expect('__call__', (), {'column': "flags:unprocessed", 'value':"Y"}, 0)
  #dummyMutationClass.expect('__call__', (), {'column': "flags:legacyToBeProcessed", 'value':"N"}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "meta_data:json", 'value':jsonDataAsString}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "raw_data:dump", 'value':dumpBlob}, 0)
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('mutateRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', [0,0,0]), {})
  conn.put_json_dump('abcdefghijklmnopqrstuvwxyz100102', jsonDataAsString, dumpBlob)

def test_put_json_dump_2():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  dumpBlob = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
  conn = hbcfcr.conn
  dummyMutationClass = hbcfcr.dummy_mutationClass
  dummyMutationClass.expect('__call__', (), {'column': "flags:unprocessed", 'value':"Y"}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "flags:legacyToBeProcessed", 'value':"Y"}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "meta_data:json", 'value':jsonDataAsString}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "raw_data:dump", 'value':dumpBlob}, 0)
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('mutateRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', [0,0,0,0]), {})
  conn.put_json_dump('abcdefghijklmnopqrstuvwxyz100102', jsonDataAsString, dumpBlob, True)

def test_put_json_dump_from_files():
  jsonDataAsString = '{"a": 1, "b": "hello"}'
  dumpBlob = 'abcdefghijklmnopqrstuvwxyz01234567890!@#$%^&*()_-=+'
  fake_open = exp.DummyObjectWithExpectations('fake_open')
  fake_jsonFile = exp.DummyObjectWithExpectations('fake_jsonFile')
  fake_dumpFile = exp.DummyObjectWithExpectations('fake_dumpFile')
  fake_open.expect('__call__', ('/myJson.json', 'r'), {}, fake_jsonFile)
  fake_jsonFile.expect('read', (), {}, jsonDataAsString)
  fake_jsonFile.expect('close', (), {})
  fake_dumpFile.expect('read', (), {}, dumpBlob)
  fake_dumpFile.expect('close', (), {})
  hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
  conn = hbcfcr.conn
  dummyMutationClass = hbcfcr.dummy_mutationClass
  dummyMutationClass.expect('__call__', (), {'column': "flags:unprocessed", 'value':"Y"}, 0)
  #dummyMutationClass.expect('__call__', (), {'column': "flags:legacyToBeProcessed", 'value':"N"}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "meta_data:json", 'value':jsonDataAsString}, 0)
  dummyMutationClass.expect('__call__', (), {'column': "raw_data:dump", 'value':dumpBlob}, 0)
  dummy_clientObject = hbcfcr.dummy_clientObject
  dummy_clientObject.expect('mutateRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', [0,0,0]), {})
  conn.put_json_dump('abcdefghijklmnopqrstuvwxyz100102', jsonDataAsString, dumpBlob)

#def test_put_jsonz():
  #jsonzDataAsString = '{"a": 1, "b": "hello"}'
  #hbcfcr = HBaseConnectionForCrashReportsWithPresetExpectations()
  #conn = hbcfcr.conn
  #dummyMutationClass = hbcfcr.dummy_mutationClass
  #dummyMutationClass.expect('__call__', (), {'column': "processed_data:json", 'value':jsonzDataAsString}, 0)
  #dummy_clientObject = hbcfcr.dummy_clientObject
  #dummy_clientObject.expect('mutateRow', ('crash_reports', '100102abcdefghijklmnopqrstuvwxyz100102', [0]), {})
  #conn.put_jsonz('abcdefghijklmnopqrstuvwxyz100102', jsonzDataAsString)

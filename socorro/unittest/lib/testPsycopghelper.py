import unittest
import socorro.lib.psycopghelper as ppghelper
import psycopg2
import psycopg2.extensions
import datetime as DT
import logging
import threading

from socorro.unittest.testlib.loggerForTest import TestingLogger
import socorro.unittest.testlib.util as tutil
from createDBforTest import *

import socorro.lib.ConfigurationManager as cm
import dbTestconfig as testConfig
config = cm.newConfiguration(configurationModule = testConfig, applicationName='Testing Psycopghelper')
def setup_module():
  tutil.nosePrintModule(__file__)

"""
Assume that psycopg2 works, then all we need to do is assure ourselves
that our simplistic wrap around a returned array is correct
"""

class TestMultiCursor(psycopg2.extensions.cursor):
  def __init__(self,numCols = 4, numRows=2, **kwargs):
    self.result = []
    for i in range(numRows):
      aRow = []
      for j in range(numCols):
        aRow.append('Row %d, Column %d' %(i,j))
      self.result.append(aRow)
    self.next = self.__next()
  def execute(self,sql, args=None):
    pass
  def fetchall(self):
    return self.result
  def __next(self):
    index = 0
    while True:
      try:
        yield self.result[index]
        index += 1
      except:
        yield None
  def fetchone(self):
    try:
      return self.next.next()
    except:
      return None

class TestEmptyCursor(psycopg2.extensions.cursor):
  def __init__(self):
    self.result = []
  def execute(self,sql, args=None):
    pass
  def fetchall(self):
    return self.result

class TestSingleCursor(psycopg2.extensions.cursor):
  def __init__(self):
    self.result = [['Row 0, Column 0']]
  def execute(self,sql, args=None):
    pass
  def fetchall(self):
    return self.result


class TestPsycopghelper(unittest.TestCase):
  def setUp(self):
    self.logger = TestingLogger()
    self.connectionData0 = (config.databaseHost,config.databaseName,config.databaseUserName,config.databasePassword)
    self.connectionDataL = (config.databaseHost,config.databaseName,config.databaseUserName,config.databasePassword,self.logger)
    self.dsn = "host=%s dbname=%s user=%s password=%s" % self.connectionData0
    self.connection = psycopg2.connect(self.dsn)
    createDB(self.connection)

  def tearDown(self):
    dropDB(self.connection)
    self.connection.close()

  def testExecute(self):
    aCursor = TestMultiCursor(numCols=1,numRows=3)
    f = ppghelper.execute(aCursor,"")
    vals = [x for x in f]
    assert 3 == len(vals)
    assert 'Row 0, Column 0' == vals[0][0]
    assert 'Row 2, Column 0' == vals[-1][0]
    aCursor = TestMultiCursor(numCols=1,numRows=1)

  def testSingleValueEmpty(self):
    try:
      cur = TestEmptyCursor()
      ppghelper.singleValueSql(cur,"")
      assert False, "must raise SQLDidNotReturnSingleValue"
    except ppghelper.SQLDidNotReturnSingleValue,e:
      pass

  def testSingleValueSingle(self):
    try:
      cur = TestSingleCursor()
      assert "Row 0, Column 0" == ppghelper.singleValueSql(cur,"")
    except Exception, e:
      assert False, "must not raise an exception for this %s" %e

  def testSingleValueMulti(self):
    try:
      cur = TestMultiCursor(numRows=5)
      assert "Row 0, Column 0" == ppghelper.singleValueSql(cur,"")
    except Exception, e:
      assert False, "must not raise an exception for this "+e

  def testSingleRowEmpty(self):
    try:
      cur = TestEmptyCursor()
      ppghelper.singleRowSql(cur,"")
      assert False, "must raise SQLDidNotReturnSingleRow"
    except ppghelper.SQLDidNotReturnSingleRow,e:
      pass

  def testSingleRowSingle(self):
    try:
      cur = TestSingleCursor()
      assert ["Row 0, Column 0"] == ppghelper.singleRowSql(cur,"")
    except Exception, e:
      assert False, "must not raise this exception"

  def testSingleRowMulti(self):
    try:
      cur = TestMultiCursor(numRows=5, numCols=1)
      assert ["Row 0, Column 0"] == ppghelper.singleRowSql(cur,"")
    except Exception, e:
      assert False, "must not raise this exception"

  def testConnectionPoolConstructor(self):
    # just test some variations on constructor calls
    logger = self.logger
    logger.clear()
    try:
      cp = ppghelper.DatabaseConnectionPool()
      assert False, 'expected a raised TypeError, not to get here'
    except TypeError,x:
      pass
    except Exception,x:
      assert False, 'expected a TypeError, not %s: %s'%(type(x),x)
    try:
      cp = ppghelper.DatabaseConnectionPool(*self.connectionData0)
    except Exception,x:
      assert False, 'expected the non-logger constructor to succeed, got %s: %s'%(type(x),x)
    try:
      cp = ppghelper.DatabaseConnectionPool(*self.connectionDataL)
    except Exception,x:
      assert False, 'expected the with-logger constructor to succeed, got %s: %s'%(type(x),x)

  def testConnectionPoolConnectToDatabase(self):
    logger = self.logger
    logger.clear()
    cp = ppghelper.DatabaseConnectionPool(config.databaseHost,config.databaseName,config.databaseUserName,config.databasePassword,logger)
    logger.clear()
    try:
      connection,cursor = cp.connectToDatabase()
      assert connection
      assert cursor
    except Exception,x:
      assert False, 'expected nothing, got %s: %s'%(type(x),x)
    assert logger.levels[0] == logging.INFO
    assert logger.buffer[0] == '%s - connecting to database' %threading.currentThread().getName()

  def testConnectionPoolConnectionCursorPairNoTest(self):
    logger = self.logger
    logger.clear()
    cp = ppghelper.DatabaseConnectionPool(config.databaseHost,config.databaseName,config.databaseUserName,config.databasePassword,logger)
    connection0 = cursor0 = None
    try:
      connection0,cursor0 = cp.connectionCursorPairNoTest()
      assert connection0
      assert cursor0
    except Exception,x:
      assert False, 'expected nothing, got %s: %s'%(type(x),x)
    connection1,cursor1 = cp.connectionCursorPairNoTest()
    assert 1 == len(logger.buffer) # only logged one actual connection attempt
    assert connection0 == connection1
    assert cursor0 == cursor1

  def testConnectionPoolConnectionCursorPair(self):
    logger = self.logger
    logger.clear()
    cp = ppghelper.DatabaseConnectionPool(config.databaseHost,config.databaseName,config.databaseUserName,config.databasePassword,logger)
    connection0 = cursor0 = None
    try:
      connection0,cursor0 = cp.connectionCursorPair()
      assert connection0
      assert cursor0
    except Exception,x:
      assert False, 'expected nothing, got %s: %s'%(type(x),x)
    connection1,cursor1 = cp.connectionCursorPair()
    assert 1 == len(logger.buffer) # only logged one actual connection attempt
    assert connection0 == connection1
    assert cursor0 == cursor1

    logger.clear()
    cp = ppghelper.DatabaseConnectionPool(config.databaseHost,config.databaseName,config.databaseUserName,config.databasePassword,logger)
    connection0 = cursor0 = None
    try:
      connection0,cursor0 = cp.connectionCursorPair()
    except Exception,x:
      assert False, 'Expected OperationalError above, got %s: %s' %(type(x),x)

  def testConnectionPoolCleanup(self):
    logger = self.logger
    logger.clear()
    cp = ppghelper.DatabaseConnectionPool(config.databaseHost,config.databaseName,config.databaseUserName,config.databasePassword,logger)
    conn,cur = cp.connectionCursorPairNoTest()
    logger.clear()
    cp.cleanup()
    assert [logging.DEBUG,logging.DEBUG] == logger.levels
    expected = ["%s - killing thread database connections"% threading.currentThread().getName(),"%s - connection %s closed"% (threading.currentThread().getName(),threading.currentThread().getName())]
    assert expected == logger.buffer, "Expected %s got %s"%(expected, logger.buffer)

    logger.clear()
    cp.cleanup()
    assert [logging.DEBUG,logging.DEBUG] == logger.levels
    expected = ["%s - killing thread database connections"% threading.currentThread().getName(),"%s - connection %s already closed"% (threading.currentThread().getName(),threading.currentThread().getName())]
    assert expected == logger.buffer, "Expected %s got %s"%(expected, logger.buffer)

  def testLoggingCursorExecute(self):
    logCursor = self.connection.cursor(cursor_factory=ppghelper.LoggingCursor)
    logCursor.setLogger(self.logger)
    self.logger.clear()
    logCursor.execute('select 4;')
    assert logging.INFO == self.logger.levels[0], "Expect level %s, go %s"%(logging.INFO,self.logger.levels[0])
    assert self.logger.buffer[0] == 'select 4;','... but got %s'%(self.logger.buffer[0])
    params = {'id':3}
    logCursor.execute("select id from gringo where id=%(id)s;",params)
    assert logging.INFO == self.logger.levels[1]
    expected = "select id from gringo where id=%(id)s;"%(params)
    got = self.logger.buffer[1]
    assert expected == got, "Expected [%s] but got [%s]"%(expected,got)
    params = [3]
    logCursor.execute("select id from gringo where id=%s;",params)
    expected = "select id from gringo where id=%s;"%(params[0])
    got = self.logger.buffer[2]
    assert expected == got, "Expected [%s] but got [%s]"%(expected,got)

  def testLoggingCursorExecutemany(self):
    logCursor = self.connection.cursor(cursor_factory=ppghelper.LoggingCursor)
    logCursor.setLogger(self.logger)
    self.logger.clear()
    def chargen():
      for i in 'abcdef':
        yield (i,)

    logCursor.executemany("insert into chartable values (%s)",chargen())
    assert self.logger.buffer[0] == 'insert into chartable values (%s) ...'
    assert self.logger.levels[0] == logging.INFO
    data = ('g','h')
    logCursor.executemany("insert into chartable values (%s)",data)
    assert self.logger.buffer[1].startswith("insert into chartable values")
    assert "'g'" in self.logger.buffer[1]
    assert "..." in self.logger.buffer[1]
    assert self.logger.levels[1] == logging.INFO

if __name__ == "__main__":
  unittest.main()


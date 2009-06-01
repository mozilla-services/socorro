
import psycopg2
import psycopg2.extensions
import datetime
import threading

import socorro.lib.util as util

#-----------------------------------------------------------------------------------------------------------------
def singleValueSql (aCursor, sql, parameters=None):
  aCursor.execute(sql, parameters)
  result = aCursor.fetchall()
  try:
    return result[0][0]
  except Exception, x:
    raise SQLDidNotReturnSingleValue("%s: %s" % (str(x), sql))

#-----------------------------------------------------------------------------------------------------------------
def singleRowSql (aCursor, sql, parameters=None):
  aCursor.execute(sql, parameters)
  result = aCursor.fetchall()
  try:
    return result[0]
  except Exception, x:
    raise SQLDidNotReturnSingleRow("%s: %s" % (str(x), sql))

#-----------------------------------------------------------------------------------------------------------------
def execute (aCursor, sql, parameters=None):
  aCursor.execute(sql, parameters)
  while True:
    aRow = aCursor.fetchone()
    if aRow is not None:
      yield aRow
    else:
      break

#=================================================================================================================
class LoggingCursor(psycopg2.extensions.cursor):
  """Use as cursor_factory when getting cursor from connection:
  ...
  cursor = connection.cursor(cursor_factory = socorro.lib.pyscopghelper.LoggingCursor)
  cursor.setLogger(someLogger)
  ...
  """
  #-----------------------------------------------------------------------------------------------------------------
  def setLogger(self, logger):
    self.logger = logger
    self.logger.info("Now logging cursor")
  #-----------------------------------------------------------------------------------------------------------------
  def execute(self, sql, args=None):
    try:
      self.logger.info(self.mogrify(sql,args))
    except AttributeError:
      pass
    super(LoggingCursor, self).execute(sql,args)
  def executemany(self,sql,args=None):
    try:
      try:
        self.logger.info("%s ..." % (self.mogrify(sql,args[0])))
      except TypeError:
        self.logger.info("%s ..." % (sql))
    except AttributeError:
      pass
    super(LoggingCursor,self).executemany(sql,args)

#=================================================================================================================
class SQLDidNotReturnSingleValue (Exception):
  pass

#=================================================================================================================
class SQLDidNotReturnSingleRow (Exception):
  pass

#=================================================================================================================
class CannotConnectToDatabase(Exception):
  pass

#=================================================================================================================
class DatabaseConnectionPool(dict):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, databaseHostName, databaseName, databaseUserName, databasePassword, logger=util.FakeLogger()):
    super(DatabaseConnectionPool, self).__init__()
    if databaseHostName != '':
      self.dsn = "host=%s dbname=%s user=%s password=%s" % (databaseHostName, databaseName, databaseUserName, databasePassword)
    else:
      self.dsn = "dbname=%s user=%s password=%s" % (databaseName, databaseUserName, databasePassword)
    self.logger = logger

  #-----------------------------------------------------------------------------------------------------------------
  def connectToDatabase(self):
    """ Deliberately do NOT put the connection into the pool"""
    threadName = threading.currentThread().getName()
    try:
      self.logger.info("%s - connecting to database", threadName)
      connection = psycopg2.connect(self.dsn)
      return (connection, connection.cursor())
    except Exception, x:
      self.logger.critical("%s - cannot connect to the database", threadName)
      raise CannotConnectToDatabase(x)

  #-----------------------------------------------------------------------------------------------------------------
  def connectionCursorPairNoTest(self):
    """Try to re-use this thread's connection, else create one and use that"""
    threadName = threading.currentThread().getName()
    try:
      return self[threadName]
    except KeyError:
      self[threadName] = self.connectToDatabase()
      return self[threadName]

  #-----------------------------------------------------------------------------------------------------------------
  def connectionCursorPair(self):
    """Like connecionCursorPairNoTest, but test that the specified connection actually works"""
    connection, cursor = self.connectionCursorPairNoTest()
    try:
      cursor.execute("select 1")
      cursor.fetchall()
      return (connection, cursor)
    #except (psycopg2.OperationalError, psycopg2.ProgrammingError):
    except psycopg2.Error:
      # did the connection time out?
      self.logger.info("%s - trying to re-establish a database connection", threading.currentThread().getName())
      try:
        del self[threading.currentThread().getName()]
        connection, cursor = self.connectionCursorPairNoTest()
        cursor.execute("select 1")
        cursor.fetchall()
        return (connection, cursor)
      #except (psycopg2.OperationalError, psycopg2.ProgrammingError):
      except Exception, x:
        self.logger.critical("%s - something's gone horribly wrong with the database connection", threading.currentThread().getName())
        raise CannotConnectToDatabase(x)

  #-----------------------------------------------------------------------------------------------------------------
  def cleanup (self):
    self.logger.debug("%s - killing thread database connections", threading.currentThread().getName())
    for i, aDatabaseConnectionPair in self.iteritems():
      try:
        aDatabaseConnectionPair[0].rollback()
        aDatabaseConnectionPair[0].close()
        self.logger.debug("%s - connection %s closed", threading.currentThread().getName(), i)
      except psycopg2.InterfaceError:
        self.logger.debug("%s - connection %s already closed", threading.currentThread().getName(), i)
      except:
        util.reportExceptionAndContinue(self.logger)


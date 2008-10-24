
import psycopg2
import psycopg2.extensions
import datetime
import threading

import socorro.lib.util as util

#-----------------------------------------------------------------------------------------------------------------
def singleValueSql (aCursor, sql):
  aCursor.execute(sql)
  result = aCursor.fetchall()
  try:
    return result[0][0]
  except Exception, x:
    raise SQLDidNotReturnSingleValue("%s: %s" % (str(x), sql))

#-----------------------------------------------------------------------------------------------------------------
def singleRowSql (aCursor, sql):
  aCursor.execute(sql)
  result = aCursor.fetchall()
  try:
    return result[0]
  except Exception, x:
    raise SQLDidNotReturnSingleRow("%s: %s" % (str(x), sql))

#-----------------------------------------------------------------------------------------------------------------
def execute (aCursor, sql):
  aCursor.execute(sql)
  while True:
    aRow = aCursor.fetchone()
    if aRow is not None:
      yield aRow
    else:
      break

#-----------------------------------------------------------------------------------------------------------------
def postgreSQLTypeConversion (x):
  if type(x) == datetime.datetime:
    return "'%4d-%2d-%2d %2d:%2d:%2d'" % (x.year, x.month, x.day, x.hour, x.minute, x.second)
  if type(x) == str:
    return "'%s'" % x
  return str(x)

#=================================================================================================================
class LoggingCursor(psycopg2.extensions.cursor):
  #-----------------------------------------------------------------------------------------------------------------
  def setLogger(self, logger):
    self.logger = logger
    self.logger.info("Now logging cursor")
  #-----------------------------------------------------------------------------------------------------------------
  def execute(self, sql):
    try:
      self.logger.info(sql)
    except AttributeError:
      pass
    super(LoggingCursor, self).execute(sql)

#=================================================================================================================
class SQLDidNotReturnSingleValue (Exception):
  pass

#=================================================================================================================
class SQLDidNotReturnSingleRow (Exception):
  pass

#=================================================================================================================
class CannotConnectToDatabase(Exception):
  def __init__(self, msg):
    super(CannotConnectToDatabase, self).__init__(msg)

#=================================================================================================================
class DatabaseConnectionPool(dict):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, databaseHostName, databaseName, databaseUserName, databasePassword, logger=util.FakeLogger()):
    super(DatabaseConnectionPool, self).__init__()
    self.dsn = "host=%s dbname=%s user=%s password=%s" % (databaseHostName, databaseName, databaseUserName, databasePassword)
    self.logger = logger

  #-----------------------------------------------------------------------------------------------------------------
  def connectToDatabase(self):
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
    threadName = threading.currentThread().getName()
    try:
      return self[threadName]
    except KeyError:
      self[threadName] = self.connectToDatabase()
      return self[threadName]

  #-----------------------------------------------------------------------------------------------------------------
  def connectionCursorPair(self):
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
        self.logger.debug("%s -   connection %s closed", threading.currentThread().getName(), i)
      except psycopg2.InterfaceError:
        self.logger.debug("%s -   connection %s already closed", threading.currentThread().getName(), i)
      except:
        util.reportExceptionAndContinue(self.logger)


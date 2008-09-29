
import psycopg2
import psycopg2.extensions
import datetime

class LoggingCursor(psycopg2.extensions.cursor):
  def setLogger(self, logger):
    self.logger = logger
    self.logger.info("Now logging cursor")

  def execute(self, sql):
    try:
      self.logger.info(sql)
    except AttributeError:
      pass
    super(LoggingCursor, self).execute(sql)


def postgreSQLTypeConversion (x):
  if type(x) == datetime.datetime:
    return "'%4d-%2d-%2d %2d:%2d:%2d'" % (x.year, x.month, x.day, x.hour, x.minute, x.second)
  if type(x) == str:
    return "'%s'" % x
  return str(x)

class SQLDidNotReturnSingleValue (Exception):
  pass

def singleValueSql (aCursor, sql):
  aCursor.execute(sql)
  result = aCursor.fetchall()
  try:
    return result[0][0]
  except Exception, x:
    raise SQLDidNotReturnSingleValue("%s: %s" % (str(x), sql))

class SQLDidNotReturnSingleRow (Exception):
  pass

def singleRowSql (aCursor, sql):
  aCursor.execute(sql)
  result = aCursor.fetchall()
  try:
    return result[0]
  except Exception, x:
    raise SQLDidNotReturnSingleRow("%s: %s" % (str(x), sql))

class CannotDetermineTableLength (Exception):
  pass

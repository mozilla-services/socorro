import simplejson as json

import socorro.lib.psycopghelper as psy
import logging

class Unimplemented(Exception):
  pass

class JsonServiceBase (object):
  def __init__(self, config):
    try:
      self.context = config
      self.connectionPool = psy.DatabaseConnectionPool(config.databaseHost,
                                                       config.databaseName,
                                                       config.databaseUserName,
                                                       config.databasePassword)
    except (AttributeError, KeyError):
      pass

  def databaseConnectionCursorPair(self):
    return self.connectionPool.connectToDatabase()

  def GET(self, *args):
    try:
      return json.dumps(self.get(*args))
    except Exception, x:
      return str(x)

  def get(self, *args):
    raise Unimplemented("the GET function has not been implemented for %s" % args)

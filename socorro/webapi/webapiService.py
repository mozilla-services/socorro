import simplejson as json
import logging
import web

import socorro.lib.util as util
import socorro.database.database as db

logger = logging.getLogger("webapi")

#-----------------------------------------------------------------------------------------------------------------
def typeConversion (listOfTypeConverters, listOfValuesToConvert):
  return (t(v) for t, v in zip(listOfTypeConverters, listOfValuesToConvert))

#=================================================================================================================
class Unimplemented(Exception):
  pass

#=================================================================================================================
class JsonServiceBase (object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    try:
      self.context = config
      self.database = db.Database(config)
    except (AttributeError, KeyError):
      util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def GET(self, *args):
    try:
      return json.dumps(self.get(*args))
    except Exception, x:
      stringLogger = util.StringLogger()
      util.reportExceptionAndContinue(stringLogger)
      try:
        util.reportExceptionAndContinue(self.context.logger)
      except (AttributeError, KeyError):
        pass
      raise Exception(stringLogger.getMessages())

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    raise Unimplemented("the GET function has not been implemented for %s" % args)

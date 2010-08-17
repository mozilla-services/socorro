import json
import logging
import web

import socorro.lib.util as util

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
  def __init__(self, context):
    try:
      self.context = context
      self.logger = context.logger
    except (AttributeError, KeyError):
      util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def GET(self, *args):
    try:
      result = self.get(*args)
      if type(result) is tuple:
        web.header('Content-Type', result[1])
        return result[0]
      return json.dumps(result)
    except web.HTTPError:
      raise
    except Exception:
      util.reportExceptionAndContinue(self.context.logger)
      raise

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    raise Unimplemented("the GET function has not been implemented for %s" % args)



import json
import logging
import web
import collections

import socorro.lib.util as util

logger = logging.getLogger("webapi")

#-----------------------------------------------------------------------------------------------------------------
def sanitizeForJson(something):
  if something is None:
    return None
  if type(something) in [int, str, float, unicode]:
    return something
  if isinstance(something, collections.Mapping):
    return dict((k, sanitizeForJson(v)) for k, v in something.iteritems())
  if isinstance(something, collections.Iterable):
    print something, type(something)
    return [sanitizeForJson(x) for x in something]
  return str(something)

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
  def transformReturn(self, returnValue):
    return returnValue

  #-----------------------------------------------------------------------------------------------------------------
  def GET(self, *args):
    try:
      result = self.get(*args)
      if type(result) is tuple:
        web.header('Content-Type', result[1])
        return result[0]
      return json.dumps(self.transformReturn(result))
    except web.HTTPError:
      raise
    except Exception:
      util.reportExceptionAndContinue(self.context.logger)
      raise

  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    raise Unimplemented("the GET function has not been implemented for %s" % args)

  #-----------------------------------------------------------------------------------------------------------------
  def POST(self, *args):
    try:
      result = self.post()
      if type(result) is tuple:
        web.header('Content-Type', result[1])
        return result[0]
      return json.dumps(self.transformReturn(result))
    except web.HTTPError:
      raise
    except Exception:
      util.reportExceptionAndContinue(self.context.logger)
      raise

  #-----------------------------------------------------------------------------------------------------------------
  def post(self, *args):
    raise Unimplemented("the POST function has not been implemented.")

#=================================================================================================================
class SanitizedJsonServiceBase (JsonServiceBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context):
    super(SanitizedJsonServiceBase, self).__init__(context)

  #-----------------------------------------------------------------------------------------------------------------
  def transformReturn(self, returnValue):
    return sanitizeForJson(returnValue)



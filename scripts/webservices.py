#!/usr/bin/python

import web
import datetime as dt

import config.webapiconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.datetimeutil as dtutil
import socorro.webapi.webapiService as webapi
#import socorro.webapi.hello as hello

import logging
import logging.handlers

configContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Socorro Webapi")


logger = logging.getLogger("webapi")
logger.setLevel(logging.DEBUG)

if not logger.handlers: #we're in a multithreaded environment and logger is a global singleton - don't add more than 1 handler
  rotatingFileLog = logging.handlers.RotatingFileHandler(configContext.logFilePathname, "a", configContext.logFileMaximumSize, configContext.logFileMaximumBackupHistory)
  rotatingFileLog.setLevel(configContext.logFileErrorLoggingLevel)
  rotatingFileLogFormatter = logging.Formatter(configContext.logFileLineFormatString)
  rotatingFileLog.setFormatter(rotatingFileLogFormatter)
  logger.addHandler(rotatingFileLog)

logger.info("current configuration\n%s", str(configContext))

#configContext['logger'] = logger

def typeConversion (listOfTypeConverters, listOfValuesToConvert):
  return (t(v) for t, v in zip(listOfTypeConverters, listOfValuesToConvert))

def strHoursToTimeDelta(hoursAsString):
  return dt.timedelta(hours=int(hoursAsString))

#=================================================================================================================
class DotDict(dict):
  __getattr__= dict.__getitem__
  __setattr__= dict.__setitem__
  __delattr__= dict.__delitem__

#=================================================================================================================
import socorro.services.topCrashBySignatureTrends as tcbst
class TopCrashBySignatureTrends(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self):
    super(TopCrashBySignatureTrends, self).__init__(configContext)
    logger.debug('TopCrashBySignatureTrends __init__')
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/200911/topcrash/sig/trend/rank/p/(.*)/v/(.*)/end/(.*)/duration/(.*)/listsize/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = typeConversion([str, str, dtutil.datetimeFromISOdateString, strHoursToTimeDelta, int], args)
    parameters = DotDict(zip(['product','version', 'endDate','duration', 'listSize'], convertedArgs))
    parameters.os_name = ''
    parameters.os_version = ''
    logger.debug("TopCrashBySignatureTrends %s", parameters)
    parameters.logger = logger
    connection, cursor = self.databaseConnectionCursorPair()
    return tcbst.twoPeriodTopCrasherComparison(cursor, parameters)


#=================================================================================================================
urls = (
  TopCrashBySignatureTrends.uri, TopCrashBySignatureTrends,
)

app = web.application(urls, globals())


if __name__ == "__main__":
  app.run()

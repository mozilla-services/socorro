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

configContext['logger'] = logger

#=================================================================================================================
def proxyClassWithContext (aClass):
  class proxyClass(aClass):
    def __init__(self):
      super(proxyClass,self).__init__(configContext)
  logger.debug ('in proxy: %s', configContext)
  return proxyClass

#=================================================================================================================

web.webapi.internalerror = web.debugerror

urls = tuple(y for aTuple in ((x.uri, proxyClassWithContext(x)) for x in configContext.servicesList) for y in aTuple)
logger.info(str(urls))

if configContext.wsgiInstallation:
  logger.info('This is a wsgi installation')
  application = web.wsgifunc(web.webpyfunc(urls, globals()))
else:
  logger.info('This is stand alone installation without wsgi')
  app = web.application(urls, globals())


if __name__ == "__main__":
  app.run()

#!/usr/bin/python

import web
import datetime as dt

import config.webapiconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.datetimeutil as dtutil
import socorro.lib.productVersionCache as pvc
import socorro.webapi.webapiService as webapi

import logging
import logging.handlers

config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Socorro Webapi")

logger = logging.getLogger("webapi")
logger.setLevel(logging.DEBUG)

syslog = logging.handlers.SysLogHandler(facility=config.syslogFacilityString)
syslog.setLevel(config.syslogErrorLoggingLevel)
syslogFormatter = logging.Formatter(config.syslogLineFormatString)
syslog.setFormatter(syslogFormatter)
logger.addHandler(syslog)

sutil.echoConfig(logger, config)

config['logger'] = logger
config['productVersionCache'] = pvc.ProductVersionCache(config)

#=================================================================================================================
def proxyClassWithContext (aClass):
  class proxyClass(aClass):
    def __init__(self):
      super(proxyClass,self).__init__(config)
  #logger.debug ('in proxy: %s', config)
  return proxyClass

web.webapi.internalerror = web.debugerror

urls = tuple(y for aTuple in ((x.uri, proxyClassWithContext(x)) for x in config.servicesList) for y in aTuple)
logger.info(str(urls))

if config.wsgiInstallation:
  logger.info('This is a wsgi installation')
  application = web.application(urls, globals()).wsgifunc()
else:
  logger.info('This is stand alone installation without wsgi')
  app = web.application(urls, globals())


if __name__ == "__main__":
  app.run()

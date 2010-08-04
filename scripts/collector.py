#!/usr/bin/python

import web
import datetime as dt

import config.collectorconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.webapi.webapiService as webapi
import socorro.webapi.classPartial as cpart
import socorro.collector.wsgicollector as wscol
#import socorro.webapi.hello as hello

#-------------------------------------------------------------------------------
configurationContext = \
    configurationManager.newConfiguration(configurationModule=config,
                                          applicationName="Socorro Collector 3.0")

#-------------------------------------------------------------------------------
import logging
import logging.handlers

logger = logging.getLogger("collector")
logger.setLevel(logging.DEBUG)

syslog = logging.handlers.SysLogHandler(
  address=(configurationContext.syslogHost, configurationContext.syslogPort),
  facility=configurationContext.syslogFacilityString,
)
syslog.setLevel(configurationContext.syslogErrorLoggingLevel)
syslogFormatter = logging.Formatter(configurationContext.syslogLineFormatString)
syslog.setFormatter(syslogFormatter)
logger.addHandler(syslog)

logger.info("current configuration:")
for value in str(configurationContext).split('\n'):
    logger.info('%s', value)

configurationContext.logger = logger

#-------------------------------------------------------------------------------
import socorro.storage.crashstorage as cstore
crashStoragePool = cstore.CrashStoragePool(configurationContext,
                                           cstore.CollectorCrashStorageSystemForHBase)
configurationContext.crashStoragePool = crashStoragePool

legacyThrottler = cstore.LegacyThrottler(configurationContext)
configurationContext.legacyThrottler = legacyThrottler

#-------------------------------------------------------------------------------
web.webapi.internalerror = web.debugerror
web.config.debug = False
servicesList = (wscol.Collector,
               )
urls = tuple(y for aTuple in ((x.uri, cpart.classWithPartialInit(x, configurationContext))
                    for x in servicesList) for y in aTuple)
logger.info(str(urls))

if configurationContext.modwsgiInstallation:
    logger.info('This is a mod_wsgi installation')
    application = web.application(urls, globals()).wsgifunc()
else:
    logger.info('This is stand alone installation without mod_wsgi')
    import socorro.webapi.webapp as sweb
    app =  sweb.StandAloneWebApplication(configurationContext.serverIPAddress,
                                         configurationContext.serverPort,
                                         urls,
                                         globals())

if __name__ == "__main__":
    try:
        app.run()
    finally:
        crashStoragePool.cleanup()

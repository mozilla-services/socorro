# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import web
import socorro.webapi.class_partial as cpart
import socorro.lib.ConfigurationManager as cm
import socorro.collector.wsgicollector as wscol
import socorro.lib.util as sutil
#import socorro.webapi.hello as hello

import config.collectorconfig as collectorConfig

#-------------------------------------------------------------------------------
config = \
    cm.newConfiguration(configurationModule=collectorConfig,
                                        applicationName="Socorro Collector 3.0")

#-------------------------------------------------------------------------------
import logging
import logging.handlers

logger = logging.getLogger("collector")
logger.setLevel(logging.DEBUG)

syslog = logging.handlers.SysLogHandler(
  address=(config.syslogHost, config.syslogPort),
  facility=config.syslogFacilityString,
)
syslog.setLevel(config.syslogErrorLoggingLevel)
syslogFormatter = logging.Formatter(config.syslogLineFormatString)
syslog.setFormatter(syslogFormatter)
logger.addHandler(syslog)

sutil.echoConfig(logger, config)

config.logger = logger

#-------------------------------------------------------------------------------
import socorro.storage.crashstorage as cstore
crashStoragePool = cstore.CrashStoragePool(config,
                                    config.primaryStorageClass)
config.crashStoragePool = crashStoragePool

legacyThrottler = cstore.LegacyThrottler(config)
config.legacyThrottler = legacyThrottler

#-------------------------------------------------------------------------------
web.webapi.internalerror = web.debugerror
web.config.debug = False
servicesList = (wscol.Collector,
               )
urls = tuple(y for aTuple in ((x.uri, cpart.class_with_partial_init(x, config))
                    for x in servicesList) for y in aTuple)
logger.info(str(urls))

if config.modwsgiInstallation:
    logger.info('This is a mod_wsgi installation')
    application = web.application(urls, globals()).wsgifunc()
else:
    logger.info('This is stand alone installation without mod_wsgi')
    import socorro.webapi.webapp as sweb
    app =  sweb.StandAloneWebApplication(config.serverIPAddress,
                                         config.serverPort,
                                         urls,
                                         globals())

if __name__ == "__main__":
    try:
        app.run()
    finally:
        crashStoragePool.cleanup()

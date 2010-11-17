import os
import logging
import logging.handlers

import socorro.lib.ConfigurationManager
import socorro.lib.util as sutil
import socorro.lib.JsonDumpStorage as jds

import socorro.storage.crashstorage as cstore

#-----------------------------------------------------------------------------------------------------------------
def createPersistentInitialization(configModule):
  storage = sutil.DotDict()

  storage.config = config = socorro.lib.ConfigurationManager.newConfiguration(configurationModule=configModule,automaticHelp=False)
  storage.logger = logger = logging.getLogger("collector")

  logger.setLevel(logging.DEBUG)

  syslog = logging.handlers.SysLogHandler(
    address=(config.syslogHost, config.syslogPort),
    facility=config.syslogFacilityString,
  )
  syslog.setLevel(config.syslogErrorLoggingLevel)
  syslogFormatter = logging.Formatter(config.syslogLineFormatString)
  syslog.setFormatter(syslogFormatter)
  logger.addHandler(syslog)

  logger.info("current configuration:")
  for value in str(config).split('\n'):
      logger.info('%s', value)

  storage.config['logger'] = logger

  storage.crashStorage = cstore.CrashStorageSystemForLocalFS(config)

  storage.legacyThrottler = cstore.LegacyThrottler(config)

  return storage

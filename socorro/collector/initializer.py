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
  rotatingFileLog = logging.handlers.RotatingFileHandler(config.logFilePathname, "a", config.logFileMaximumSize, config.logFileMaximumBackupHistory)
  rotatingFileLog.setLevel(config.logFileErrorLoggingLevel)
  rotatingFileLogFormatter = logging.Formatter(config.logFileLineFormatString)
  rotatingFileLog.setFormatter(rotatingFileLogFormatter)
  logger.addHandler(rotatingFileLog)

  logger.info("current configuration\n%s", str(config))

  storage.config['logger'] = logger

  if config.crashStorageClass == 'CrashStorageSystemForHBase':
    storage.crashStorage = cstore.CollectorCrashStorageSystemForHBase(config)
    if config.useBackupNFSStorage:
      storage.altCrashStorage = cstore.CrashStorageSystemForNFS(config)
  else:
    storage.crashStorage = cstore.CrashStorageSystemForNFS(config)

  storage.legacyThrottler = cstore.LegacyThrottler(config)

  return storage

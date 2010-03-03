import os
import logging
import logging.handlers

import socorro.lib.ConfigurationManager
import socorro.lib.util as sutil
import socorro.lib.JsonDumpStorage as jds

import socorro.collector.collect as collect

#for perf, remove me soon
import time

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

  storage.nfsStorage = collect.CrashStorageSystemForNFS(config)

  if config.hbaseSubmissionRate:
    beforeCreate = time.time()
    storage.hbaseStorage = collect.CrashStorageSystemForHBase(config)
    logger.info("Time to Create hbase conn %s" % (time.time() - beforeCreate))
  else:
    logger.info("because the config.hbaseSubmissionRate is zero or None, no hbaseConnection is created.")

  return storage

import os
import logging
import logging.handlers

import socorro.lib.ConfigurationManager
import socorro.lib.util as sutil
import socorro.lib.JsonDumpStorage as jds

import socorro.collector.collect as collect

#-----------------------------------------------------------------------------------------------------------------
def createPersistentInitialization(configModule):
  storage = {}

  storage["config"] = config = socorro.lib.ConfigurationManager.newConfiguration(configurationModule=configModule,automaticHelp=False)
  storage["collectObject"] = collect.Collect(config)
  storage["hostname"] = os.uname()[1]
  storage["logger"] = logger = logging.getLogger("collector")

  logger.setLevel(logging.DEBUG)
  rotatingFileLog = logging.handlers.RotatingFileHandler(config.logFilePathname, "a", config.logFileMaximumSize, config.logFileMaximumBackupHistory)
  rotatingFileLog.setLevel(config.logFileErrorLoggingLevel)
  rotatingFileLogFormatter = logging.Formatter(config.logFileLineFormatString)
  rotatingFileLog.setFormatter(rotatingFileLogFormatter)
  logger.addHandler(rotatingFileLog)

  logger.info("current configuration\n%s", str(config))

  standardFileSystemStorage = jds.JsonDumpStorage(root = config.storageRoot,
                                                  maxDirectoryEntries = config.dumpDirCount,
                                                  jsonSuffix = config.jsonFileSuffix,
                                                  dumpSuffix = config.dumpFileSuffix,
                                                  dumpGID = config.dumpGID,
                                                  dumpPermissions = config.dumpPermissions,
                                                  dirPermissions = config.dirPermissions,
                                                 )
  storage["standardFileSystemStorage"] = standardFileSystemStorage
  deferredFileSystemStorage = jds.JsonDumpStorage(root = config.deferredStorageRoot,
                                                  maxDirectoryEntries = config.dumpDirCount,
                                                  jsonSuffix = config.jsonFileSuffix,
                                                  dumpSuffix = config.dumpFileSuffix,
                                                  dumpGID = config.dumpGID,
                                                  dumpPermissions = config.dumpPermissions,
                                                  dirPermissions = config.dirPermissions,
                                                 )
  storage["deferredFileSystemStorage"] = deferredFileSystemStorage

  return storage
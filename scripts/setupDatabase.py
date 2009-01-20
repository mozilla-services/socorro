#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.setupdatabaseconfig as config
except ImportError:
  import setupdatabaseconfig as config

import socorro.database.schema as socorro_schema
import socorro.lib.ConfigurationManager as configurationManager

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Socorro Database Setup 1.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("setupDatabase")
logger.setLevel(logging.DEBUG)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(configurationContext.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(configurationContext.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

rotatingFileLog = logging.handlers.RotatingFileHandler(configurationContext.logFilePathname, "a", configurationContext.logFileMaximumSize, configurationContext.logFileMaximumBackupHistory)
rotatingFileLog.setLevel(configurationContext.logFileErrorLoggingLevel)
rotatingFileLogFormatter = logging.Formatter(configurationContext.logFileLineFormatString)
rotatingFileLog.setFormatter(rotatingFileLogFormatter)
logger.addHandler(rotatingFileLog)

logger.info("current configuration\n%s", str(configurationContext))

try:
  socorro_schema.setupDatabase(configurationContext, logger)
finally:
  logger.info("done.")



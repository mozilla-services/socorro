#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.bugzillaconfig as config
except ImportError:
  import bugzillaconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.bugzilla as bug

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Bugzilla Associations 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("bugzilla")
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
  bug.record_associations(configurationContext)
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()




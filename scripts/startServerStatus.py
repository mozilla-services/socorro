#! /usr/bin/env python

import logging
import logging.handlers
import sys

try:
  import config.serverstatusconfig as config
except ImportError:
    import serverstatusconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.serverstatus as serverstatus

try:
  configContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Server Status Summary")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("server_status_summary")
logger.setLevel(logging.DEBUG)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(configContext.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(configContext.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

rotatingFileLog = logging.handlers.RotatingFileHandler(configContext.logFilePathname, "a", configContext.logFileMaximumSize, configContext.logFileMaximumBackupHistory)
rotatingFileLog.setLevel(logging.DEBUG)
rotatingFileLogFormatter = logging.Formatter(configContext.logFileLineFormatString)
rotatingFileLog.setFormatter(rotatingFileLogFormatter)
logger.addHandler(rotatingFileLog)

logger.info("current configuration\n%s", str(configContext))

try:
  serverstatus.update(configContext, logger)
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()

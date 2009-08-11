#! /usr/bin/env python

import logging
import logging.handlers
import sys
import time

try:
  import config.topCrashesByUrlConfig as config
except ImportError:
  import topCrashesByUrlconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.topcrashbyurl as tcbyurl

configContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Top Crash By URL Summary")

logger = tcbyurl.logger
loggerLevel = configContext.logFileErrorLoggingLevel
logger.setLevel(loggerLevel)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(configContext.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(configContext.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

rotatingFileLog = logging.handlers.RotatingFileHandler(configContext.logFilePathname, "a", configContext.logFileMaximumSize, configContext.logFileMaximumBackupHistory)
rotatingFileLog.setLevel(loggerLevel)
rotatingFileLogFormatter = logging.Formatter(configContext.logFileLineFormatString)
rotatingFileLog.setFormatter(rotatingFileLogFormatter)
logger.addHandler(rotatingFileLog)

logger.info("current configuration\n%s", str(configContext))

try:
  before = time.time()
  tu = tcbyurl.TopCrashesByUrl(configContext)
  tu.processDateInterval()
  logger.info("Successfully ran in %d seconds" % (time.time() - before))
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()

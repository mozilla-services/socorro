#! /usr/bin/env python

import logging
import logging.handlers
import sys
import time

try:
  import config.topCrashesBySignatureConfig as config
except ImportError:
    import topCrashesBySignatureConfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.topCrashesBySignature as topcrasher

try:
  configContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Top Crashes Summary")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

loggerLevel = configContext.logFileErrorLoggingLevel
logger = topcrasher.logger
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
  tc = topcrasher.TopCrashesBySignature(configContext)
  count = tc.processDateInterval()
  logger.info("Successfully processed %s items in %3.2f seconds",count, time.time()-before)
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()

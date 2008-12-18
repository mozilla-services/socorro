#! /usr/bin/env python

import logging
import logging.handlers
import sys
import time

try:
  import config.mtbfconfig as config
except ImportError:
  import mtbfconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.mtbf as mtbf

#try:
configContext = configurationManager.newConfiguration(configurationModule=config, applicationName="MTBF Summary")
#except configurationManager.NotAnOptionError, x:
#  print >>sys.stderr, x
#  print >>sys.stderr, "for usage, try --help"
#  sys.exit(1)

logger = logging.getLogger("mtbf_summary")
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
  before = time.time()
  mtbf.calculateMtbf(configContext, logger)
  logger.info("Successfully ran in %d seconds" % (time.time() - before))
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()

#! /usr/bin/env python

import logging
import logging.handlers
import sys
import datetime as dt

try:
  import config.deferredcleanupconfig as config
except ImportError:
  import deferredcleanupconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as util
import socorro.lib.JsonDumpStorage as jds

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Socorro Deferred Storage Cleanup 1.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("deferred_storage_cleanup")
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
  try:
    logger.info("beginning deferredJobCleanup")
    j = jds.JsonDumpStorage(root = configurationContext.deferredStorageRoot,
                            logger=logger)
    numberOfDaysAsTimeDelta = dt.timedelta(days=int(configurationContext.maximumDeferredJobAge))
    threshold = dt.datetime.now() - numberOfDaysAsTimeDelta
    logger.info("  removing older than: %s", threshold)
    j.removeOlderThan(threshold)
  except (KeyboardInterrupt, SystemExit):
    logger.debug("got quit message")
  except:
    util.reportExceptionAndContinue(logger)
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()
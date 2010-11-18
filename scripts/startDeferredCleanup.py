#! /usr/bin/env python

import logging
import logging.handlers
import sys
import datetime as dt

try:
  import config.deferredcleanupconfig as configModule
except ImportError:
  import deferredcleanupconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as sutil
import socorro.lib.JsonDumpStorage as jds

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Socorro Deferred Storage Cleanup 1.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("deferred_storage_cleanup")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  try:
    logger.info("beginning deferredJobCleanup")
    j = jds.JsonDumpStorage(root = config.deferredStorageRoot,
                            logger=logger)
    numberOfDaysAsTimeDelta = dt.timedelta(days=int(config.maximumDeferredJobAge))
    threshold = dt.datetime.now() - numberOfDaysAsTimeDelta
    logger.info("  removing older than: %s", threshold)
    j.removeOlderThan(threshold)
  except (KeyboardInterrupt, SystemExit):
    logger.debug("got quit message")
  except:
    sutil.reportExceptionAndContinue(logger)
finally:
  logger.info("done.")

#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.reportsCleanconfig as configModule
except ImportError:
  import reportsCleanconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.reportsClean as reportsClean
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Reports Clean 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("reportsClean")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  reportsClean.run(config)
finally:
  logger.info("done.")


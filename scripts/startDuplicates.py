#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.duplicatesconfig as configModule
except ImportError:
  import duplicatesconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.duplicates as duplicates
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Duplicate Detector 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("duplicates")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  duplicates.find_duplicates(config)
finally:
  logger.info("done.")




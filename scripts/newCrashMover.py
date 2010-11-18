#! /usr/bin/env python

import sys
import logging
import logging.handlers

import config.crashmoverconfig as cmconf

import socorro.lib.ConfigurationManager as configurationManager
import socorro.storage.storageMover as smover

try:
  config = configurationManager.newConfiguration(configurationModule=cmconf, applicationName="New Crash Mover")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("newCrashMover")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger

try:
  smover.move(config)
finally:
  logger.info("done.")




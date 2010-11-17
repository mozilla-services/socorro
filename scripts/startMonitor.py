#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.monitorconfig as configModule
except ImportError:
  import monitorconfig as configModule

import socorro.monitor.monitor as monitor
import socorro.lib.ConfigurationManager as configurationManager

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Socorro Monitor 2.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("monitor")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  while True:
    m = monitor.Monitor(config)
    m.start()
finally:
  logger.info("done.")



#! /usr/bin/env python

import logging
import logging.handlers
import sys

try:
  import config.serverstatusconfig as configModule
except ImportError:
    import serverstatusconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.serverstatus as serverstatus

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Server Status Summary")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("server_status_summary")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  serverstatus.update(config, logger)
finally:
  logger.info("done.")

#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.bugzillaconfig as configModule
except ImportError:
  import bugzillaconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.bugzilla as bug

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Bugzilla Associations 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("bugzilla")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)
  
try:
  bug.record_associations(config)
finally:
  logger.info("done.")




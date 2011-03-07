#! /usr/bin/env python

import logging
import logging.handlers
import sys

try:
  import config.fixbrokendumpsconfig as configModule
except ImportError:
    import fixbrokendumpsconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.fixBrokenDumps as fixBrokenDumps
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Fix Broken Dumps")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("fix_broken_dumps")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  #fixBrokenDumps.fix(config, logger, config.brokenFirefoxLinuxQuery, config.brokenFirefoxLinuxFixer)
  fixBrokenDumps.fix(config, logger, config.brokenFennecQuery, config.brokenFennecFixer)
finally:
  logger.info("done.")

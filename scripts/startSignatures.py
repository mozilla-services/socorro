#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.signaturesconfig as configModule
except ImportError:
  import signaturesconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.signatures as signatures
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Signatures 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("signatures")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  signatures.update_signatures(config)
finally:
  logger.info("done.")


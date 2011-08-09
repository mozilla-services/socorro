#! /usr/bin/env python

import sys
import logging
import logging.handlers

import config.orphansubmitterconf as cmconf

import socorro.lib.ConfigurationManager as configurationManager
import socorro.storage.orphans as smover
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=cmconf,
                                                 applicationName="Orphan Submitter")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("orphanSubmitter")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger

try:
  smover.move(config)
finally:
  logger.info("done.")


#! /usr/bin/env python

import logging
import logging.handlers
import sys
import time

try:
  import config.topCrashesByUrlConfig as configModule
except ImportError:
  import topCrashesByUrlConfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.topCrashesByUrl as tcbyurl
import socorro.lib.util as sutil

config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Top Crash By URL Summary")

logger = tcbyurl.logger
loggerLevel = config.logFileErrorLoggingLevel
logger.setLevel(loggerLevel)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  before = time.time()
  tu = tcbyurl.TopCrashesByUrl(config)
  tu.processDateInterval()
  logger.info("Successfully ran in %d seconds" % (time.time() - before))
finally:
  logger.info("done.")

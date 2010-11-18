#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.dailycrashconfig as configModule
except ImportError:
  import dailycrashconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.daily_crash as daily_crash
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Daily Crash")
except configurationManager.NotAnOptionError, x:
  print >> sys.stderr, x
  print >> sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("daily_cron")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  daily_crash.record_crash_stats(config, logger)
finally:
  logger.info("done.")




#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.dailyurlconfig as configModule
except ImportError:
  import dailyurlconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.dailyUrl as url
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Daily URL Dump 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("dailyUrlDump")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  url.dailyUrlDump(config)
finally:
  logger.info("done.")




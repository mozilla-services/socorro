#! /usr/bin/env python

import sys
import logging
import logging.handlers
from datetime import date, timedelta

try:
    import config.dailyMatviewsConfig as configModule
except ImportError:
    import dailyMatviewsConfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.dailyMatviews as dailyMatviews
import socorro.lib.util as sutil

try:
    config = configurationManager.newConfiguration(
        configurationModule=configModule, applicationName="dailyMatviews 0.1")
except configurationManager.NotAnOptionError, x:
    print >>sys.stderr, x
    print >>sys.stderr, "for usage, try --help"
    sys.exit()

logger = logging.getLogger("dailyMatviews")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

exitCode = 255

try:
    targetDate = date.today() - timedelta(1)
    exitCode = dailyMatviews.update(config, targetDate)
finally:
    logger.info("done.")

sys.exit(exitCode)

#! /usr/bin/env python

import sys
import logging
import logging.handlers
from datetime import date, timedelta

try:
    import config.newtcbsconfig as configModule
except ImportError:
    import newtcbsconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.newtcbs as newtcbs
import socorro.lib.util as sutil

try:
    config = configurationManager.newConfiguration(
        configurationModule=configModule, applicationName="newTCBS 0.1")
except configurationManager.NotAnOptionError, x:
    print >>sys.stderr, x
    print >>sys.stderr, "for usage, try --help"
    sys.exit()

logger = logging.getLogger("newtcbs")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

exitCode = 255

try:
    targetDate = date.today() - timedelta(1)
    exitCode = newtcbs.update(config, targetDate)
finally:
    logger.info("done.")

sys.exit(exitCode)

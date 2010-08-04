#! /usr/bin/env python

import sys
import logging
import logging.handlers

import config.dbfeederconfig as config

import socorro.processor.dbfeeder as feeder
import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as util

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Socorro Database Feeder 1.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("dbfeeder")
logger.setLevel(logging.DEBUG)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(configurationContext.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(configurationContext.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

syslog = logging.handlers.SysLogHandler(
  address=(configurationContext.syslogHost, configurationContext.syslogPort),
  facility=configurationContext.syslogFacilityString,
)
syslog.setLevel(configurationContext.syslogErrorLoggingLevel)
syslogFormatter = logging.Formatter(configurationContext.syslogLineFormatString)
syslog.setFormatter(syslogFormatter)
logger.addHandler(syslog)

logger.info("current configuration\n%s", str(configurationContext))

configurationContext.logger = logger

try:
  try:
    f = feeder.DbFeeder(configurationContext)
    f.start()
  except Exception:
    util.reportExceptionAndContinue(logger)
finally:
  logger.info("done.")

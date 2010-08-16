#! /usr/bin/env python

import logging
import logging.handlers
import sys
import datetime as dt

try:
  import config.createpartitionsconfig as config
except ImportError:
    import createpartitionsconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.schema as schema

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="startNextPartition")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("nextPartition")
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

try:
  configurationContext["endDate"] = configurationContext.startDate + dt.timedelta(configurationContext.weeksIntoFuture * 7)
  print
  schema.createPartitions(configurationContext, logger)
finally:
  logger.info("done.")

#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.dailyurlconfig as config
except ImportError:
  import dailyurlconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.dailyUrl as url

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Daily URL Dump 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("dailyUrlDump")
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
  url.dailyUrlDump(configurationContext)
finally:
  logger.info("done.")




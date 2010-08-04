#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.bugzillaconfig as config
except ImportError:
  import bugzillaconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.bugzilla as bug

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Bugzilla Associations 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("bugzilla")
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
  bug.record_associations(configurationContext)
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()




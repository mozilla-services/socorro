#! /usr/bin/env python

import sys
import logging
import logging.handlers

import config.hbaseresubmitconfig as hbrconf

import socorro.lib.ConfigurationManager as cm
import socorro.cron.hbaseResubmit as hbr

try:
  configurationContext = cm.newConfiguration(configurationModule=hbrconf,
                                             applicationName="HBase Resubmit")
except cm.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("hbaseresubmit")
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

configurationContext['logger'] = logger

try:
  hbr.resubmit(configurationContext)
finally:
  logger.info("done.")




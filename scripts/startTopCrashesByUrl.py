#! /usr/bin/env python

import logging
import logging.handlers
import sys
import time

try:
  import config.topCrashesByUrlConfig as config
except ImportError:
  import topCrashesByUrlConfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.topCrashesByUrl as tcbyurl

configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Top Crash By URL Summary")

logger = logging.getLogger("topCrashesByUrl")
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
  before = time.time()
  tu = tcbyurl.TopCrashesByUrl(configurationContext)
  tu.processDateInterval()
  logger.info("Successfully ran in %d seconds" % (time.time() - before))
finally:
  logger.info("done.")

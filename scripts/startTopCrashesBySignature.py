#! /usr/bin/env python

import logging
import logging.handlers
import sys
import time

try:
  import config.topCrashesBySignatureConfig as config
except ImportError:
    import topCrashesBySignatureConfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.topCrashesBySignature as topcrasher

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Top Crashes Summary")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("topCrashBySignature")
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
  tc = topcrasher.TopCrashesBySignature(configurationContext)
  count = tc.processDateInterval()
  logger.info("Successfully processed %s items in %3.2f seconds",count, time.time()-before)
finally:
  logger.info("done.")

#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.hbasetonfsconfig as hb2nfconf
except ImportError:
  import hbasetonfsconfig as hb2nfconf

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.hbaseResubmit as hbr

try:
  conf = configurationManager.newConfiguration(configurationModule=hb2nfconf, applicationName="HBase Resubmit")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("hbaseresubmit")
logger.setLevel(logging.DEBUG)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(conf.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(conf.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

syslog = logging.handlers.SysLogHandler(facility=configContext.syslogFacilityString)
syslog.setLevel(configContext.syslogErrorLoggingLevel)
syslogFormatter = logging.Formatter(configContext.syslogLineFormatString)
syslog.setFormatter(syslogFormatter)
logger.addHandler(syslog)

logger.info("current configuration:")
for value in str(configContext).split('\n'):
  logger.info('%s', value)
  
collectorLogger = logging.getLogger("collector")
collectorLogger.addHandler(stderrLog)
collectorLogger.addHandler(rotatingFileLog)

conf.logger = logger

try:
  hbr.hbaseToNfsResubmit(conf)
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()




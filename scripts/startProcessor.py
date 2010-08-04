#! /usr/bin/env python

import sys
import logging
import logging.handlers

import config.processorconfig as configModule

import socorro.processor.streamProcessor as processor
import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as util

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Socorro Processor 4.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("processor")
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

logger.info("current configuration:")
for value in str(configurationContext).split('\n'):
  logger.info('%s', value)

configurationContext["logger"] = logger

try:
  try:
    p = processor.StreamBreakpadProcessor(configurationContext)
    p.start()
  except Exception:
    util.reportExceptionAndContinue(logger)
finally:
  logger.info("done.")
  syslog.flush()
  syslog.close()




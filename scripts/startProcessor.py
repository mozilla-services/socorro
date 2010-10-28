#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.processorconfig as config
except ImportError:
  import processorconfig as config

import socorro.processor.externalProcessor as processor
import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as util

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Socorro Processor 2.0")
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

rotatingFileLog = logging.handlers.RotatingFileHandler(configurationContext.logFilePathname, "a", configurationContext.logFileMaximumSize, configurationContext.logFileMaximumBackupHistory)
rotatingFileLog.setLevel(configurationContext.logFileErrorLoggingLevel)
rotatingFileLogFormatter = logging.Formatter(configurationContext.logFileLineFormatString)
rotatingFileLog.setFormatter(rotatingFileLogFormatter)
logger.addHandler(rotatingFileLog)

logger.info("current configuration\n%s", str(configurationContext))

configurationContext['logger'] = logger

try:
  try:
    p = processor.ProcessorWithExternalBreakpad(configurationContext)
    p.start()
  except:
    util.reportExceptionAndContinue(logger)
finally:
  logger.info("done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()




#! /usr/bin/env python

import sys
import logging
import logging.handlers

try:
  import config.processorconfig as configModule
except ImportError:
  import processorconfig as configModule

import socorro.processor.externalProcessor as processor
import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Socorro Processor 2.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("processor")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config['logger'] = logger

try:
  try:
    p = processor.ProcessorWithExternalBreakpad(config)
    p.start()
  except:
    sutil.reportExceptionAndContinue(logger)
finally:
  logger.info("done.")




#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


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




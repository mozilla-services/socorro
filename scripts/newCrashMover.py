#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import logging
import logging.handlers

import config.crashmoverconfig as cmconf

import socorro.lib.ConfigurationManager as configurationManager
import socorro.storage.storageMover as smover
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=cmconf, applicationName="New Crash Mover")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("newCrashMover")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger

try:
  smover.move(config)
finally:
  logger.info("done.")




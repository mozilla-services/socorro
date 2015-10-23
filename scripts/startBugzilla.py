#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import logging
import logging.handlers

try:
  import config.bugzillaconfig as configModule
except ImportError:
  import bugzillaconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.bugzilla as bug
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Bugzilla Associations 0.1")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("bugzilla")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  bug.record_associations(config)
finally:
  logger.info("done.")


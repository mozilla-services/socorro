#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import logging
import logging.handlers
import sys

try:
  import config.serverstatusconfig as configModule
except ImportError:
    import serverstatusconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.serverstatus as serverstatus
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="Server Status Summary")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("server_status_summary")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

try:
  serverstatus.update(config, logger)
finally:
  logger.info("done.")

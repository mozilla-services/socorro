#! /usr/bin/env python
"""
fetchBuilds.py is used to get the primary nightly builds from ftp.mozilla.org, record
the build information and provide that information through the Crash Reporter website.

This script is expected to be run once per day.
"""

import logging
import logging.handlers

try:
  import config.buildsconfig as configModule
except ImportError:
  import buildsconfig as configModule

import socorro.cron.builds as builds
import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util as sutil

config = configurationManager.newConfiguration(configurationModule = configModule, applicationName='startBuilds.py')
assert "databaseHost" in config, "databaseHost is missing from the configuration"
assert "databaseName" in config, "databaseName is missing from the configuration"
assert "databaseUserName" in config, "databaseUserName is missing from the configuration"
assert "databasePassword" in config, "databasePassword is missing from the configuration"
assert "base_url" in config, "base_url is missing from the configuration"
assert "platforms" in config, "platforms is missing from the configuration"
assert "product_uris" in config, "product_uris is missing from the configuration"

logger = logging.getLogger("builds")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger

try:
  builds.recordNightlyBuilds(config)
  # replaced by ftpscraper.py
  #builds.recordReleaseBuilds(config)
finally:
  logger.info("Done.")

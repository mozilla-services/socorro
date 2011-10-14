#! /usr/bin/env python
"""
startFtpScraper.py is used to get the primary nightly builds from
ftp.mozilla.org, record the build information and provide that
information through the Crash Reporter website.

This script can be run as often as desired, and will automatically backfill.
"""

import logging
import logging.handlers

try:
    import config.ftpscraperconfig as configModule
except ImportError:
    import ftpscraperconfig as configModule

import socorro.cron.ftpscraper as ftpscraper
import socorro.lib.ConfigurationManager as cfgManager
import socorro.lib.util as sutil

config = cfgManager.newConfiguration(configurationModule=configModule,
                                     applicationName='startFtpScraper.py')
assert "databaseHost" in config, "databaseHost missing from config"
assert "databaseName" in config, "databaseName missing from config"
assert "databaseUserName" in config, "databaseUserName missing from config"
assert "databasePassword" in config, "databasePassword missing from config"
assert "base_url" in config, "base_url missing from config"
assert "products" in config, "products missing from config"

logger = logging.getLogger("ftpscraper")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger

try:
    ftpscraper.recordBuilds(config)
finally:
    logger.info("Done.")

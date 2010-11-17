#! /usr/bin/env python
"""
startSignatureProductdims.py is used to document each of the versions 
in which a crash signature is found.  These will be stored in the 
signature_productsdims table.

This script is expected to be run once per day.
"""

import logging
import logging.handlers

try:
  import config.signatureProductdims as configModule
except ImportError:
  import signatureProductdims as configModule

import socorro.cron.signatureProductdims as signatureProductdims
import socorro.lib.ConfigurationManager as configurationManager

config = configurationManager.newConfiguration(configurationModule = configModule, applicationName='startSignatureProductdims.py')
assert "databaseHost" in config, "databaseHost is missing from the configuration"
assert "databaseName" in config, "databaseName is missing from the configuration"
assert "databaseUserName" in config, "databaseUserName is missing from the configuration"
assert "databasePassword" in config, "databasePassword is missing from the configuration"

logger = logging.getLogger("signatureProductdims")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)

config.logger = logger 

try:
  signatureProductdims.populateSignatureProductdims(config)
finally:
  logger.info("Completed startSignatureProductdims.py")

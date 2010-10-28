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
  import config.signatureProductdims as config
except ImportError:
  import signatureProductdims as config

import socorro.cron.signatureProductdims as signatureProductdims
import socorro.lib.ConfigurationManager as configurationManager

config = configurationManager.newConfiguration(configurationModule = config, applicationName='startSignatureProductdims.py')
assert "databaseHost" in config, "databaseHost is missing from the configuration"
assert "databaseName" in config, "databaseName is missing from the configuration"
assert "databaseUserName" in config, "databaseUserName is missing from the configuration"
assert "databasePassword" in config, "databasePassword is missing from the configuration"

logger = logging.getLogger("signatureProductdims")
logger.setLevel(logging.DEBUG)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(config.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(config.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

rotatingFileLog = logging.handlers.RotatingFileHandler(config.logFilePathname, "a", config.logFileMaximumSize, config.logFileMaximumBackupHistory)
rotatingFileLog.setLevel(config.logFileErrorLoggingLevel)
rotatingFileLogFormatter = logging.Formatter(config.logFileLineFormatString)
rotatingFileLog.setFormatter(rotatingFileLogFormatter)
logger.addHandler(rotatingFileLog)

config.logger = logger 
logger.info("current configuration\n%s", str(config))

try:
  signatureProductdims.populateSignatureProductdims(config)
finally:
  logger.info("Completed startSignatureProductdims.py")
  rotatingFileLog.flush()
  rotatingFileLog.close()

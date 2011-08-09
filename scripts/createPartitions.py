#! /usr/bin/env python

import logging
import logging.handlers
import sys
import datetime as dt

try:
  import config.createpartitionsconfig as configModule
except ImportError:
    import createpartitionsconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.schema as schema
import socorro.lib.util as sutil

try:
  config = configurationManager.newConfiguration(configurationModule=configModule, applicationName="startNextPartition")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("nextPartition")
logger.setLevel(logging.DEBUG)

sutil.setupLoggingHandlers(logger, config)
sutil.echoConfig(logger, config)
  
try:
  config["endDate"] = config.startDate + dt.timedelta(config.weeksIntoFuture * 7)
  print 
  schema.createPartitions(config, logger)
finally:
  logger.info("done.")

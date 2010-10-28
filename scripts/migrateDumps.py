#! /usr/bin/env python

import sys
import os
import threading
import logging
import logging.handlers
import datetime as dt
import time

import simplejson as sj

import socorro.lib.threadlib as sthr
import socorro.lib.psycopghelper as spsy
import socorro.lib.processedDumpStorage as spds
import socorro.database.schema as sdbs

#import psycopg2.extras

def moveADump (args):
  theDump, filesystemObject, logger = args
  date_processed = None
  started_datetime = None
  for key, value in theDump.iteritems():
    if type(value) == dt.datetime:
      theDump[key] = "%4d-%02d-%02d %02d:%02d:%02d.%d" % (value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond)
    if key == 'date_processed':
      date_processed = value
    if key == 'started_datetime':
      started_datetime = value
  logger.debug("%s - adding %s to the filesystem", threading.currentThread().getName(), theDump['uuid'])
  try:
    if date_processed.hour == 0 and date_processed.minute == 0 and date_processed.second == 0 and started_datetime is not None:
      date_processed = started_datetime
  except AttributeError:
    date_processed = started_datetime
  try:
    filesystemObject.putDumpToFile(theDump['uuid'], theDump, date_processed)
  except Exception, x:
    logger.error("%s - %s", threading.currentThread().getName(), str(x))

def getResultAsDict (aRowTuple, columnDescription):
  dictResult = {}
  for column, value in zip(columnDescription, aRowTuple):
    dictResult[column[0]] = value
  del dictResult["url"]
  del dictResult["user_id"]
  del dictResult["email"]
  return dictResult

def queueTable (args):
  dateIdentifier, databaseConnectionPool, taskQueue, filesystemObject, logger = args
  connection, cursor = databaseConnectionPool.connectionCursorPair()
  logger.debug("%s -  connected to database - getting dict cursor", threading.currentThread().getName())
  cursor = connection.cursor("%s_cursor" % threading.currentThread().getName().replace('-','_'))
  sql = """select r.*,
                  d.data as dump
           from reports_%s r join dumps_%s d on r.id = d.report_id""" % (dateIdentifier, dateIdentifier)
  logger.info("%s -  executing: %s", threading.currentThread().getName(), sql)
  cursor.execute(sql)
  try:
    result = cursor.fetchmany(100)
    columns = cursor.description
    while result:
      for aDump in result:
        aDumpAsDict = getResultAsDict(aDump, columns)
        logger.debug("%s - queuing %s", threading.currentThread().getName(), aDumpAsDict['uuid'])
        taskQueue.newTask(moveADump, (aDumpAsDict, filesystemObject, logger))
      result = cursor.fetchmany(100)
  except Exception, x:
    logger.critical("%s - DatabaseError: %s", threading.currentThread().getName(), x)
  cursor.close()
  logger.info("%s -  done with database results", threading.currentThread().getName())

def startUp (config, logger):
  databaseConnectionPool = spsy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  logger.debug("%s -  setting up database queue", threading.currentThread().getName())
  databaseQueue = sthr.TaskManager(config.numberOfTablesAtOnce)
  logger.debug("%s -  setting up task queue", threading.currentThread().getName())
  taskQueue = sthr.TaskManager(3, 200)
  logger.debug("%s -  setting up storage", threading.currentThread().getName())
  #filesystemObject = spds.ProcessedDumpStorage(config.processedDumpStoragePath, logger=logger)
  filesystemObject = spds.ProcessedDumpStorage(config.processedDumpStoragePath)
  logger.debug("%s -  starting loop", threading.currentThread().getName())
  for aDatePair in sdbs.mondayPairsIteratorFactory(config.startDate, config.endDate):
    dateIdentifier = "%4d%02d%02d" % (aDatePair[0].year, aDatePair[0].month, aDatePair[0].day)
    logger.info("%s -  queuing dumps_%s", threading.currentThread().getName(), dateIdentifier)
    databaseQueue.newTask(queueTable, (dateIdentifier, databaseConnectionPool, taskQueue, filesystemObject, logger))
  logger.debug("%s -  waiting for database queue to end", threading.currentThread().getName())
  databaseQueue.waitForCompletion()
  logger.debug("%s -  waiting for task queue to end", threading.currentThread().getName())
  taskQueue.waitForCompletion()

if __name__ == "__main__":
  try:
    import config.migratedumpsconfig as config
  except ImportError:
    import migratedumpsconfig as config

  import socorro.lib.ConfigurationManager as configurationManager

  try:
    configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Migrate Dumps 1.0")
  except configurationManager.NotAnOptionError, x:
    print >>sys.stderr, x
    print >>sys.stderr, "for usage, try --help"
    sys.exit()

  logger = logging.getLogger("migrateDumps")
  logger.setLevel(logging.DEBUG)

  stderrLog = logging.StreamHandler()
  stderrLog.setLevel(configurationContext.stderrErrorLoggingLevel)
  stderrLogFormatter = logging.Formatter(configurationContext.stderrLineFormatString)
  stderrLog.setFormatter(stderrLogFormatter)
  logger.addHandler(stderrLog)

  rotatingFileLog = logging.handlers.RotatingFileHandler(configurationContext.logFilePathname, "a", configurationContext.logFileMaximumSize, configurationContext.logFileMaximumBackupHistory)
  rotatingFileLog.setLevel(configurationContext.logFileErrorLoggingLevel)
  rotatingFileLogFormatter = logging.Formatter(configurationContext.logFileLineFormatString)
  rotatingFileLog.setFormatter(rotatingFileLogFormatter)
  logger.addHandler(rotatingFileLog)

  logger.info("current configuration\n%s", str(configurationContext))

  try:
    try:
      startUp(configurationContext, logger)
    except Exception, x:
      logger.critical("%s - This did not end well: %s", threading.currentThread().getName(), x)
  finally:
    logger.info("done.")



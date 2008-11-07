#! /usr/bin/env python

import socorro.database.schema as socorro_schema
import socorro.lib.util as socorro_util
import socorro.lib.psycopghelper as socorro_psy
import socorro.database.postgresql as socorro_pg

import psycopg2.extras


def getOldPartitionList (databaseCursor, tableName):
  return sorted([x for x in socorro_pg.tablesMatchingPattern("%s_part%%" % tableName, databaseCursor)])

def disconnectPartition (databaseCursor, partitionList, masterTableName, logger):
  for anOldPartitionName in partitionList:
    try:
      databaseCursor.execute("SAVEPOINT X; ALTER TABLE %s NO INHERIT %s; RELEASE SAVEPOINT X;" % (anOldPartitionName, masterTableName))
    except:
      databaseCursor.execute("ROLLBACK TO SAVEPOINT X")
      socorro_util.reportExceptionAndContinue(logger)
  databaseCursor.connection.commit()

def reportsTableSpecialHandler(databaseCursor, logger):
  databaseCursor.execute("""ALTER SEQUENCE seq_reports_id OWNED BY reports.id;""")
  databaseCursor.execute("""ALTER TABLE reports ALTER COLUMN id SET DEFAULT nextval('seq_reports_id'::regclass);""")
  databaseCursor.connection.commit()

parititionNameCache = {}
def partitionTableNames(date):
  year, isoWeek = date.isocalendar()[:2]
  try:
    return parititionNameCache[(year, isoWeek)]
  except KeyError:
    suffix = "_%d%02d" % (year, isoWeek)
    partitionNameTriplet = parititionNameCache[(year, isoWeek)] = ("reports%s" % suffix, "dumps%s" % suffix, "frames%s" % suffix)
    return partitionNameTriplet

def migrate (config, logger):

  databaseConnection, databaseCursor = socorro_schema.connectToDatabase(config, logger)

  # get range for new partitions
  logger.info ("getting min max date information from reports")
  minDate, maxDate = socorro_psy.singleRowSql(databaseCursor, """select
                                                                     min(date) as minDate,
                                                                     max(date) as maxDate
                                                                 from reports""")
  weekIteratorGenerator = socorro_schema.iterateBetweenDatesGeneratorCreator(minDate, maxDate)

  # disconnect all old partitions
  logger.info ("disconnect all old partitions")
  logger.debug ("disconnect all old reports partitions")
  oldReportsPartitions = getOldPartitionList(databaseCursor, 'reports')
  disconnectPartition(databaseCursor, oldReportsPartitions, 'reports', logger)
  logger.debug ("disconnect all old dumps partitions")
  oldDumpsPartitions = getOldPartitionList(databaseCursor, 'dumps')
  disconnectPartition(databaseCursor, oldDumpsPartitions, 'dumps', logger)
  logger.debug ("disconnect all old frames partitions")
  oldFramesPartitions = getOldPartitionList(databaseCursor, 'frames')
  disconnectPartition(databaseCursor, oldFramesPartitions, 'frames', logger)
  logger.debug ("disconnect all old modules partitions")
  oldModulesPartitions = getOldPartitionList(databaseCursor, 'modules')
  disconnectPartition(databaseCursor, oldModulesPartitions, 'modules', logger)
  logger.debug ("disconnect all old extensions partitions")
  oldExtensionsPartitions = getOldPartitionList(databaseCursor, 'extensions')
  disconnectPartition(databaseCursor, oldExtensionsPartitions, 'extensions', logger)

  reportsTableSpecialHandler(databaseCursor, logger)

  socorro_schema.updateDatabase(config, logger)
  chattyTrigger = socorro_schema.ChattyParititioningTriggerScript(logger)
  chattyTrigger.updateDefinition(databaseCursor)
  databaseConnection.commit()

  logger.info ("creating new partitions")
  try:
    logger.debug ("creating new reports partitions")
    reportsTable = socorro_schema.ReportsTable(logger=logger)
    reportsTable.createPartitions(databaseCursor, weekIteratorGenerator)
    databaseConnection.commit()
    logger.debug ("creating new dumps partitions")
    dumpsTable = socorro_schema.DumpsTable(logger=logger)
    dumpsTable.createPartitions(databaseCursor, weekIteratorGenerator)
    logger.debug ("creating new frames partitions")
    framesTable = socorro_schema.FramesTable(logger=logger)
    framesTable.createPartitions(databaseCursor, weekIteratorGenerator)
  except:
    socorro_util.reportExceptionAndAbort(logger)

  try:
    logger.info("creating migration database cursors")
    reportsReadingCursor = databaseConnection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    otherReadingCursor = databaseConnection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    writingCursor = databaseConnection.cursor()

    logger.info("looping though old reports partitions")
    for anOldReportsPartition, anOldDumpsPartition, anOldFramesPartition, anOldExtensionsPartition, anOldModulesPartition in zip(oldReportsPartitions, oldDumpsPartitions, oldFramesPartitions, oldExtensionsPartitions, oldModulesPartitions):
      logger.info("  working on %s, %s, %s, %s, %s", anOldReportsPartition, anOldDumpsPartition, anOldFramesPartition, anOldExtensionsPartition, anOldModulesPartition)

      writingCursor.execute ("insert into reports select * from %s" % anOldReportsPartition)
      writingCursor.execute ("""insert into dumps
                                    select
                                        dp.*,
                                        rp.date
                                    from
                                        %s dp join %s rp
                                            on dp.report_id = rp.id""" % (anOldDumpsPartition, anOldReportsPartition))
      writingCursor.execute ("""insert into frames
                                    select
                                        dp.*,
                                        rp.date
                                    from
                                        %s dp join %s rp
                                            on dp.report_id = rp.id""" % (anOldFramesPartition, anOldReportsPartition))
      writingCursor.execute("drop table %s cascade" % anOldDumpsPartition)
      writingCursor.execute("drop table %s cascade" % anOldFramesPartition)
      writingCursor.execute("drop table %s cascade" % anOldModulesPartition)
      writingCursor.execute("drop table %s cascade" % anOldExtensionsPartition)
      writingCursor.execute("drop table %s cascade" % anOldReportsPartition)
      writingCursor.connection.commit()
    writingCursor.execute("drop table modules")
    writingCursor.execute("drop function if exists create_partition_rules (partition integer)")
    writingCursor.execute("drop function drop_partition_rules ()")
    writingCursor.execute("drop function get_latest_partition ()")
    writingCursor.execute("drop function lock_for_changes ()")
    writingCursor.execute("drop function make_partition ()")
    writingCursor.execute("drop function subst (str text, vals text[])")
    writingCursor.connection.commit()
    trigger = socorro_schema.ParititioningTriggerScript(logger)
    trigger.updateDefinition(writingCursor)
    databaseConnection.commit()
  except:
    socorro_util.reportExceptionAndAbort(logger)

import sys
import logging
import logging.handlers

try:
  import config.setupdatabase as config
except ImportError:
  import setupconfig as config

import socorro.database.schema as socorro_schema
import socorro.lib.ConfigurationManager as configurationManager

try:
  configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Socorro Database Setup 1.0")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit()

logger = logging.getLogger("setupDatabase")
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
  migrate(configurationContext, logger)
finally:
  logger.info("done.")



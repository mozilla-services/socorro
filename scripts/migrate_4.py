#! /usr/bin/env python

import socorro.database.schema as socorro_schema
import socorro.lib.util as socorro_util
import socorro.lib.psycopghelper as socorro_psy
import socorro.database.postgresql as socorro_pg

import psycopg2.extras

import datetime as dt


def getOldPartitionList (databaseCursor, tableName):
  return sorted([x for x in socorro_pg.tablesMatchingPattern("%s_part%%%%" % tableName, databaseCursor)])

def disconnectPartition (databaseCursor, partitionList, masterTableName, logger):
  for anOldPartitionName in partitionList:
    try:
      databaseCursor.execute("SAVEPOINT X; ALTER TABLE %s NO INHERIT %s; RELEASE SAVEPOINT X;" % (anOldPartitionName, masterTableName))
    except:
      databaseCursor.execute("ROLLBACK TO SAVEPOINT X")
      socorro_util.reportExceptionAndContinue(logger)
  databaseCursor.connection.commit()

def reportsTableConnectExistingSequence(databaseCursor, logger):
  databaseCursor.execute("""ALTER SEQUENCE seq_reports_id OWNED BY reports.id;""")
  databaseCursor.execute("""ALTER TABLE reports ALTER COLUMN id SET DEFAULT nextval('seq_reports_id'::regclass);""")
  databaseCursor.connection.commit()

def migrate (config, logger):

  oneWeek = dt.timedelta(7)

  databaseConnection, databaseCursor = socorro_schema.connectToDatabase(config, logger)

  #logger.info ("create insert trigger")
  #try:
    #databaseCursor.execute("CREATE LANGUAGE plpythonu")
  #except:
    #databaseConnection.rollback()
  #socorro_schema.ParititioningTriggerScript(logger=logger, userName=config.databaseUserName).create(databaseCursor)
  #databaseConnection.commit()

  #socorro_schema.JobsTable(logger=logger).updateDefinition(databaseCursor)
  #databaseConnection.commit()

  # get range for new partitions
  #logger.info ("getting min max date information from reports")
  #minDate, maxDate = socorro_psy.singleRowSql(databaseCursor, """select
                                                                     #min(date_processed) as minDate,
                                                                     #max(date_processed) as maxDate
                                                                 #from reports""")
  #weekIteratorGenerator = socorro_schema.iterateBetweenDatesGeneratorCreator(minDate, maxDate)

  # delete everything older than 120 days
  #oneHundredTwentyDaysEarlier = maxDate - dt.timedelta(120)
  #logger.info("deleting stuff older than 120 days of the max date: %s - %s", maxDate, oneHundredTwentyDaysEarlier)
  #databaseCursor.execute("delete from reports where date_processed < timestamp with time zone '%4d-%02d-%02d'" % (oneHundredTwentyDaysEarlier.year,
  #                                                                                                                oneHundredTwentyDaysEarlier.month,
  #                                                                                                                oneHundredTwentyDaysEarlier.day))
  #databaseConnection.commit()

  masterTableClassList = [ socorro_schema.ExtensionsTable, socorro_schema.FramesTable, socorro_schema.DumpsTable, socorro_schema.ReportsTable ]
  masterTableList = [x(logger=logger, userName=config.databaseUserName) for x in masterTableClassList]

  #logger.info ("disconnect all old partitions")
  oldPartitionLists = {}
  for aTable in masterTableList:
    logger.info("  %s", aTable.name)
    oldPartitionLists[aTable.name] = oldPartitionList = getOldPartitionList(databaseCursor, aTable.name)
    #disconnectPartition(databaseCursor, oldPartitionList, aTable.name, logger)

  #logger.info ("drop and recreate all old master tables")
  #for aTable in masterTableList:
    #logger.info("  %s", aTable.name)
    #aTable.drop(databaseCursor)
    #aTable.create(databaseCursor)
  #databaseConnection.commit()

  logger.info ("spill old partitions into new partitions")
  for oldReportsPartitionName, oldextensionsPartitionName, oldFramesPartitionName, oldDumpsPartitionName in zip(oldPartitionLists["reports"], oldPartitionLists["extensions"], oldPartitionLists["frames"], oldPartitionLists["dumps"]):
    logger.info("  %s, %s, %s, %s", oldReportsPartitionName, oldextensionsPartitionName, oldFramesPartitionName, oldDumpsPartitionName)
    oldPartitionNames = {"reports": oldReportsPartitionName,
                         "extensions": oldextensionsPartitionName,
                         "frames": oldFramesPartitionName,
                         "dumps": oldDumpsPartitionName
                        }

    logger.info("adding some handy indexes")
    try:
      databaseCursor.execute("create index %(reports)s_date_processed_key on %(reports)s (date_processed)" % oldPartitionNames)
    except:
      databaseConnection.rollback()
    databaseCursor.execute("create index %(extensions)s_report_id_key on %(extensions)s (report_id)" % oldPartitionNames)
    databaseCursor.execute("create index %(frames)s_report_id_key on %(frames)s (report_id)" % oldPartitionNames)
    databaseCursor.execute("create index %(dumps)s_report_id_key on %(dumps)s (report_id)" % oldPartitionNames)

    partitionUniqueId = oldReportsPartitionName[len("reports_"):]
    minDate, maxDate = socorro_psy.singleRowSql(databaseCursor, """select
                                                                     min(date_processed) as minDate,
                                                                     max(date_processed) as maxDate
                                                                   from %s""" % oldReportsPartitionName)
    if minDate is None or maxDate is None:
      logger.info("this table is empty - delete corresponding table partitions")
      for aPartitionName in [x.name for x in masterTableList]:
        try:
          partitionName = "%s_%s" % (aPartitionName, partitionUniqueId)
          databaseCursor.execute("drop table %s cascade" % partitionName)
          databaseCursor.connection.commit()
        except Exception, x:
          logger.info(str(x))
          logger.info("%s doesn't exist - can't drop it", partitionName)
          databaseCursor.connection.rollback()
      continue

    dateRangeIterator = socorro_schema.iterateBetweenDatesGeneratorCreator(minDate, maxDate)
    #databaseConnection, databaseCursor = socorro_schema.connectToDatabase(config, logger)
    def wrapperIter():
      for x in list(dateRangeIterator())[::-1][:4]:
        yield x
    for aPartitionedTable in masterTableList[::-1]:
      logger.info("  %s", aPartitionedTable.name)
      aPartitionedTable.createPartitions(databaseCursor, wrapperIter)
    for minPartitionDate, maxPartitionDate in wrapperIter():
      newPartitionNames = {}
      for aPartitionedTable in masterTableList:
        newPartitionNames[aPartitionedTable.name] = aPartitionedTable.partitionCreationParameters((minPartitionDate, maxPartitionDate))["partitionName"]
      sqlParameters = { "startDate":str(minPartitionDate)[:10],
                        "endDate":str(maxPartitionDate)[:10],
                        "newPartitionName":newPartitionNames["reports"],
                        "oldPartitionName":oldPartitionNames["reports"],
                        "oldReportsPartition":oldPartitionNames["reports"],
                        "newReportsPartition":newPartitionNames["reports"]
                      }
      singleDayTuples = [(str(minPartitionDate + dt.timedelta(x))[:10], str(minPartitionDate + dt.timedelta(x + 1))[:10]) for x in range(7)]
      try:
        databaseCursor.execute("""insert into %(newPartitionName)s
                                            (id, uuid, client_crash_date, date_processed, product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, user_comments, started_datetime, completed_datetime, success, truncated, processor_notes, app_notes, distributor, distributor_version)
                                    (select
                                             id, uuid, date,              date_processed, product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, comments,      starteddatetime,  completeddatetime,  success, truncated, message,         NULL,      NULL,        NULL
                                     from %(oldPartitionName)s
                                     where TIMESTAMP without time zone '%(startDate)s' <= date_processed and date_processed < TIMESTAMP without time zone '%(endDate)s')""" % sqlParameters)
        databaseConnection.commit()
      except:
        databaseConnection.rollback()
      sqlParameters["newPartitionName"] = newPartitionNames["extensions"]
      sqlParameters["oldPartitionName"] = oldPartitionNames["extensions"]
      #logger.info("#### %s / %s", str(oldPartitionNames), sqlParameters["oldPartitionName"])
      try:
        databaseCursor.execute("""insert into %(newPartitionName)s
                                    (select
                                       e.report_id,
                                       r.date_processed,
                                       e.extension_key,
                                       e.extension_id,
                                       e.extension_version
                                     from
                                       %(oldPartitionName)s e join %(newReportsPartition)s r on e.report_id = r.id)
                              """ % sqlParameters)
        databaseConnection.commit()
      except:
        databaseConnection.rollback()
      sqlParameters["newPartitionName"] = newPartitionNames["frames"]
      sqlParameters["oldPartitionName"] = oldPartitionNames["frames"]
      for lowDay, highDay in singleDayTuples:
        sqlParameters["lowDay"] = lowDay
        sqlParameters["highDay"] = highDay
        try:
          databaseCursor.execute("""insert into %(newPartitionName)s
                                      (select
                                         f.report_id,
                                         r.date_processed,
                                         f.frame_num,
                                         f.signature
                                       from
                                         %(oldPartitionName)s f join %(newReportsPartition)s r on f.report_id = r.id
                                       where
                                         TIMESTAMP without time zone '%(lowDay)s' <= r.date_processed and r.date_processed < TIMESTAMP without time zone '%(highDay)s')""" % sqlParameters)
          databaseConnection.commit()
        except Exception, x:
          logger.error("SQL failed: %s", str(x))
          databaseConnection.rollback()
      sqlParameters["newPartitionName"] = newPartitionNames["dumps"]
      sqlParameters["oldPartitionName"] = oldPartitionNames["dumps"]
      for lowDay, highDay in singleDayTuples:
        sqlParameters["lowDay"] = lowDay
        sqlParameters["highDay"] = highDay
        try:
          databaseCursor.execute("""insert into %(newPartitionName)s
                                      (select
                                         d.report_id,
                                         r.date_processed,
                                         d.data
                                       from
                                         %(oldPartitionName)s d join %(newReportsPartition)s r on d.report_id = r.id
                                       where
                                         TIMESTAMP without time zone '%(lowDay)s' <= r.date_processed and r.date_processed < TIMESTAMP without time zone '%(highDay)s')""" % sqlParameters)
          databaseConnection.commit()
        except Exception, x:
          logger.error("SQL failed: %s", str(x))
          databaseConnection.rollback()
      databaseCursor.execute("""delete from %(oldReportsPartition)s
                                  where
                                     TIMESTAMP without time zone '%(startDate)s' <= date_processed and date_processed < TIMESTAMP without time zone '%(endDate)s'
                                  """ % sqlParameters)

    logger.info("Now take the rest of the original partition as a big steaming lump")

    minDate, maxDate = socorro_psy.singleRowSql(databaseCursor, """select
                                                               min(date_processed) as minDate,
                                                               max(date_processed) as maxDate
                                                             from %s""" % oldReportsPartitionName)

    if minDate is None or maxDate is None:
      logger.info("There's nothing left in %s - deleting tables", oldReportsPartitionName)
      for aPartitionName in [x.name for x in masterTableList]:
        try:
          partitionName = "%s_%s" % (aPartitionName, partitionUniqueId)
          databaseCursor.execute("drop table %s cascade" % partitionName)
          databaseCursor.connection.commit()
        except Exception, x:
          logger.info(str(x))
          logger.info("%s doesn't exist - can't drop it", partitionName)
          databaseCursor.connection.rollback()
      continue

    mondayBeforeMaxDate = maxDate - dt.timedelta(maxDate.weekday())
    partitionNameDate = "%4d%02d%02d" % (mondayBeforeMaxDate.year, mondayBeforeMaxDate.month, mondayBeforeMaxDate.day)
    mondayAfterMaxDate = mondayBeforeMaxDate + oneWeek
    newReportsPartitionName = "reports_%s" % partitionNameDate
    logger.info("rename %s to %s", oldReportsPartitionName, newReportsPartitionName)
    databaseCursor.execute("alter table %s rename to %s" % (oldReportsPartitionName, newReportsPartitionName))

    logger.info("add new columns to %s", newReportsPartitionName)
    columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(newReportsPartitionName, databaseCursor)
    if 'client_crash_date' not in columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE %s RENAME COLUMN date TO client_crash_date""" % newReportsPartitionName)
    if 'started_datetime' not in columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE %s RENAME COLUMN starteddatetime TO started_datetime""" % newReportsPartitionName)
    if 'completed_datetime' not in columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE %s RENAME COLUMN completeddatetime TO completed_datetime""" % newReportsPartitionName)
    if 'user_comments' not in columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE %s RENAME COLUMN comments TO user_comments""" % newReportsPartitionName)
      databaseCursor.execute("""ALTER TABLE %s ALTER COLUMN user_comments TYPE  character varying(1024)""" % newReportsPartitionName)
    if 'app_notes' not in columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE %s ADD COLUMN app_notes character varying(1024)""" % newReportsPartitionName)
    if 'distributor' not in columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE %s ADD COLUMN distributor character varying(20)""" % newReportsPartitionName)
    if 'distributor_version' not in columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE %s ADD COLUMN distributor_version character varying(20)""" % newReportsPartitionName)
    databaseCursor.execute("""ALTER TABLE %s rename column message to processor_notes""" % newReportsPartitionName)

    logger.info("replace & update indexes for %s", newReportsPartitionName)
    reportsParitionIndexList = socorro_pg.indexesForTable(newReportsPartitionName, databaseCursor)
    if "reports_part1_pkey" in reportsParitionIndexList:
      databaseCursor.execute("ALTER INDEX reports_part1_pkey RENAME TO %s_pkey" % newReportsPartitionName)
    if "reports_part1_uuid_key" in reportsParitionIndexList:
      databaseCursor.execute("ALTER INDEX reports_part1_uuid_key RENAME TO %s_uuid_key" % newReportsPartitionName)
    if "idx_reports_part1_date" in reportsParitionIndexList:
      databaseCursor.execute("ALTER INDEX idx_reports_part1_date RENAME TO %s_date_key" % newReportsPartitionName)
    #if "reports_part1_date_processed_key" in reportsParitionIndexList:
    #  databaseCursor.execute("ALTER INDEX reports_part1_date_processed_key RENAME TO %s_date_processed_key" % newReportsPartitionName)
    databaseCursor.execute("CREATE INDEX %s_signature_key ON %s (signature)" % (newReportsPartitionName, newReportsPartitionName))
    databaseCursor.execute("CREATE INDEX %s_url_key ON %s (url)" % (newReportsPartitionName, newReportsPartitionName))
    databaseCursor.execute("CREATE INDEX %s_signature_date_key ON %s (signature, date_processed)" % (newReportsPartitionName, newReportsPartitionName))

    logger.info("adjust constraints for %s", newReportsPartitionName)
    for constraintName, constraintType in socorro_pg.constraintsAndTypeForTable(newReportsPartitionName, databaseCursor):
      if constraintType == 'c':
        databaseCursor.execute("alter table %s drop constraint %s" % (newReportsPartitionName, constraintName))
    startDate = "%4d-%02d-%02d" % (minDate.year, minDate.month, minDate.day)
    endDate = "%4d-%02d-%02d" % (mondayAfterMaxDate.year, mondayAfterMaxDate.month, mondayAfterMaxDate.day)
    databaseCursor.execute("alter table %s add constraint %s_date_check CHECK (TIMESTAMP without time zone '%s' <= date_processed and date_processed < TIMESTAMP without time zone '%s')" % (newReportsPartitionName, newReportsPartitionName, startDate, endDate))
    logger.info("reconnect %s to report master", newReportsPartitionName)
    databaseCursor.execute("alter table %s inherit reports" % newReportsPartitionName)
    databaseCursor.connection.commit()

    # rename partitions
    for aMasterTableName in ("dumps", "frames", "extensions"):
      oldPartitionName = "%s_%s" % (aMasterTableName, partitionUniqueId)
      newPartitionName = "%s_%s" % (aMasterTableName, partitionNameDate)
      logger.info("renaming %s to %s", oldPartitionName, newPartitionName)
      try:
        databaseCursor.execute("alter table %s rename to %s" % (oldPartitionName, newPartitionName))
      except:
        logger.info("%s did not exist - skipping", oldPartitionName)
        databaseCursor.connection.rollback()
        continue

      logger.info("adding date_processed column to %s", newPartitionName)
      databaseCursor.execute("alter table %s add column date_processed timestamp without time zone" % newPartitionName)
      databaseCursor.execute("""update %s
                                    set date_processed = (select
                                                    date_processed
                                                from %s
                                                where %s.report_id = %s.id)""" % (newPartitionName, newReportsPartitionName, newPartitionName, newReportsPartitionName))

      logger.info("replace & update indexes for %s partition", newPartitionName)
      indexList = socorro_pg.indexesForTable(newPartitionName, databaseCursor)
      if "%s_pkey" % oldPartitionName in indexList:
        databaseCursor.execute("alter index %s_pkey rename to %s_pkey" % (oldPartitionName, newPartitionName))

      logger.info("adjust constraints for %s partition", newPartitionName)
      for constraintName, constraintType in socorro_pg.constraintsAndTypeForTable(newPartitionName, databaseCursor):
        print constraintName, constraintType
        if constraintType in 'cf':
          databaseCursor.execute("alter table %s drop constraint %s" % (newPartitionName, constraintName))
      databaseCursor.execute("alter table %s add constraint %s_date_check CHECK (TIMESTAMP without time zone '%s' <= date_processed and date_processed < TIMESTAMP without time zone '%s')" % (newPartitionName, newPartitionName, startDate, endDate))
      databaseCursor.execute("alter table %s add constraint %s_report_id_fkey foreign key (report_id) references %s (id) on delete cascade" % (newPartitionName, newPartitionName, newReportsPartitionName))

      logger.info("reconnect %s partition to master", newPartitionName)
      databaseCursor.execute("alter table %s inherit %s" % (newPartitionName, aMasterTableName))
      databaseCursor.connection.commit()
    logger.info("end inner loop")
  logger.info("end outer loop")
  try:
    logger.info("dropping table 'modules' and its children")
    databaseCursor.execute("drop table modules cascade")
    databaseCursor.connection.commit()
  except:
    databaseCursor.connection.rollback()
  try:
    logger.info("dropping function create_partition_rules")
    databaseCursor.execute("drop function create_partition_rules (partition integer)")
    databaseCursor.connection.commit()
  except:
    databaseCursor.connection.rollback()
  try:
    logger.info("dropping function drop_partition_rules")
    databaseCursor.execute("drop function drop_partition_rules()")
    databaseCursor.connection.commit()
  except:
    databaseCursor.connection.rollback()
  try:
    logger.info("dropping function  get_latest_partition()")
    databaseCursor.execute("drop function get_latest_partition()")
    databaseCursor.connection.commit()
  except:
    databaseCursor.connection.rollback()
  try:
    logger.info("dropping function  lock_for_changes()")
    databaseCursor.execute("drop function lock_for_changes()")
    databaseCursor.connection.commit()
  except:
    databaseCursor.connection.rollback()
  try:
    logger.info("dropping function  make_partition()")
    databaseCursor.execute("drop function make_partition()")
    databaseCursor.connection.commit()
  except:
    databaseCursor.connection.rollback()
  try:
    logger.info("dropping function  subst(str text, vals text[])")
    databaseCursor.execute("drop function subst(str text, vals text[])")
    databaseCursor.connection.commit()
  except:
    databaseCursor.connection.rollback()

import sys
import logging
import logging.handlers

try:
  import config.setupdatabaseconfig as config
except ImportError:
  import setupdatabaseconfig as config

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



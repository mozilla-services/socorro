#! /usr/bin/env python

import logging
import logging.handlers
import re
import sys
import time

import socorro.lib.ConfigurationManager as cm

from config.commonconfig import databaseHost
from config.commonconfig import databaseName
from config.commonconfig import databaseUserName
from config.commonconfig import databasePassword

import config.commonconfig as config

import psycopg2

import socorro.lib.util as lib_util
import socorro.cron.util as cron_util
import socorro.database.cachedIdAccess as socorro_cia
import socorro.database.postgresql as db_pgsql



import socorro.lib.ConfigurationManager as configurationManager

all_tables_sql = """
  SELECT table_name FROM information_schema.tables
  WHERE table_schema='public' AND
        table_type='BASE TABLE' AND
        table_name LIKE 'reports_%'
  ORDER BY table_name"""

migrate_process_type_sql = """
  UPDATE %s SET process_type = 'plugin'
  FROM %s
  WHERE %s.process_type IS NULL AND %s.report_id = %s.id """

def migrate_process_type_params(reports, plugins_reports):
  """ Makes a tuple suitable for prepared statment """
  return (reports, plugins_reports, reports, plugins_reports, reports)

def main():
  try:
      logger = setupLog()
      configContext = setupConfig()
      logger.info("current configuration\n%s", str(configContext))
      conn = None
      try:
        testConfig(configContext)
        databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
        # Be sure self.connection is closed before you quit!
        conn = psycopg2.connect(databaseDSN)
        cursor = conn.cursor()
        cursor.execute(all_tables_sql)
        tables = cursor.fetchall()
        for reports in tables:
          logger.info("Processing %s" % reports[0])
          plugins_reports = "plugins_%s" % reports[0]
          params = migrate_process_type_params(reports[0], plugins_reports)
          try:
            cursor.execute(migrate_process_type_sql % params)
            logger.info("%d rows updated" % cursor.rowcount)
            conn.commit()
          except psycopg2.ProgrammingError, x:              
            logging.warn("Skipping %s as %s doesn't exist" % (reports[0], plugins_reports))
            conn.rollback()
        conn.close()
      except (psycopg2.OperationalError, AssertionError),x:
        lib_util.reportExceptionAndAbort(logger)
      #TODO finally close
      
      #cursor.execute(sql,startEndData)
  finally:
    logger.info("done.")

def setupLog():
  logger = logging.getLogger("migrateProcessType")
  logger.setLevel(10)

  stderrLog = logging.StreamHandler()
  stderrLog.setLevel(10)
  stderrLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  stderrLog.setFormatter(stderrLogFormatter)
  logger.addHandler(stderrLog)
  return logger

def setupConfig():
  try:
    return configurationManager.newConfiguration(configurationModule=config, applicationName="Migrate Process Type")
  except configurationManager.NotAnOptionError, x:
    print >>sys.stderr, x
    print >>sys.stderr, "for usage, try --help"
    sys.exit(1)
    
def testConfig(configContext):
  assert "databaseHost" in configContext, "databaseHost is missing from the configuration"
  assert "databaseName" in configContext, "databaseName is missing from the configuration"
  assert "databaseUserName" in configContext, "databaseUserName is missing from the configuration"
  assert "databasePassword" in configContext, "databasePassword is missing from the configuration"

if __name__ == "__main__":
  main()

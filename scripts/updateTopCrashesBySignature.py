#! /usr/bin/env python

import logging
import logging.handlers
import math
import sys
import time

import psycopg2 as psy

import socorro.lib.util as lib_util
import socorro.cron.util as cron_util
import socorro.database.database as db

import socorro.lib.ConfigurationManager as configurationManager

from config.commonconfig import databaseHost
from config.commonconfig import databasePort
from config.commonconfig import databaseName
from config.commonconfig import databaseUserName
from config.commonconfig import databasePassword

try:
  databaseDSN = "host=%s dbname=%s user=%s password=%s" % (databaseHost.default, databaseName.default, databaseUserName.default, databasePassword.default)
  connection = psy.connect(databaseDSN)
except Exception, x:
  print x

logFilePathname = './updateTopCrashBySignature.log'
logFileMaximumSize = 5000000
logFileMaximumBackupHistory = 50
logFileLineFormatString = '%(asctime)s %(levelname)s - %(message)s'
logFileErrorLoggingLevel = 20
stderrLineFormatString = '%(asctime)s %(levelname)s - %(message)s'
stderrErrorLoggingLevel = 20

logger = logging.getLogger("updateTopCrashBySignature")
logger.setLevel(stderrErrorLoggingLevel)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

rotatingFileLog = logging.handlers.RotatingFileHandler(logFilePathname, "a", logFileMaximumSize, logFileMaximumBackupHistory)
rotatingFileLog.setLevel(logFileErrorLoggingLevel)
rotatingFileLogFormatter = logging.Formatter(logFileLineFormatString)
rotatingFileLog.setFormatter(rotatingFileLogFormatter)
logger.addHandler(rotatingFileLog)

logger.info("starting top_crashes_by_signature update")

try:
  cursor = connection.cursor()
  sql1 = """SELECT COUNT(tcbs.id) as count
             FROM top_crashes_by_signature tcbs
             INNER JOIN productdims p ON tcbs.productdims_id = p.id
             WHERE tcbs.window_end >= (NOW() - CAST('2 weeks' as INTERVAL))
        """
  tcbs_count = db.singleValueSql(cursor, sql1)
  logger.info("Number of rows found in sql1: %d" % (tcbs_count))
  
  limit = 1000
  pages = math.ceil(tcbs_count/limit)
  logger.info("Pulling %d pages of queries..." % (pages))

  for i in xrange (0, pages):
    sql2 = """SELECT tcbs.id, tcbs.signature, tcbs.window_end, tcbs.productdims_id, tcbs.osdims_id
             FROM top_crashes_by_signature tcbs 
             INNER JOIN productdims p ON tcbs.productdims_id = p.id
             WHERE tcbs.window_end >= (NOW() - CAST('2 weeks' as INTERVAL))
             ORDER BY tcbs.id DESC
             LIMIT %d OFFSET %d
    """ % (limit, (i*limit))

    i += 1
    logger.info("RESULT SET %d" % (i))
    try:
      cursor.execute(sql2)
      results = cursor.fetchall()
      for result in results:
        tcbs_id = result[0]
        tcbs_sig = result[1]
        tcbs_date = result[2]
        tcbs_pid = result[3]
        tcbs_oid = result[4]
        sql3 = """SELECT
                      count(r.id), r.signature, p.id AS productdims_id, o.id AS osdims_id,
                      SUM (CASE WHEN r.hangid IS NULL THEN 0 ELSE 1 END) AS hang_count,
                      SUM (CASE WHEN r.process_type IS NULL THEN 0 ELSE 1 END) AS plugin_count
                  FROM productdims p
                  JOIN reports r 
                      ON r.product = p.product
                      AND r.version = p.version
                      AND r.date_processed BETWEEN TIMESTAMP '%s' - CAST('1 hour' AS INTERVAL) AND TIMESTAMP '%s' 
                  JOIN osdims o ON r.os_name = o.os_name 
                      AND r.os_version = o.os_version
                  WHERE r.signature = '%s'
                  AND p.id = %d
                  AND o.id = %d
                  GROUP BY r.signature, productdims_id, osdims_id
        """ % (tcbs_date, tcbs_date, tcbs_sig, tcbs_pid, tcbs_oid)
        try: 
          tcbs_result = db.singleRowSql(cursor, sql3)
          hang_count = tcbs_result[4]
          plugin_count = tcbs_result[5]

          update = 0
          if plugin_count > 0:
            update = 1
          if hang_count > 0:
            update = 1 

          if update == 1:
            try:
              sql4 = """UPDATE top_crashes_by_signature
                      SET hang_count = %d, plugin_count = %d
                      WHERE id = %d
              """ % (hang_count, plugin_count, tcbs_id)
              cursor.execute(sql4)
              cursor.connection.commit()
              logger.info("SUCCESS sql4 updated #%d with hang_count %d and plugin_count %d" % (tcbs_id, hang_count, plugin_count))
            except Exception, x:
              logger.info("FAIL sql4; unable to update record associated with tcbs.id %d. %s" % (x))
              cursor.connection.rollback()
          
        except Exception, x:
          logger.debug("Exception %s." % x)
    
    except Exception, x:
      logger.debug("Exception %s." % x)    
    
finally:
  logger.info("Done.")
  rotatingFileLog.flush()
  rotatingFileLog.close()
  connection.close()

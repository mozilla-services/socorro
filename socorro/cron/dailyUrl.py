#!/usr/bin/python

import logging
import datetime as dt
import gzip
import csv
import time
import os.path

logger = logging.getLogger("dailyUrlDump")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util

#-----------------------------------------------------------------------------------------------------------------
def dailyUrlDump(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    try:
      databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()

      now = config.day
      nowAsString = "%4d-%02d-%02d" % now.timetuple()[:3]
      yesterday = now - dt.timedelta(1)
      yesterdayAsString = "%4d-%02d-%02d" % yesterday.timetuple()[:3]
      outputFileName = "%4d%02d%02d-crashdata.csv.gz" % now.timetuple()[:3]
      outputPathName = os.path.join(config.outputPath, outputFileName)

      if config.product == '':
        productPhrase = ''
      else:
        productPhrase = "and r.product = '%s'" % config.product

      if config.version == '':
        versionPhrase = ''
      else:
        versionPhrase = "and r.version = '%s'" % config.version

      sql = """
      select
        r.signature,
        r.url,
        'http://crash-stats.mozilla.com/report/index/' || r.uuid as uuid_url,
        to_char(r.client_crash_date,'YYYYMMDDHH24MI') as client_crash_date,
        to_char(r.date_processed,'YYYYMMDDHH24MI') as date_processed,
        r.last_crash,
        r.product,
        r.version,
        r.build,
        b.branch,
        r.os_name,
        r.os_version,
        r.cpu_name,
        r.address,
        array(select ba.bug_id from bug_associations ba where ba.signature = r.signature) as bug_list,
        r.user_comments
      from
        reports r left join branches b on r.product = b.product and r.version = b.version
      where
        '%s' >= date_processed and date_processed > '%s'
        %s %s
      order by
        r.date_processed
      """ % (nowAsString, yesterdayAsString, productPhrase, versionPhrase)

      try:
        gzippedOutputFile = gzip.open(outputPathName, "w")
        csvFormatter = csv.writer(gzippedOutputFile, delimiter='\t', lineterminator='\n')
        columnHeadersAreNotWritten = True
        for aCrash in psy.execute(databaseCursor, sql):
          if columnHeadersAreNotWritten:
            columnHeadersAreNotWritten = False
            csvFormatter.writerow([x[0] for x in databaseCursor.description])
          aCrashAsAList = []
          for i, x in enumerate(aCrash):
            if x is None:
              aCrashAsAList.append(r'\N')
              continue
            if i == 14:
              aCrashAsAList.append(','.join(str(bugid) for bugid in x))
              continue
            if type(x) == str:
              x = x.strip().replace('\r','').replace('\n',' | ')
            aCrashAsAList.append(x)
          csvFormatter.writerow(aCrashAsAList)
      finally:
        gzippedOutputFile.close()

    finally:
      databaseConnectionPool.cleanup()
  except:
    util.reportExceptionAndContinue(logger)


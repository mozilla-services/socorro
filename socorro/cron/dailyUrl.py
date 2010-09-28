###!/usr/bin/python

import logging
import copy
import datetime as dt
import gzip
import csv
import simplejson
import time
import os.path

logger = logging.getLogger("dailyUrlDump")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util
from socorro.database.cachedIdAccess import IdCache

#-----------------------------------------------------------------------------------------------------------------
def dailyUrlDump(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try: # outer try/except: level 0
    try: # mid try/finally: level 1
      databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()

      now = config.day + dt.timedelta(1)
      nowAsString = "%4d-%02d-%02d" % now.timetuple()[:3]
      yesterday = config.day
      yesterdayAsString = "%4d-%02d-%02d" % yesterday.timetuple()[:3]
      outputFileName = "%4d%02d%02d-crashdata.csv.gz" % config.day.timetuple()[:3]
      publicOutputFileName = "%4d%02d%02d-pub-crashdata.csv.gz" % config.day.timetuple()[:3]
      outputPathName = os.path.join(config.outputPath, outputFileName)
      publicOutputPathName = None
      publicOutputDirectory = config.get('publicOutputPath')
      if publicOutputDirectory:
        publicOutputPathName = os.path.join(publicOutputDirectory,publicOutputFileName)
      logger.debug("config.day = %s; now = %s; yesterday = %s", config.day, now, yesterday)
      productPhrase = ''
      try:
        if config.product != '':
          productPhrase = "and r.product = '%s'" % config.product
      except:
        pass

      versionPhrase = ''
      try:
        if config.version != '':
          versionPhrase = "and r.version = '%s'" % config.version
      except:
        pass

      # -- N : array index. SQL's idea of the index is one greater
      sql = """
      select
        r.signature,  -- 0
        r.url,        -- 1
        'http://crash-stats.mozilla.com/report/index/' || r.uuid as uuid_url, -- 2
        to_char(r.client_crash_date,'YYYYMMDDHH24MI') as client_crash_date,   -- 3
        to_char(r.date_processed,'YYYYMMDDHH24MI') as date_processed,         -- 4
        r.last_crash, -- 5
        r.product,    -- 6
        r.version,    -- 7
        r.build,      -- 8
        pd.branch,    -- 9
        r.os_name,    --10
        r.os_version, --11
        r.cpu_name || ' | ' || r.cpu_info,   --12
        r.address,    --13
        array(select ba.bug_id from bug_associations ba where ba.signature = r.signature) as bug_list, --14
        r.user_comments, --15
        r.uptime as uptime_seconds, --16
        case when (r.email is NULL OR r.email='') then '' else r.email end as email, --17
        (select sum(adu_count) from raw_adu adu
           where adu.date = '%(nowAsString)s'
             and pd.product = adu.product_name and pd.version = adu.product_version
             and substring(r.os_name from 1 for 3) = substring(adu.product_os_platform from 1 for 3)
             and r.os_version LIKE '%%'||adu.product_os_version||'%%') as adu_count, --18
        r.topmost_filenames, --19
        case when (r.addons_checked is NULL) then '[unknown]'when (r.addons_checked) then 'checked' else 'not' end as addons_checked, --20
        r.flash_version, --21
        r.hangid, --22
        r.reason, --23
        r.process_type, --24
        r.app_notes --25
      from
        reports r left join productdims pd on r.product = pd.product and r.version = pd.version
      where
        '%(yesterdayAsString)s' <= r.date_processed and r.date_processed < '%(nowAsString)s'
        %(productPhrase)s %(versionPhrase)s
      order by 5 -- r.date_processed, munged
      """ % {'nowAsString':nowAsString, 'yesterdayAsString':yesterdayAsString, 'productPhrase':productPhrase, 'versionPhrase':versionPhrase}
      logger.debug("SQL is%s",sql)
      gzippedOutputFile = None
      gzippedPublicOutputFile = None
      try: # inner try/finally level 2: write gzipped files
        gzippedOutputFile = gzip.open(outputPathName, "w")
        csvFormatter = csv.writer(gzippedOutputFile, delimiter='\t', lineterminator='\n')
        csvPublicFormatter = None
        if publicOutputPathName:
          gzippedPublicOutputFile = gzip.open(publicOutputPathName, "w")
          csvPublicFormatter = csv.writer(gzippedPublicOutputFile, delimiter='\t', lineterminator='\n')
        else:
          logger.info("Will not create External (bowdlerized) gzip file")

        columnHeadersAreNotYetWritten = True
        idCache = IdCache(databaseCursor)
        for aCrash in psy.execute(databaseCursor, sql):
          if columnHeadersAreNotYetWritten:
            writeRowToInternalAndExternalFiles(csvFormatter,csvPublicFormatter,[x[0] for x in databaseCursor.description])
            columnHeadersAreNotYetWritten = False
          #logger.debug("iterating through crash %s (%s)",aCrash,len(aCrash))
          aCrashAsAList = []
          currentName = ''
          currentUuid = ''
          for i, x in enumerate(aCrash):
            if x is None:
              aCrashAsAList.append(r'\N')
              continue
            if i == 2:
              currentUuid = x.rsplit('/',1)[-1]
            if i == 10: #r.os_name
              currentName = x.strip()
            if i == 11: #r.os_version
              # per bug 519703
              aCrashAsAList.append(idCache.getAppropriateOsVersion(currentName, x))
              currentName=''
              continue
            if i == 14: #bug_associations.bug_id
              aCrashAsAList.append(','.join(str(bugid) for bugid in x))
              continue
            if i == 15: #r.user_comments
              x=x.replace('\t',' '); # per bug 519703
            if i == 17: #r.email -- show 'email' if the email is likely useful
              # per bugs 529431/519703
              if '@' in x:
                x='yes'
              else:
                x = ''
            if type(x) == str:
              x = x.strip().replace('\r','').replace('\n',' | ')
            aCrashAsAList.append(x)
          writeRowToInternalAndExternalFiles(csvFormatter,csvPublicFormatter,aCrashAsAList)
          # end for loop over each aCrash
      finally: # level 2
        if gzippedOutputFile:
          gzippedOutputFile.close()
        if gzippedPublicOutputFile:
          gzippedPublicOutputFile.close()
    finally: # level 1
      #print psy.connectionStatus(databaseConnection)
      databaseConnectionPool.cleanup()
      #print psy.connectionStatus(databaseConnection)

  except: # level 0
    util.reportExceptionAndContinue(logger)

def writeRowToInternalAndExternalFiles(internalFormatter,externalFormatter,aCrashAsAList):
  """
  Write a row to each file: Seen by internal users (full details), and external users (bowdlerized)
  """
  # logger.debug("Writing crash %s (%s)",aCrashAsAList,len(aCrashAsAList))
  if internalFormatter:
    internalFormatter.writerow(aCrashAsAList)
  else:
    logger.error("Failed to write to Interal (full) gzip file: %s",aCrashAsAList)
  # per bug 529431
  bowdlerList = copy.copy(aCrashAsAList)
  if bowdlerList[1]:
    bowdlerList[1] = 'URL (removed)'
  if len(bowdlerList) > 17: # This *should* always be true
    bowdlerList[17] = ''
  if externalFormatter:
    externalFormatter.writerow(bowdlerList)

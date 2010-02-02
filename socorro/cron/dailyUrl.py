#!/usr/bin/python

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
  try:
    try:
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

      if config.product == '':
        productPhrase = ''
      else:
        productPhrase = "and r.product = '%s'" % config.product

      if config.version == '':
        versionPhrase = ''
      else:
        versionPhrase = "and r.version = '%s'" % config.version

      # -- N : array index. SQL's idea of the index is one greater
      sql = """
      select distinct
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
        r.cpu_name,   --12
        r.address,    --13
        array(select ba.bug_id from bug_associations ba where ba.signature = r.signature) as bug_list, --14
        r.user_comments, --15
        r.uptime as uptime_seconds, -- 16
        case when (r.email is NULL OR r.email='') then '' else r.email end as email, -- 17
        (select sum(adu_count) from raw_adu adu
           where adu.date = '%s'
             AND pd.product = adu.product_name AND pd.version = adu.product_version
             AND substring(r.os_name from 1 for 3) = substring(adu.product_os_platform from 1 for 3)
             AND r.os_version LIKE '%%'||adu.product_os_version||'%%') as adu_count -- 18
      from
        reports r left join productdims pd on r.product = pd.product and r.version = pd.version
      where
        '%s' >= r.date_processed and r.date_processed > '%s'
        %s %s
      order by 5 -- r.date_processed, munged
      """ % (nowAsString, nowAsString, yesterdayAsString, productPhrase, versionPhrase) # adu date, date_processed, date_processed, where(product) where(version)
      idCache = IdCache(databaseCursor)
      try:
        gzippedOutputFile = gzip.open(outputPathName, "w")
        gzippedPublicOutputFile = gzip.open(publicOutputPathName, "w")
        csvFormatter = csv.writer(gzippedOutputFile, delimiter='\t', lineterminator='\n')
        csvPublicFormatter = csv.writer(gzippedPublicOutputFile, delimiter='\t', lineterminator='\n')
        columnHeadersAreNotYetWritten = True
        psy.execute(databaseCursor, sql)
        crashData = databaseCursor.fetchall()
        try:
          logger.info("For %s, handling %s crashes",nowAsString,len(crashData))
        except:
          logger.debug("Type of crashData is %s",type(crashData))
          logger.info("No useful crash data found for dates between %s and %s",yesterdayAsString,nowAsString)
        
        for aCrash in crashData:
          if columnHeadersAreNotYetWritten:
            writeRowToInternalAndExternalFiles(csvFormatter,csvPublicFormatter,getColumnHeader([x[0] for x in databaseCursor.description]))
            columnHeadersAreNotYetWritten = False
          logger.debug("iterating through crash %s (%s)",aCrash,len(aCrash))
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
          appendDetailsFromJson(config,aCrashAsAList,currentUuid)
          writeRowToInternalAndExternalFiles(csvFormatter,csvPublicFormatter,aCrashAsAList)
      finally:
        gzippedOutputFile.close()
        gzippedPublicOutputFile.close()

    finally:
      databaseConnectionPool.cleanup()
  except:
    util.reportExceptionAndContinue(logger)

def pathFromUuidAndMount(mount,uuid,suffix):
  tmp = "%%s%s%%s%s%%s.%%s"%(os.path.sep,os.path.sep)
  return os.path.join(mount,tmp%(uuid[0:2],uuid[2:4],uuid,suffix))

def getJson(config,uuid):
  mountPoints = config.get('rawFileMountPoints').split()
  fh = None
  jsonDoc = None
  for mount in mountPoints:
    try:
      try:
        fh = open(pathFromUuidAndMount(mount,uuid,'json'),'r')
        jsonDoc = simplejson.load(fh)
        return jsonDoc
      except IOError,x:
        if(2 == x.errno):
          pass
        else:
          raise
      except ValueError:
        pass
    finally:
      if fh:
        fh.close()
  return None


def addonsChecked(addonVal):
  ret = 'not'
  if addonVal and not 'false' == ("%s"%addonVal).lower():
    ret = 'checked'
  return ret

# extend this list to handle more json data
# header: columnHeader text
# key:    key in json Document
# valueFunction: convert jsonDoc[key] to column value
jsonInformation = [
  {'header':'addons_checked','key':'EMCheckCompatibility','valueFunction': addonsChecked}
  ]
def getColumnHeader(dbItems, infoList=jsonInformation):
  dbItems.extend([x['header'] for x in infoList])
  return dbItems
  
def appendDetailsFromJson(config,aCrashAsAList,uuid, infoList=jsonInformation):
  if not uuid:
    logger.warn("No uuid from %s",aCrashAsAList)
    return
  logger.debug("Attempting to get json from uuid '%s'",uuid)
  jsonDoc = getJson(config,uuid)
  if jsonDoc:
    for key,func in [(x['key'],x['valueFunction']) for x in infoList]:
      value = 'unknown'
      try:
        value = func(jsonDoc[key])
      except:
        pass
    aCrashAsAList.append(value)
  else:
    logger.warn("No %s.json file was accessible",uuid)
  
def writeRowToInternalAndExternalFiles(internalFormatter,externalFormatter,aCrashAsAList):
  """
  Write a row to each file: Seen by internal users (full details), and external users (bowdlerized)
  """
  logger.debug("Writing crash %s (%s)",aCrashAsAList,len(aCrashAsAList))
  internalFormatter.writerow(aCrashAsAList)
  # per bug 529431
  bowdlerList = copy.copy(aCrashAsAList)
  if bowdlerList[1]:
    bowdlerList[1] = 'URL removed'
  if len(bowdlerList) > 17: # This *should* always be true
    bowdlerList[17] = ''
  externalFormatter.writerow(bowdlerList)

import copy
import datetime
import logging
from operator import itemgetter
import threading
import time

import psycopg2

import socorro.lib.util as lib_util
import socorro.cron.util as cron_util
import socorro.database.cachedIdAccess as socorro_cia
import socorro.database.postgresql as db_pgsql

logger = logging.getLogger("topCrashBySignature")
resultTable = 'top_crashes_by_signature'
sourceTable = 'reports'

class TopCrashesBySignature(object):
  """
  Tool to populate an aggregate summary table of crashes from data in the reports table. Table top_crashes_by_signature has
   - Keys are signature, productdims_id, osdims_id
   - Data are, for each triple of product dimension, os dimension and signature (os may be null if unknown)
      = count: The number of times this signature was seen associated with this product dimension and os dimension
      = uptime: the average uptime prior to the crash associated with this product dimension and os dimension
      = hang_count: The number of crashes associated with this signature in this time period that are hangs
      = plugin_count: The number of crashes associated with this signature in the time periood that are plugin-related
      = window_end: for book-keeping, restart
      = window_size: for book-keeping, restart
  Constructor parameters are:
    - database connection details as usual
    - processingInterval defaults to 12 minutes: 5 per hour. Must evenly divide a 24-hour period
    - startDate: First moment to examine
    --- Default is discovered by inspecting top_crashes_by_signature for most recent update (usually),
    --- or fails over to midnight of initialInterval days in the past
    - initialIntervalDays defaults to 4: How many days before now to start working if there is no prior data
    - endDate default is end of the latest processingInterval that is before now().
    - deltaDate what is the 'outer' processing interval. No default.
    --- if no xxxxDate is provided, defaults are used. Providing one is an error, any two are ok, if three, they must be self-consistent
  Usage:
  Once constructed, invoke processIntervals(**kwargs) where kwargs may override the constructor parameters.
  method processIntervals loops through the intervals between startDate and endDate effectively calling:
    storeFacts(fixupCrashData(extractDataForPeriod(startPeriod,endPeriod,data),startPeriod,processingInterval)
  If you prefer to handle the details in your own code, you may mimic or override processIntervals.
  """
  def __init__(self,configContext):
    super(TopCrashesBySignature,self).__init__()
    try:
      assert "databaseHost" in configContext, "databaseHost is missing from the configuration"
      assert "databaseName" in configContext, "databaseName is missing from the configuration"
      assert "databaseUserName" in configContext, "databaseUserName is missing from the configuration"
      assert "databasePassword" in configContext, "databasePassword is missing from the configuration"
      databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
      # Be sure self.connection is closed before you quit!
      self.connection = psycopg2.connect(databaseDSN)
    except (psycopg2.OperationalError, AssertionError),x:
      lib_util.reportExceptionAndAbort(logger)
    self.configContext = configContext
    self.debugging = configContext.get('debug',False)
    self.dateColumnName = configContext.get('dateColumnName', 'date_processed') # could be client_crash_date
    cursor = self.connection.cursor()
    try:
      self.productVersionRestriction = cron_util.getProductId(configContext.product, configContext.version, cursor, logger)
    except:
      self.productVersionRestriction = None
    if self.productVersionRestriction:
      self.productVersionSqlRestrictionPhrase = "and p.id = %s" % self.productVersionRestriction
    else:
      self.productVersionSqlRestrictionPhrase = ""
    logger.debug('%s %s', self.productVersionRestriction, self.productVersionSqlRestrictionPhrase)
    self.startDate,self.deltaDate,self.endDate = cron_util.getProcessingDates(self.configContext,resultTable,self.productVersionRestriction,cursor,logger)

  def tallyPVpairs(self, rows, columns, startDateAsCompactString, previousDateAsCompactString, summaryCrashes, idCache):
    """
    This function iterates through the results of the database query in the extractDataForPeriod function.
    Each row represents a single crash.
    """
    for r in rows:
      row = lib_util.DotDict((key, value) for key, value in zip(columns, r)) # make a row object addressable by column name
      # products with a version ending in 'pre' are development builds known as nightlies.
      # the following 'if' block filters out crashes that are not from a nightly build
      # from the last 48 hours
      if row.version[-3:] == 'pre':
        logger.debug('%s %s', row.version, row.build)
        try:
          buildDateAsCompactString = row.build[:8]
        except TypeError:
          continue
        if buildDateAsCompactString != startDateAsCompactString and buildDateAsCompactString != previousDateAsCompactString:
          logger.debug('skipping: %s != %s and %s != %s', buildDateAsCompactString, startDateAsCompactString, buildDateAsCompactString, previousDateAsCompactString)
          continue
      key = (row.signature, row.productdims_id, idCache.getOsId(row.os_name, row.os_version))
      value = summaryCrashes.setdefault(key, lib_util.DotDict({'count':0,'uptime':0,'hang_count':0,'plugin_count':0}))
      value.count += 1
      value.uptime += row.uptime
      value.hang_count += row.hang_count
      value.plugin_count += row.plugin_count

  def extractDataForPeriod(self, startTime, endTime, summaryCrashes):
    """
    Given a start and end time, return tallies for the data from the half-open interval startTime <= (date_column) < endTime
    Parameter summaryCrashes is a dictionary that will contain signature:data. Passed as a parameter to allow external looping
    returns (and is in-out parameter) summaryCrashes where for each signature as key, the value is {'count':N,'uptime':N}
    """
    startDateAsCompactString = '%4d%02d%02d' % (startTime.year, startTime.month, startTime.day)
    previousDate = startTime - datetime.timedelta(1)
    previousDateAsCompactString = '%4d%02d%02d' % (previousDate.year, previousDate.month, previousDate.day)
    cur = self.connection.cursor()
    idCache = socorro_cia.IdCache(cur,logger=logger)
    if startTime > endTime:
      raise ValueError("startTime(%s) must be <= endTime(%s)"%(startTime,endTime))

    resultColumnlist = 'r.uptime, r.signature, r.build, r.version, cfg.productdims_id, r.os_name, r.os_version'
    inputColumns = [x.split('.')[1] for x in resultColumnlist.split(',')]
    sql = """SELECT
                 %(resultColumnlist)s,
                 CASE WHEN r.hangid IS NULL THEN 0 ELSE 1 END AS hang_count,
                 CASE WHEN r.process_type = 'plugin' THEN 1 ELSE 0 END AS plugin_count
             FROM product_visibility cfg JOIN productdims p on cfg.productdims_id = p.id
             JOIN %(inTable)s r on p.product = r.product AND p.version = r.version
             WHERE
                 NOT cfg.ignore
                 AND %%(startTime)s <= r.%(dcolumn)s AND r.%(dcolumn)s < %%(endTime)s
                 AND cfg.start_date <= r.%(dcolumn)s AND r.%(dcolumn)s <= cfg.end_date
                 %(productVersionSqlRestrictionPhrase)s
          """%({'dcolumn':self.dateColumnName, 'resultColumnlist':resultColumnlist,'inTable':sourceTable, 'productVersionSqlRestrictionPhrase':self.productVersionSqlRestrictionPhrase})
    startEndData = {'startTime':startTime, 'endTime':endTime,}
    if self.debugging:
      logger.debug("Collecting data in range[%s,%s) on column %s",startTime,endTime, self.dateColumnName)
    #zero = {'count':0,'uptime':0}
    try:
      #fetchmany(size) /w/ namedcursor => intermittent "ProgrammingError: named cursor isn't valid anymore"
      #per http://www.velocityreviews.com/forums/t649192-psycopg2-and-large-queries.html we should not use
      # unnamed cursors for fetchmany() calls. Thus, after some thought: Drop back to fetchall() on unnamed
      #cursor = self.connection.cursor('extractFromReports')
      cursor = self.connection.cursor()
      if self.debugging:
        logger.debug(cursor.mogrify(sql,startEndData))
      cursor.execute(sql,startEndData)
      chunk = cursor.fetchall()
      inputColumns.append('hang_count')
      inputColumns.append('plugin_count')
      self.connection.commit()
      self.tallyPVpairs(chunk, inputColumns, startDateAsCompactString, previousDateAsCompactString, summaryCrashes, idCache)
      logger.debug("Returning %s items for window [%s,%s)",len(summaryCrashes),startTime,endTime)
      return summaryCrashes # redundantly
    except Exception, x:
      logger.warn('Exception during extractDataForPeriod: %s',x)
      self.connection.rollback()
      raise

  def fixupCrashData(self,crashMap, windowEnd, windowSize):
    """
    Creates and returns an unsorted list based on data in crashMap (No need to sort: DB will hold data)
    crashMap is {(sig,prod,os):{count:c,uptime:u}}
    result is list of maps where aach map has keys 'signature','productdims_id','osdims_id', 'count', 'uptime', 'hang_count' and 'plugin_count'
    """
    crashList = []
    always = {'windowEnd':windowEnd,'windowSize':windowSize}
    if self.debugging:
      logger.debug("Fixup crash data for %s items",len(crashMap))
    for key,value in crashMap.items():
      (value['signature'],value['productdims_id'],value['osdims_id']) = key
      value.update(always)
      crashList.append(value)
    return crashList

  def storeFacts(self, crashData, intervalString):
    """
    Store crash data in the top_crashes_by_signature table
      crashData: List of {productdims_id:id,osdims_id:id,signature:signatureString,'count':c,'uptime':u,'hang_count':hc,'plugin_count':pc} as produced by self.fixupCrashData()
    """
    if not crashData or 0 == len(crashData):
      logger.warn("%s - No data for interval %s",threading.currentThread().getName(),intervalString)
      return 0
    # else
    if self.debugging:
      logger.debug('Storing %s rows into table %s at %s',len(crashData),resultTable,intervalString)
    sql = """INSERT INTO %s
          (count, uptime, signature, productdims_id, osdims_id, window_end, window_size, hang_count, plugin_count)
          VALUES (%%(count)s,%%(uptime)s,%%(signature)s,%%(productdims_id)s,%%(osdims_id)s,%%(windowEnd)s,%%(windowSize)s,%%(hang_count)s,%%(plugin_count)s)
          """%(resultTable)
    cursor = self.connection.cursor()
    try:
      cursor.executemany(sql,crashData)
      self.connection.commit()
      return len(crashData)
    except Exception,x:
      self.connection.rollback()
      lib_util.reportExceptionAndAbort(logger)

  def processDateInterval(self,**kwargs):
    """
    Loop over all the processingIntervals within the specified startDate, endDate period:
    gathering, orgainizing and storing he summary data for each interval.
    Parameters in kwargs can be used to override the same parameters passed to self's constructor:
    startDate, endDate, dateColumnName, processingInterval
    In addition, you may pass a map as summaryCrashes which will be extended in the first processing interval
    """
    summaryCrashes = kwargs.get('summaryCrashes',{})
    oldDateColumnName = self.dateColumnName
    self.dateColumnName = kwargs.get('dateColumnName',self.dateColumnName)
    revertDateColumnName = (self.dateColumnName != oldDateColumnName)
    cursor = self.connection.cursor()
    startWindow,deltaWindow,endWindow = cron_util.getProcessingWindow(self.configContext,resultTable,self.productVersionRestriction,cursor,logger,**kwargs)
    startWindow = self.startDate
    try:
      fullCount = 0
      while startWindow + deltaWindow <= self.endDate:
        logger.debug("%s - Processing with interval from %s, size=%s)",threading.currentThread().getName(),startWindow,deltaWindow)
        summaryCrashes = self.extractDataForPeriod(startWindow, startWindow+deltaWindow, summaryCrashes)
        data = self.fixupCrashData(summaryCrashes,startWindow+deltaWindow,deltaWindow)
        fullCount += self.storeFacts(data, "Start: %s, size=%s"%(startWindow,deltaWindow))
        summaryCrashes = {}
        startWindow += deltaWindow
    finally:
      self.connection.close()
      if revertDateColumnName:
        self.dateColumnName = oldDateColumnName
    return fullCount


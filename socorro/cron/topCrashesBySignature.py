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

class TopCrashesBySignature(object):
  """
  Tool to populate an aggregate summary table of crashes from data in the reports table. Table top_crashes_by_signature has
   - Keys are signature, productdims_id, osdims_id
   - Data are, for each triple of product dimension, os dimension and signature (os may be null if unknown)
      = count: The number of times this signature was seen associated with this product dimension and os dimension
      = uptime: the average uptime prior to the crash associated with this product dimension and os dimension
      = window_end: for book-keeping, restart
      = window_size: for book-keeping, restart
  Constructor parameters are:
    - database connection details as usual
    - processingInterval defaults to 12 minutes: 5 per hour. Must evenly divide a 24-hour period
    - startDate: First moment to examine. Must be exactly N*processingInterval minutes past midnight
    --- Default is discovered by inspecting top_crashes_by_signature for most recent update (usually),
    --- or fails over to midnight of initialInterval days in the past
    --- a specified startDate must be exactly N*processingInterval minutes past midnight. Asserted, not calculated.
    - initialIntervalDays defaults to 4: How many days before now to start working if there is no prior data
    - endDate default is end of the latest processingInterval that is before now().
    --- if parameter endDate <= startDate: endDate is set to startDate (an empty enterval)
    --- otherwise, endDate is adjusted to be in range(startDate,endDate) inclusive and on a processingInterval
    - dateColumnName default is date_processed to mimic old code, but could be client_crash_date
    - dbFetchChunkSize default is 512 items per fetchmany() call, adjust for your database/file-system (obsolete)
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
    self.defaultProcessingInterval = 12
    self.lastEnd = None # cache for db hit in self.getLegalProcessingInterval
    self.outTable = 'top_crashes_by_signature'
    self.inTable = 'reports'
    ## WARNING: Next line has important side effect: Should call before getStartDate ##
    self.processingInterval = self.getLegalProcessingInterval(int(configContext.get('processingInterval',0)))
    self.deltaWindow = datetime.timedelta(minutes = self.processingInterval)
    self.initialIntervalDays = int(configContext.get('initialIntervalDays',4)) # must come before self.startDate
    self.startDate = self.getStartDate(configContext.get('startDate',None))
    self.endDate = self.getEndDate(configContext.get('endDate',None))
    self.dbFetchChunkSize = int(configContext.get('dbFetchChunkSize',512))
    self.dateColumnName = configContext.get('dateColumnName', 'date_processed') # could be client_crash_date
    self.debugging = configContext.get('debug',False)

  def setProcessingInterval(self, processingIntervalInMinutes):
    """Set processingInterval AND deltaWindow"""
    self.processingInterval = processingIntervalInMinutes
    self.deltaWindow = datetime.timedelta(minutes = self.processingInterval)
    
  def getLegalProcessingInterval(self,target=0):
    min = target
    if not min:
      cursor = self.connection.cursor()
      try:
        sql="SELECT window_end,window_size FROM %s ORDER BY window_end DESC LIMIT 1"%(self.outTable)
        logger.debug("Running %s",sql)
        cursor.execute(sql);
        self.connection.rollback()
        (self.lastEnd,windowSize) = cursor.fetchone()
        assert 0 == windowSize.microseconds, "processingInterval must be a whole number of minutes, but got %s microseconds"%windowSize.microseconds
        assert 0 == windowSize.days, "processingInterval must be less than a full day, but got %s days"%windowSize.days
        min = windowSize.seconds/60
      except TypeError: # Don't log 'NoneType object is not iterable'
        self.connection.rollback()
        self.lastEnd, windowSize = None,None
      except Exception,x:
        self.connection.rollback()
        lib_util.reportExceptionAndContinue(logger)        
        self.lastEnd, windowSize = None,None
    if not min:
      min = self.defaultProcessingInterval
    assert min > 0, 'Negative processing interval is not allowed, but got %s'%min
    assert min == int(min), 'processingInterval must be whole number of minutes, but got %s'%min
    assert 0 == (24*60)%min, 'Minutes in processing interval must divide evenly into a day, but got %d'%min
    return min

  def getStartDate(self, startDate=None):
    """
    Return the appropriate startDate for this invocation of TopCrashesBySignature
     - if no startDate param, try to use the cached startDate (window_end from top_crashes_by_signature) if any
     - if no cached startDate, return midnight of initialIntervalDays before now
     - if startDate parameter, truncate it to exact seconds
     Finally assert that the start date is midnight, or exactly some number of processingIntervals after midnight
     then return the (calculated) date
    """
    if not startDate:
      if self.lastEnd:
        startDate = self.lastEnd
      else:
        startDate = datetime.datetime.now() - datetime.timedelta(days=self.initialIntervalDays)
        startDate = startDate.replace(hour=0,minute=0,second=0,microsecond=0)
    else:
      startDate = datetime.datetime.fromtimestamp(time.mktime(startDate.timetuple()))
    check = startDate.replace(hour=0,minute=0,second=0,microsecond=0)
    deltah = datetime.timedelta(hours=1)
    while deltah>self.deltaWindow and check < startDate-deltah:
      check += deltah
    while check < startDate:
      check += self.deltaWindow
    assert check == startDate,'startDate %s is not on a processingInterval division (%s)'%(startDate,self.processingInterval)
    return startDate

  def getEndDate(self, endDate = None, startDate=None):
    if not startDate:
      startDate = self.startDate
    now = datetime.datetime.now()
    now -= self.deltaWindow
    deltah = datetime.timedelta(hours=1)
    if endDate:
      endDate = datetime.datetime.fromtimestamp(time.mktime(endDate.timetuple()))
    if endDate and endDate <= startDate:
      return startDate
    if (not endDate) or endDate >= now:
      endDate = now
      endDate = endDate.replace(hour=0,minute=0,second=0,microsecond=0)
      while endDate < now - deltah: # At worst 23 (22?) loops
        endDate += deltah
      while endDate < now: # at worst, about 59 (58?) loops
        endDate += self.deltaWindow
    else:
      mark = endDate - self.deltaWindow
      deltad = datetime.timedelta(days=1)
      endDate = startDate
      while endDate < mark - deltad: # x < initialIntervalDays loops
        endDate += deltad
      while endDate < mark - deltah: # x < 23 loops
        endDate += deltah
      while endDate <= mark: # x < 59 loops
        endDate += self.deltaWindow
    return endDate

  def extractDataForPeriod(self, startTime, endTime, summaryCrashes):
    """
    Given a start and end time, return tallies for the data from the half-open interval startTime <= (date_column) < endTime
    Parameter summaryCrashes is a dictionary that will contain signature:data. Passed as a parameter to allow external looping
    returns (and is in-out parameter) summaryCrashes where for each signature as key, the value is {'count':N,'uptime':N}
    """
    cur = self.connection.cursor()
    idCache = socorro_cia.IdCache(cur,logger=logger)
    if startTime > endTime:
      raise ValueError("startTime(%s) must be <= endTime(%s)"%(startTime,endTime))
    inputColumns = ["uptime", "signature", "productdims_id", "os_name", "os_version"]
    columnIndexes = dict((x,inputColumns.index(x)) for x in inputColumns)
    cI = columnIndexes # Spare the typing and spoil the editor's line-wrapping

    resultColumnlist = 'r.uptime, r.signature, cfg.productdims_id, r.os_name, r.os_version'
    sql = """SELECT %(resultColumnlist)s FROM product_visibility cfg
                JOIN productdims p on cfg.productdims_id = p.id
                JOIN %(inTable)s r on p.product = r.product AND p.version = r.version
              WHERE NOT cfg.ignore AND %%(startTime)s <= r.%(dcolumn)s and r.%(dcolumn)s < %%(endTime)s
              AND   r.%(dcolumn)s >= cfg.start_date AND r.%(dcolumn)s <= cfg.end_date
          """%({'dcolumn':self.dateColumnName, 'resultColumnlist':resultColumnlist,'inTable':self.inTable})
    startEndData = {'startTime':startTime, 'endTime':endTime,}
    if self.debugging:
      logger.debug("Collecting data in range[%s,%s) on column %s",startTime,endTime, self.dateColumnName)
    zero = {'count':0,'uptime':0}
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
      if chunk and chunk[0]:
        for row in chunk:
          key = (row[cI['signature']],row[cI['productdims_id']],idCache.getOsId(row[cI['os_name']],row[cI['os_version']]))
          value = summaryCrashes.setdefault(key,copy.copy(zero))
          value['count'] += 1
          value['uptime'] += row[cI['uptime']]
      self.connection.commit()
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
    result is list of maps where aach map has keys 'signature','productdims_id','osdims_id', 'count' and 'uptime'
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
      crashData: List of {productdims_id:id,osdims_id:id,signature:signatureString,'count':c,'uptime',u} as produced by self.fixupCrashData()
    """
    if not crashData or 0 == len(crashData):
      logger.warn("%s - No data for interval %s",threading.currentThread().getName(),intervalString)
      return 0
    # else
    if self.debugging:
      logger.debug('Storing %s rows into table %s at %s',len(crashData),self.outTable,intervalString)
    sql = """INSERT INTO %s
          (count, uptime, signature, productdims_id, osdims_id, window_end, window_size)
          VALUES (%%(count)s,%%(uptime)s,%%(signature)s,%%(productdims_id)s,%%(osdims_id)s,%%(windowEnd)s,%%(windowSize)s)
          """%(self.outTable)
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
    startDate = self.getStartDate(startDate=kwargs.get('startDate',self.startDate))
    endDate = self.getEndDate(endDate=kwargs.get('endDate',self.endDate),startDate=startDate)
    oldDateColumnName = self.dateColumnName
    self.dateColumnName = kwargs.get('dateColumnName',self.dateColumnName)
    revertDateColumnName = (self.dateColumnName != oldDateColumnName)
    oldProcessingInterval = self.processingInterval
    self.setProcessingInterval(self.getLegalProcessingInterval(kwargs.get('processingInterval',self.processingInterval)))
    revertProcessingInterval = (oldProcessingInterval != self.processingInterval)
    startWindow = startDate
    try:
      fullCount = 0
      while startWindow + self.deltaWindow <= endDate:
        logger.debug("%s - Processing with interval from %s, size=%s)",threading.currentThread().getName(),startWindow,self.deltaWindow)
        summaryCrashes = self.extractDataForPeriod(startWindow, startWindow+self.deltaWindow, summaryCrashes)
        data = self.fixupCrashData(summaryCrashes,startWindow+self.deltaWindow,self.deltaWindow)
        fullCount += self.storeFacts(data, "Start: %s, size=%s"%(startWindow,self.deltaWindow))
        summaryCrashes = {}
        startWindow += self.deltaWindow
    finally:
      self.connection.close()
      if revertDateColumnName:
        self.dateColumnName = oldDateColumnName
      if revertProcessingInterval:
        self.setProcessingInterval(oldProcessingInterval)
    return fullCount
      

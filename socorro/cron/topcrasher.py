import copy
import datetime
import logging
from operator import itemgetter
import threading

import psycopg2

import socorro.lib.util as socorro_util

logger = logging.getLogger("topcrasher")

class TopCrasher(object):
  """
  Tool to populate an aggregate summary table of crashes from data in the reports table. Table topcrashfacts has
   - Keys are productdims_id, osdims_id, signaturedims_id
   - Data are, for each triple of product dimension, os dimension and signature (product or/and os may be null)
      = count: The number of times this signature was seen associated with this product dimension and os dimension
      = uptime: the average uptime prior to the crash associated with  this product dimension and os dimension
      = rank: (rank 1 is largest number reported) of this crash in the reporting period per product/os and across all
      = interval_start: for book-keeping, restart
      = interval_minues: for book-keeping, restart
  Constructor parameters are:
    - database connection details as usual
    - processingInterval defaults to 12 minutes: 5 per hour. Must evenly divide a 24-hour period
    - startDate: First moment to examine. Must be exactly N*processingInterval minutes past midnight
    --- Default is discovered by inspecting topcrashfacts for most recent update (usually),
    --- or fails over to midnight of initialInterval days in the past
    --- a specified startDate must be exactly N*processingInterval minutes past midnight. Asserted, not calculated.
    - initialIntervalDays defaults to 4: How many days before now to start working if there is no prior data
    - endDate default is end of the latest processingInterval that is before now().
    --- if parameter endDate <= startDate: endDate is set to startDate (an empty enterval)
    --- otherwise, endDate is adjusted to be in range(startDate,endDate) inclusive and on a processingInterval
    - dateColumnName default is date_processed to mimic old code, but could be client_crash_date
    - dbFetchChunkSize default is 512 items per fetchmany() call, adjust for your database/file-system
  Usage:
  Once constructed, invoke processIntervals(**kwargs) where kwargs may override the constructor parameters.
  method processIntervals loops through the intervals between startDate and endDate effectively calling:
    storeFacts(fixupCrashData(extractDataForPeriod(startPeriod,endPeriod,data),startPeriod,processingInterval)
  If you prefer to handle the details in your own code, you may mimic or override processIntervals.
  """
  def __init__(self,config):
    try:
      assert "databaseHost" in config, "databaseHost is missing from the configuration"
      assert "databaseName" in config, "databaseName is missing from the configuration"
      assert "databaseUserName" in config, "databaseUserName is missing from the configuration"
      assert "databasePassword" in config, "databasePassword is missing from the configuration"
      databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % config
      # Be sure self.connection is closed before you quit!
      self.connection = psycopg2.connect(databaseDSN)
    except (psycopg2.OperationalError, AssertionError),x:
      socorro_util.reportExceptionAndAbort(logger)
    self.config = config
    self.defaultProcessingInterval = 12
    self.lastStart = None # cache for db hit in self.getLegalProcessingInterval
    self.processingInterval = self.getLegalProcessingInterval(int(config.get('processingInterval',0)))
    self.processingIntervalDelta = datetime.timedelta(minutes = self.processingInterval)
    self.initialIntervalDays = int(config.get('initialIntervalDays',4)) # must come before self.startDate
    self.startDate = self.getStartDate(config.get('startDate',None))
    self.endDate = self.getEndDate(config.get('endDate',None))
    self.dbFetchChunkSize = int(config.get('dbFetchChunkSize',512))
    self.dateColumnName = config.get('dateColumnName', 'date_processed') # could be client_crash_date
    self.reportColumns = ["productdims_id", "osdims_id", "signaturedims_id", "uptime",]
    self.columnIndexes = dict((x,self.reportColumns.index(x)) for x in self.reportColumns)
    # These describe the possible keys into summary data. Historically, we have used indices 0 and 3
    self.keyDescriptors = [ 
      self.reportColumns[:3],                                              # index 0: fully specified: All three ids provided
      [self.reportColumns[0],None,                self.reportColumns[-2]], # index 1: 'any' os; specific product and signature
      [None,                self.reportColumns[1],self.reportColumns[-2]], # index 2: 'any' product; specific os and signature
      [None,                None,                 self.reportColumns[-2]], # index 3: 'any' os and 'any' product; specific signature
      ]

  def setProcessingInterval(self, processingIntervalInMinutes):
    """Set processingInterval AND processingIntervalDelta"""
    self.processingInterval = processingIntervalInMinutes
    self.processingIntervalDelta = datetime.timedelta(minutes = self.processingInterval)
    
  def getLegalProcessingInterval(self,target=0):
    min = target
    if not min:
      cursor = self.connection.cursor()
      try:
        cursor.execute("SELECT interval_start,interval_minutes FROM topcrashfacts ORDER BY interval_start DESC LIMIT 1")
        (self.lastStart,min) = cursor.fetchone()
      except Exception,x:
        self.connection.rollback()
        socorro_util.reportExceptionAndContinue(logger)        
        self.lastStart, min = None,None
    if not min:
      min = self.defaultProcessingInterval
    assert min > 0, 'Negative processing interval is not allowed, but got %s'%min
    assert min == int(min), 'processingInterval must be whole number of minutes, but got %s'%min
    assert 0 == (24*60)%min, 'Minutes in processing interval must divide evenly into a day, but got %d'%min
    return min
      
  def getStartDate(self, startDate=None):
    """
    Return the appropriate startDate for this invocation of TopCrasher
     - if no startDate param, try to use the cached startDate (interval_start from topcrashfacts) if any
     - if no cached startDate, return midnight of initialIntervalDays before now
     - if startDate parameter, truncate it to exact seconds
     Finally assert that the start date is midnight, or exactly some number of processingIntervals after midnight
     then return the (calculated) date
    """
    if not startDate:
      if self.lastStart:
        startDate = self.lastStart + self.processingIntervalDelta
      else:
        startDate = datetime.datetime.now() - datetime.timedelta(days=self.initialIntervalDays)
        startDate = startDate.replace(hour=0,minute=0,second=0,microsecond=0)
    else:
      startDate = startDate.replace(microsecond=0)
    check = startDate.replace(hour=0,minute=0,second=0,microsecond=0)
    deltah = datetime.timedelta(hours=1)
    while deltah>self.processingIntervalDelta and check < startDate-deltah:
      check += deltah
    while check < startDate:
      check += self.processingIntervalDelta
    assert check == startDate,'startDate %s is not on a processingInterval division (%s)'%(startDate,self.processingInterval)
    return startDate

  def getEndDate(self, endDate = None, startDate=None):
    if not startDate:
      startDate = self.startDate
    now = datetime.datetime.now()
    now -= self.processingIntervalDelta
    deltah = datetime.timedelta(hours=1)
    if endDate and endDate <= startDate:
      return startDate
    if (not endDate) or endDate >= now:
      endDate = now
      endDate = endDate.replace(hour=0,minute=0,second=0,microsecond=0)
      while endDate < now - deltah: # At worst 23 (22?) loops
        endDate += deltah
      while endDate < now: # at worst, about 59 (58?) loops
        endDate += self.processingIntervalDelta
    else:
      mark = endDate - self.processingIntervalDelta
      deltad = datetime.timedelta(days=1)
      endDate = startDate
      while endDate < mark - deltad: # x < initialIntervalDays loops
        endDate += deltad
      while endDate < mark - deltah: # x < 23 loops
        endDate += deltah
      while endDate <= mark: # x < 59 loops
        endDate += self.processingIntervalDelta
    return endDate

  def extractDataForPeriod(self, startTime, endTime, summaryCrashes):
    """
    Given a start and end time, return tallies for the data from the half-open interval startTime <= date_processed < endTime
    Parameter summaryCrashes is a dictionary that will contain signature:data. Passed as a parameter to allow external looping
    returns (and is in-out parameter) summaryCrashes where for each signature as key, the value is {'count':N,'uptime':N}
    """
    if startTime > endTime:
      raise ValueError("startTime(%s) must be <= endTime(%s)"%(startTime,endTime))
    #sql = "SELECT %(columnlist)s from crash_reports WHERE '%(startTime)s' <= %(dcolumn)s AND %(dcolumn)s < '%(endTime)s'"
    rcolumnlist = 'r.'+" ,r.".join(self.reportColumns)
    sql = """SELECT %(rcolumnlist)s FROM tcbysignatureconfig cfg JOIN crash_reports r
                    ON cfg.osdims_id = r.osdims_id AND cfg.productdims_id = r.productdims_id
              WHERE %%(startTime)s <= r.%(dcolumn)s and r.%(dcolumn)s < %%(endTime)s
              AND   r.%(dcolumn)s >= cfg.start_dt AND r.%(dcolumn)s <= cfg.end_dt
          """%({'dcolumn':self.dateColumnName, 'rcolumnlist':rcolumnlist})
    logger.debug("%s - Collecting data in range[%s,%s) on column %s",threading.currentThread().getName(),startTime,endTime, self.dateColumnName)
    cI = self.columnIndexes
    try:
      cursor = self.connection.cursor('extractFromReports')
      cursor.execute(sql,({'startTime':startTime, 'dcolumn':self.dateColumnName, 'endTime':endTime,}))
      while True:
        chunk = cursor.fetchmany(self.dbFetchChunkSize)
        if chunk and chunk[0]:
          for row in chunk:
            keySet = []
            for i in self.keyDescriptors:
              k = []
              for d in i:
                if d:
                  k.append(row[cI[d]])
                else:
                  k.append(None)
              keySet.append(tuple(k))
            for k in keySet:
              value = summaryCrashes.setdefault(k,{'count':0,'uptime':0})
              value['count'] += 1
              value['uptime'] += row[cI['uptime']]
          # end of 'for row in chunk'
        else: # no more chunks
          break
      self.connection.commit()
      logger.debug("%s - Returning %s items of data",threading.currentThread().getName(),len(summaryCrashes))
      return summaryCrashes # redundantly
    except:
      self.connection.rollback()
      raise

  signaturedimsCache = {}
  osdims_cache = {}
  productdims_cache = {}

  def fixupCrashData(self,crashMap):
    crashLists = [[],[],[],[]] #Indices are the same as for self.keyDescriptors. See __init__ near bottom
    for key,value in crashMap.items():
      (value['productdims_id'],value['osdims_id'],value['signaturedims_id']) = key
      if(None,None) == key[:2]: # all os, all product
        crashLists[3].append(value)
      elif None == key[0]:
        crashLists[2].append(value)
      elif None == key[1]:
        crashLists[1].append(value)
      else:
        crashLists[0].append(value)
    for crashList in crashLists:
      crashList.sort(key=itemgetter('count'),reverse=True)
      rank = 1
      for crash in crashList:
        crash['rank'] = rank
        rank += 1
    return crashLists

  def storeFacts(self, crashData, startTime, intervalMinutes):
    """
    Store crash data in the topcrashfacts table
      crashData: Lists of {productdims_id:id,osdims_id:id,signaturedims_id:id,'count':c,'rank':r,'uptime',u} as produced by self.fixupCrashData()
       - outer list has lists holding:
         0: all ids are index numbers
         1: osdims_id is None
         2: productdims_id is None
         3: productdims_id and osdims_id are both None
      startTime and intervalMinutes are stored in the table, used to determine the next interval to work on
    """
    storeData = crashData[0]
    for cd in crashData[1:]:
      storeData.extend(cd)
    if not storeData:
      logger.warn("%s - No data for interval start_date=%s,minutes=%s",threading.currentThread().getName(),startTime,intervalMinutes)
      return
    # else
    logger.debug('Storing %s rows into topcrashfacts table with last_updated=%s',len(storeData),startTime)
    sql = """INSERT INTO topcrashfacts
          (count, rank, uptime, productdims_id, osdims_id, signaturedims_id,interval_start,interval_minutes)
          VALUES (%%(count)s,%%(rank)s,%%(uptime)s,%%(productdims_id)s,%%(osdims_id)s,%%(signaturedims_id)s,'%s',%s)
          """%(startTime,intervalMinutes)
    cursor = self.connection.cursor()
    try:
      cursor.executemany(sql,storeData)
      self.connection.commit()
    except:
      self.connection.rollback()
      socorro_util.reportExceptionAndAbort(logger)

  def processIntervals(self,**kwargs):
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
    try:
      while startDate + self.processingIntervalDelta <= endDate:
        logger.info("%s - Processing with interval from %s, minutes=%s)",threading.currentThread().getName(),startDate,self.processingInterval)
        summaryCrashes = self.extractDataForPeriod(startDate, startDate+self.processingIntervalDelta, summaryCrashes)
        data = self.fixupCrashData(summaryCrashes)
        self.storeFacts(data,startDate,self.processingInterval)
        summaryCrashes = {}
        startDate += self.processingIntervalDelta
    finally:
      if revertDateColumnName:
        self.dateColumnName = oldDateColumnName
      if revertProcessingInterval:
        self.setProcessingInterval(oldProcessingInterval)

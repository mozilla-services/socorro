"""
Populate top_crashes_by_url and top_crashes_by_url_signature

For each day, product/version, os/version, domain/url associate a count of known crashes
For each row in table above, associate all signatures that were in a crash

To show counts associated with a particular domain, appropriate SELECT statements will be needed.

Counts will be done for only the top N most commonly encountered URLs for the particular day where N is configurable default 500

expects to run exactly once per day
"""
# table names (in case we want to make a quick-n-dirty change right here)
reportsTable = 'reports'
topCrashesByUrlTable = 'top_crashes_by_url'
topCrashesByUrlSignatureTable = 'top_crashes_by_url_signature'
topCrashesByUrlReportsTable =  'topcrashurlfactsreports'

import copy
import datetime
import logging
import psycopg2
import time

import socorro.database.cachedIdAccess as socorro_cia
import socorro.lib.util as socorro_util

logger = logging.getLogger('topCrashesByUrl')

class TopCrashesByUrl(object):
  """
  TopCrashesByUrl knows how to
   - extract crash data from reports
   - update facts table top_crashes_by_url holding the top (count of) crashes by url
     = key columns are productdims_id, urldims_id, osdims_id
     = value column is count
     = book-keeping columns: window_end (timestamp) and window_size (interval) which is 'nearly constant'
   - update correlation table holding facts table id and signatures
     = columns are top_crashes_by_url_id and signature
   - update correlation table holding facts table id and uuid with user_comment
     = columns are topcrashurlfacts_id (a historical name), uuid and comments

  Constructor takes a configContext, optional kwargs that override the context
  Required details for constructor are database dsn values
  Optional details for constructor are:
   - topCrashesByUrlTable to change the name of the facts table
   - topCrashesByUrlSignatureTable for the signature correlation table
   - topCrashesByUrlReportsTable for the reports correlation table
   - minimumHitsPerUrl: default 1 (ignored)
   - maximumUrls: default 500
   - dateColumn: default 'date_processed' (in reports table)
   - windowSize: default exactly one day
  You may either use the various methods yourself, or invoke myTopCrashByUrlInstance.processIntervals(**kwargs)
  processIntervals simply loops from the beginning time until there is not enough remaining time calling:
    - getNextAppropriateWindowStart: Assures us that there is sufficient time in the window
    - countCrashesPerUrlPerWindow: Collects as many as maximumUrls for crashes that have at least minimumHitsPerUrl
    - saveData: Uses the provided urls to collect aggregated and correlated data and save it
  """
  def __init__(self, configContext, **kwargs):
    super(TopCrashesByUrl, self).__init__()
    configContext.update(kwargs)
    assert "databaseHost" in configContext, "databaseHost is missing from the configuration"
    assert "databaseName" in configContext, "databaseName is missing from the configuration"
    assert "databaseUserName" in configContext, "databaseUserName is missing from the configuration"
    assert "databasePassword" in configContext, "databasePassword is missing from the configuration"
    self.configContext = configContext
    self.dsn = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    self.connection = psycopg2.connect(self.dsn)

    # handle defaults
    configContext.setdefault('reportsTable',reportsTable)
    configContext.setdefault('topCrashesByUrlTable',topCrashesByUrlTable)
    configContext.setdefault('topCrashesByUrlSignatureTable',topCrashesByUrlSignatureTable)
    configContext.setdefault('topCrashesByUrlReportsTable',topCrashesByUrlReportsTable)
    configContext.setdefault('minimumHitsPerUrl',1) # ignored
    configContext.setdefault('maximumUrls',500)
    # There's an issue with diff between raw and cooked urls (cooked: drop from '?' to end)
    # Based on exhastive analysis of three data points, want 15% more to cover. Pad to 20%
    # *** THIS IS A HACK ***:
    configContext.setdefault('fatMaximumUrls',configContext.maximumUrls + configContext.maximumUrls/5)
    configContext.setdefault('dateColumn','date_processed')
    configContext.setdefault('windowSize',datetime.timedelta(days=1))
    self.idCache = None
    logger.info("After constructor, config=\n%s",str(configContext))

  def getNextAppropriateWindowStart(self, lastWindowEnd=None):
    """
    Returns (nextWindowStart,tooCloseToNow).
     - If nextWindowStart is None, tooCloseToNow is False if we can't determine from db, else True
    If windowEnd, check it for appropriate as described below and return (windowEnd,False) else (None, True)
    Otherwise: Get the last updated windowEnd in the topCrashesByUrlTable.
    Check that the next windowSize time chunk ends strictly before 'now' (ignoring seconds and microseconds)
    If that check passes, return (windowEnd,False) of the next appropriate slot; else return (None,True)
    If there is no row in the table with a set windowEnd column, return (None,False)
    """
    now = datetime.datetime.now().replace(second=0,microsecond=0)
    tooCloseToNow = None
    doDB = True
    if lastWindowEnd:
      lastWindowEnd = datetime.datetime.fromtimestamp(time.mktime(lastWindowEnd.timetuple()))
      doDB = False
      if lastWindowEnd + self.configContext.windowSize > now:
        logger.info("Parameter windowEnd: %s is too close to now (%s) to allow full window size (%s)",lastWindowEnd,now,self.configContext.windowSize)
        lastWindowEnd = None      # too close to now. Wait until we have a whole slot's work to do
        tooCloseToNow = True
    if doDB:
      cur = self.connection.cursor()
      cur.execute("SELECT window_end FROM %s ORDER BY window_end DESC LIMIT 1"%topCrashesByUrlTable)
      lastWindowEnd = cur.fetchone()
      if not lastWindowEnd:
        logger.info("No row with window_end in table %s",topCrashesByUrlTable)
        lastWindowEnd = None
        tooCloseToNow = False
      else:
        lastWindowEnd = lastWindowEnd[0]
        if lastWindowEnd +self.configContext.windowSize > now:
          logger.info("Database column window_end: %s is too close to now (%s) to allow full window size (%s)",lastWindowEnd,now,self.configContext.windowSize)
          lastWindowEnd = None
          tooCloseToNow = True
    return lastWindowEnd,tooCloseToNow

  def countCrashesPerUrlPerWindow(self,lastWindowEnd=None):
    """
    Collect the count of all crashes per url within this time window.
    Deliberately ignore platform and os details to get counts per url on a global basis
    return [(count, url),...] for as many as maximumUrls hits within the time window, each with at least minimumHitsPerUrl.
    """
    cur = self.connection.cursor()
    windowStart,tooClose = self.getNextAppropriateWindowStart(lastWindowEnd)
    if not windowStart: # we don't care why
      logger.warn("with prior window ending at %s, unable to get good windowStart: %s",lastWindowEnd,windowStart)
      return []
    selector = {'startDate':windowStart,'endDate':(windowStart + self.configContext.windowSize)}
    topUrlSql = """SELECT COUNT(r.id), r.url FROM %(reportsTable)s r
                     JOIN productdims p ON r.product = p.product AND r.version = p.version
                     JOIN product_visibility cfg ON p.id = cfg.productdims_id
                     WHERE r.url IS NOT NULL AND %%(startDate)s <= r.%(dateColumn)s AND r.%(dateColumn)s < %%(endDate)s
                     AND cfg.start_date <= r.%(dateColumn)s AND r.%(dateColumn)s <= cfg.end_date
                     GROUP BY r.url
                     ORDER BY COUNT(r.id) desc
                     LIMIT %(fatMaximumUrls)s"""%(self.configContext) # fatMaximumUrls is a HACK to assure enough cooked urls
    cur.execute(topUrlSql,selector)
    data = cur.fetchall() # count (implicit rank) and url here.
    self.connection.rollback() # per suggestion in psycopg mailing list: Rollback if no db modification
    if not data:
      logger.warn("No url crash data collected between %(startDate)s and %(endDate)s",selector)
    return data

  def getUrlId(self,url):
    if not self.idCache:
      cursor = self.connection.cursor()
      self.idCache = socorro_cia.IdCache(cursor)
    return self.idCache.getUrlId(url)[0]

  def saveData(self, windowStart, countUrlData):
    """
    given a time-window (start) and a list of (count,fullUrl), for each fullUrl:
      - assure that the fullUrl is legal and available in in urldims
      - collect count, window_end, window_size, productdims_id,osdims_id,urldims_id,signature for all quads that match
      - merge the counts for all the signatures with the same (product,os,url) and insert that data into top_crashes_by_url...
      - ...collecting all the signatures for the merged data.
      - Insert the new row id and each signature into top_crashes_by_url_signature
      - return the number of rows added to top_crashes_by_url
    """
    if not countUrlData:
      return 0
    # No need to get the count: It is always exactly 1 because uuid is unique and we group by it.
    selectSql = """SELECT %%(windowEnd)s, %%(windowSize)s, p.id as prod, o.id as os, r.signature, r.uuid, r.user_comments
                     FROM %(reportsTable)s r
                     JOIN productdims p on r.product = p.product AND r.version = p.version
                     JOIN osdims o on r.os_name = o.os_name AND r.os_version = o.os_version
                    WHERE %%(windowStart)s <= r.%(dateColumn)s AND r.%(dateColumn)s < %%(windowEnd)s
                      AND r.url = %%(fullUrl)s
                    GROUP BY prod, os, r.signature, r.uuid, r.user_comments
                    """ % (self.configContext)
    getIdSql = """SELECT lastval()"""
    insertUrlSql = """INSERT INTO %(topCrashesByUrlTable)s (count, urldims_id, productdims_id, osdims_id, window_end, window_size)
                      VALUES (%%(count)s,%%(urldimsId)s,%%(productdimsId)s,%%(osdimsId)s,%%(windowEnd)s,%%(windowSize)s)""" % (self.configContext)
    insertSigSql = """INSERT INTO %(topCrashesByUrlSignatureTable)s (top_crashes_by_url_id,signature,count)
                      VALUES(%%s,%%s,%%s)""" % (self.configContext)
    insertUuidSql = """INSERT INTO %(topCrashesByUrlReportsTable)s (uuid,comments,topcrashurlfacts_id)
                       VALUES (%%s,%%s,%%s)""" % (self.configContext)
    windowData= {
      'windowStart': windowStart,
      'windowEnd': windowStart + self.configContext.windowSize,
      'windowSize': self.configContext.windowSize,
      }
    cursor = self.connection.cursor()
    insData = {}
    urldimsIdSet = set()
    for expectedCount,fullUrl in countUrlData:
      urldimsId = self.getUrlId(fullUrl) # updates urldims if needed
      urldimsIdSet.add(urldimsId)
      if not urldimsId:
        continue
      selector = {'fullUrl':fullUrl}
      selector.update(windowData)
      cursor.execute(selectSql,selector)
      self.connection.rollback() # didn't modify, so rollback is enough
      data = cursor.fetchall()
      for (windowEnd, windowSize, productdimsId, osdimsId, signature, uuid, comment) in data:
        key = (productdimsId,urldimsId,osdimsId)
        insData.setdefault(key,{'count':0,'signatures':{}, 'uuidAndComments':[]})
        insData[key]['count'] += 1 # Count all urls that had a crash
        if signature: #don't handle empty signatures
          insData[key]['signatures'].setdefault(signature,0)
          insData[key]['signatures'][signature] += 1
        if uuid or comment: # always True, because uuid, but what the heck.
          insData[key]['uuidAndComments'].append((uuid,comment))
      if len(urldimsIdSet) > self.configContext.maximumUrls:
        break
    insertCount = 0
    try:
      # Looping 'quite awhile' without closing transaction. Rollback *should* revert everything except urldims which is benign
      # 'quite awhile' is up to 500 urls with up to (maybe nine or ten thousand?) correlations total. So ~~ 10K rows awaiting commit()
      signatureCorrelationData = []
      uuidCommentCorrelationData = []
      aKey = None
      stage = "in pre-loop"
      for key in insData:
        aKey = key
        stage = "inserting url crash for %s"%(str(aKey))
        # the next line overwrites prior values (except the first time through)  with current values
        selector.update({'count':insData[key]['count'],'productdimsId':key[0],'urldimsId':key[1],'osdimsId':key[2]})
        # save the 'main' facts
        cursor.execute(insertUrlSql,selector)
        # grab the new row id
        stage = "getting new row id for %s"%(str(aKey))
        cursor.execute(getIdSql)
        newId = cursor.fetchone()[0]
        stage = "calculating secondary data for %s"%(str(aKey))
        # update data for correlations tables
        for signature,count in insData[key]['signatures'].items():
          signatureCorrelationData.append([newId,signature,count])
        for uuid,comment in insData[key]['uuidAndComments']:
          uuidCommentCorrelationData.append([uuid,comment,newId])
        insertCount += 1
      # end of loop over keys in insData
      # update the two correlation tables
      stage = "inserting signature correlations for %s"%(str(aKey))
      cursor.executemany(insertSigSql,signatureCorrelationData)
      stage = "inserting uuid correlations for %s"%(str(aKey))
      cursor.executemany(insertUuidSql,uuidCommentCorrelationData)
      stage = "commiting updates for %s"%(str(aKey))
      self.connection.commit()
      logger.info("Committed data for %s crashes for period %s up to %s",insertCount,windowStart,windowData['windowEnd'])
    except Exception,x:
      logger.warn("Exception while %s",stage)
      self.connection.rollback()
      socorro_util.reportExceptionAndAbort(logger)
    return insertCount

  def processIntervals(self, **kwargs):
    keepConfigContext = copy.copy(self.configContext)
    self.configContext.update(kwargs)
    outerStart = self.configContext.get('windowStart')
    pd = None
    if not outerStart:
      pd = self.configContext.get('processingDay')
      if pd:
        outerStart = datetime.datetime(pd.year,pd.month,pd.day)
    if not outerStart:
      outerStart = self.getNextAppropriateWindowStart()[0]
    if not outerStart:
      logger.warn("Will not process intervals: No appropriate start time is available")
      return

    outerEnd = self.configContext.get('windowEnd')
    if not outerEnd and pd:
      outerEnd = outerStart +self.configContext.get('windowSize')
    startTime = outerStart
    logger.info("Starting loop from %s up to %s step %s",startTime.isoformat(),outerEnd.isoformat(),self.configContext.windowSize)
    while startTime and startTime < outerEnd:
      data = self.countCrashesPerUrlPerWindow(startTime)
      if data:
        logger.info("Saving %s items in window starting at %s",len(data),startTime)
        self.saveData(startTime,data)
      else:
        logger.info("Window starting at %s had no data",startTime)
      # whether or not we saved some data, advance to next slot
      startTime += self.configContext.windowSize
    logger.info("Done processIntervals")
    self.configContext = keepConfigContext
      

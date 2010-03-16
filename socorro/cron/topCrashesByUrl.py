"""
Populate top_crashes_by_url and top_crashes_by_url_signature

For each day, product/version, os/version, domain/url associate a count of known crashes
For each row in table above, associate all signatures that were in a crash

To show counts associated with a particular domain, appropriate SELECT statements will be needed.

Counts will be done for only the top N most commonly encountered URLs for the particular day where N is configurable default 500

expects to run exactly once per day
"""
import copy
import datetime
import logging
import psycopg2
import time

import socorro.database.cachedIdAccess as socorro_cia
import socorro.lib.util as socorro_util
import socorro.lib.ConfigurationManager as cm
import socorro.cron.util as cron_util

logger = logging.getLogger('topCrashesByUrl')

# table names (in case we want to make a quick-n-dirty change right here)
reportsTable = 'reports'
resultTable = 'top_crashes_by_url'
resultSignatureTable = 'top_crashes_by_url_signature'
resultReportsTable =  'topcrashurlfactsreports'

# a few other top-level 'constant' values
dateColumn = 'date_processed' # in the reportsTable
defaultDeltaWindow = datetime.timedelta(days=1)
defaultMaximumUrls = 500
defaultMinimumHitsPerUrl = 1
# be aware of fatMaximumUrls in __init__ below

class TopCrashesByUrl(object):
  """
  TopCrashesByUrl knows how to
   - extract crash data from reports
   - update facts table top_crashes_by_url holding the top (count of) crashes by url per windowDelta time period
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
   - resultTable to change the name of the facts table
   - resultSignatureTable for the signature correlation table
   - resultReportsTable for the reports correlation table
   - minimumHitsPerUrl: Do not record data for urls with count of hits < than this. Default 1
   - maximumUrls: Do not record data for more urls than this. Default 500
   - dateColumn: default 'date_processed' (in reports table)
   - deltaWindow: overrides prior row in resultTable. Default exactly one day
  You may either use the various methods yourself, or invoke myTopCrashByUrlInstance.processCrashesByUrlWindows(**kwargs)
  processCrashesByUrlWindows simply loops from the beginning time until there is not enough remaining time calling:
    - countCrashesByUrlInWindow: Collects as many as maximumUrls for crashes that have at least minimumHitsPerUrl
    - saveData: Uses the provided urls to collect aggregated and correlated data and save it
    * note about the heuristic (hack): *
    countCrashesPerUrlInWindow actually collects a "fatMaximum" number of crashes based on raw urls. SaveData then
    counts the number of distinct url ids, adding together crashes from urls with the same id, and discarding only
    crashes whose count after that is still less than the minumum. This process might result in fewer than the requested
    maximum number.
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
    configContext.setdefault('resultTable',resultTable)
    configContext.setdefault('resultSignatureTable',resultSignatureTable)
    configContext.setdefault('resultReportsTable',resultReportsTable)
    configContext.setdefault('minimumHitsPerUrl',defaultMinimumHitsPerUrl)
    configContext.setdefault('maximumUrls',defaultMaximumUrls)
    configContext.setdefault('truncateUrlLength',None)
    # There's an issue with diff between raw and cooked urls (cooked: drop from '[?&=;]' to end, possibly truncate)
    # Based on exhastive analysis of three data points, want 15% more to cover. Pad to 20%
    # *** THIS IS A HACK ***:
    configContext.setdefault('fatMaximumUrls',configContext.maximumUrls + configContext.maximumUrls/5)

    configContext.setdefault('dateColumn',kwargs.get('dateColumn','date_processed'))
    self.idCache = None
    try:
      self.productVersionRestriction = cron_util.getProductId(configContext.product, configContext.version, self.connection.cursor(), logger)
    except:
      self.productVersionRestriction = None
    if self.productVersionRestriction:
      self.productVersionSqlRestrictionPhrase = "and p.id = %s" % self.productVersionRestriction
    else:
      self.productVersionSqlRestrictionPhrase = ""
    self.configContext['productVersionSqlRestrictionPhrase'] = self.productVersionSqlRestrictionPhrase
    logger.debug('%s %s', self.productVersionRestriction, self.productVersionSqlRestrictionPhrase)
    logger.info("After constructor, config=\n%s",str(configContext))
    # put the calculated date and window stuff into self.config
    kwargs.setdefault('defaultDeltaWindow',defaultDeltaWindow)
#    ignore = cron_util.getDateAndWindow(self.configContext,resultTable,self.productVersionRestriction,self.connection.cursor(),logger,**kwargs)

  def countCrashesByUrlInWindow(self, startWindow=None):
    """
    Collect the count of all crashes per url within this time window.
    Deliberately ignore platform and os details to get counts per url on a global basis
    return [(count, url),...] for as many as maximumUrls hits within the time window, each with at least minimumHitsPerUrl.
    """
    cur = self.connection.cursor()
    if not startWindow: # we don't care why
      return []
    deltaWindow = self.configContext.get('deltaWindow')
    assert deltaWindow, 'Cannot calculate crash count with deltaWindow="%s"'%deltaWindow
    selector = {'startDate':startWindow,'endDate':(startWindow+deltaWindow),}
    topUrlSql = """SELECT COUNT(r.id), r.url FROM %(reportsTable)s r
                     JOIN productdims p ON r.product = p.product AND r.version = p.version
                     JOIN product_visibility cfg ON p.id = cfg.productdims_id
                     WHERE r.url IS NOT NULL AND r.url <> '' AND %%(startDate)s <= r.%(dateColumn)s AND r.%(dateColumn)s < %%(endDate)s
                     AND cfg.start_date <= r.%(dateColumn)s AND r.%(dateColumn)s <= cfg.end_date
                     %(productVersionSqlRestrictionPhrase)s
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
      # if you want to truncate the length of stored url, pass it as truncateUrlLength=length in ctor below
      self.idCache = socorro_cia.IdCache(cursor,logger=logger, truncateUrlLength=self.configContext.truncateUrlLength)
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
                      %(productVersionSqlRestrictionPhrase)s
                    GROUP BY prod, os, r.signature, r.uuid, r.user_comments
                    """ % (self.configContext)
    getIdSql = """SELECT lastval()"""
    insertUrlSql = """INSERT INTO %(resultTable)s (count, urldims_id, productdims_id, osdims_id, window_end, window_size)
                      VALUES (%%(count)s,%%(urldimsId)s,%%(productdimsId)s,%%(osdimsId)s,%%(windowEnd)s,%%(windowSize)s)""" % (self.configContext)
    insertSigSql = """INSERT INTO %(resultSignatureTable)s (top_crashes_by_url_id,signature,count)
                      VALUES(%%s,%%s,%%s)""" % (self.configContext)
    insertUuidSql = """INSERT INTO %(resultReportsTable)s (uuid,comments,topcrashurlfacts_id)
                       VALUES (%%s,%%s,%%s)""" % (self.configContext)
    windowData= {
      'windowStart': windowStart,
      'windowEnd': windowStart + self.configContext.deltaWindow,
      'windowSize': self.configContext.deltaWindow,
      }
    cursor = self.connection.cursor()
    insData = {}
    urldimsIdSet = set()
    urldimsIdCounter = {}
    for expectedCount,fullUrl in countUrlData:
      urldimsId = self.getUrlId(fullUrl) # updates urldims if needed
      if not urldimsId:
        continue
      urldimsIdCounter.setdefault(urldimsId,0)
      urldimsIdCounter[urldimsId] += 1
      if(urldimsIdCounter[urldimsId]) >= self.configContext.minimumHitsPerUrl:
        urldimsIdSet.add(urldimsId)
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
        if key[1] in urldimsIdSet: # then this urlid has at least minimumHitsPerUrl
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
        #end if key[1] in urldimsIdSet
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

  def processDateInterval(self, **kwargs):
    cursor = self.connection.cursor()
    kwargs.setdefault('defaultDeltaWindow',defaultDeltaWindow)
    startDate,deltaDate,endDate,startWindow,deltaWindow,endWindow = cron_util.getDateAndWindow(self.configContext, resultTable, self.productVersionRestriction, cursor, logger, **kwargs)
    logger.info("Starting loop from %s up to %s step (%s)",startDate.isoformat(),endDate.isoformat(),deltaWindow)
    while startWindow + deltaWindow < endDate:
      data = self.countCrashesByUrlInWindow(startWindow=startWindow)
      if data:
        logger.info("Saving %s items in window starting at %s",len(data),startWindow)
        self.saveData(startWindow,data)
      else:
        logger.info("Window starting at %s had no data",startWindow)
      # whether or not we saved some data, advance to next slot
      startWindow += deltaWindow
    logger.info("Done processIntervals")


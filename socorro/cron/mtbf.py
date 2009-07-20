#!/usr/bin/python

"""
This script is what populates the time before failure table for the Mean Time Before failure report.

It will aggregate the previous days crash report informaiton, specifically the
average uptime, number of unique users, and number of reports. It does this across
products based on product_visibility for two dimensions - time and products.

The following fields are updated in time_before_failure table:
  id - primary key
  avg_seconds - average number of seconds (reports.uptime) for crashes in the window, per product, version, os, os-version
  - Note that outlier data are cleaned up in this process
  report_count - number of crash reports 
  window_end - the end point of the aggregation slot. By default, midnight 00:00:00 of 'tomorrow'
  window_size - the size of the aggregation slot. By default 1 day (slot is end-size <= x < end)
  productdims_id - foreign key reference the product dimensions table
  osdims_id - foreign key references the os dimentions table
  
On the front end various products from product_visibility are grouped into reports based on
 - product and product version (and thus the type of release: major, milestone, development)
 - operating system and os version
"""
import time
import datetime
import re

import psycopg2
import psycopg2.extras

import socorro.lib.util as soc_util

configTable = 'product_visibility'

def calculateMtbf(configContext, logger, **kwargs):
  """
  Extract data from reports into time_before_failure
  kwargs options beat configContext, and within those two:
   - slotSizeMinutes is the number of minutes for this calculation slot. Default: One day's worth
   - slotEnd is the moment past the end of the calculation slot.
   - processingDay (old style): the calculation slot starts at midnight and ends just before next midnight

   You may limit the calculation with one or more of the following:
   - product: name the product to be looked at
   - version: name the version of the product to be looked at
   - os_name: name the OS to be looked at
   - os_version: name the version of the OS to be looked at
  """
  try:
    databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    conn = psycopg2.connect(databaseDSN)
    cur = conn.cursor()
  except:
    soc_util.reportExceptionAndAbort(logger)
  oneDay = datetime.timedelta(days=1)
  # If we specify slotSizeMinutes, use that interval, else use 1 day
  if kwargs and 'slotSizeMinutes' in kwargs:
    slotInterval = datetime.timedelta(minutes = int(kwargs['slotSizeMinutes']))
  elif 'slotSizeMinutes' in configContext:
    slotInterval = datetime.timedelta(minutes = int(configContext.slotSizeMinutes))
  else:
    slotInterval = oneDay
  # If we have slotEnd, it wins:
  if kwargs and 'slotEnd' in kwargs:
    eWindow = soc_util.parseIsoDateTimeString("%s"%(kwargs['slotEnd']))
  elif 'slotEnd' in configContext:
    eWindow = soc_util.parseIsoDateTimeString("%s"%(configContext.slotEnd))
    # If no slotEnd and we have the old processing day, then use it
  else:
    if kwargs and 'processingDay' in kwargs:
      aDay = soc_util.parseIsoDateTimeString("%s"%(kwargs.get('processingDay')))
    else:
      aDay = soc_util.parseIsoDateTimeString("%s"%(configContext.processingDay))
    assert oneDay == slotInterval, 'If you specify "processingDay", then slot size must be one day'
    eWindow = aDay.replace(hour=0,minute=0,second=0,microsecond=0)+slotInterval
  sWindow = eWindow - slotInterval
  sqlDict = {
    'configTable': configTable, 'startDate':'start_date', 'endDate':'end_date',
    'windowStart':sWindow, 'windowEnd':eWindow, 'windowSize':slotInterval,
    }
  extraWhereClause = ''
  if kwargs:
    specs = []
    if 'product' in kwargs:
      specs.append('p.product = %(product)s')
      sqlDict['product'] = kwargs['product']
    elif 'product' in configContext and configContext.product: # ignore empty
      specs.append('p.product = %(product)s')
      sqlDict['product'] = configContext.product
    if 'version' in kwargs:
      specs.append('p.version = %(version)s')
      sqlDict['version'] = kwargs['version']
    elif 'version' in configContext and configContext.version: # ignore empty
      specs.append('p.version = %(version)s')
      sqlDict['version'] = configContext.version
    if 'os_name' in kwargs:
      specs.append('o.os_name = %(os_name)s')
      sqlDict['os_name'] = kwargs['os_name']
    elif 'os_name' in configContext and configContext.os_name: # ignore empty
      specs.append('o.os_name = %(os_name)s')
      sqlDict['os_name'] = configContext.os_name
    if 'os_version' in kwargs:
      specs.append('o.os_version = %(os_version)s')
      sqlDict['os_version'] = kwargs['os_version']
    elif 'os_version' in configContext and configContext.os_version: # ignore empty
      specs.append('o.os_version = %(os_version)s')
      sqlDict['os_version'] = configContext.os_version
    if specs:
      extraWhereClause = ' AND '+' AND '.join(specs)
  sqlDict['extraWhereClause'] = extraWhereClause
  # per ss: mtbf runs for 60 days from the time it starts: Ignore cfg.end
  sql = """INSERT INTO time_before_failure (sum_uptime_seconds, report_count, productdims_id, osdims_id, window_end, window_size)
              SELECT SUM(r.uptime) AS sum_uptime_seconds,
                     COUNT(r.*) AS report_count,
                     p.id,
                     o.id,
                     timestamp %%(windowEnd)s,
                     interval %%(windowSize)s
                 FROM reports r JOIN productdims p ON r.product = p.product AND r.version = p.version
                                JOIN osdims o on r.os_name = o.os_name AND r.os_version = o.os_version
                                JOIN %(configTable)s cfg ON p.id = productdims_id
              WHERE NOT cfg.ignore
                 AND cfg.%(startDate)s <= %%(windowStart)s
              -- AND %%(windowStart)s <= cfg.%(endDate)s  -- ignored per ss
                 AND %%(windowStart)s <= cfg.%(startDate)s+interval '60 days' -- per ss
                 AND %%(windowStart)s <= r.date_processed AND r.date_processed < %%(windowEnd)s
                 %(extraWhereClause)s
              GROUP BY p.id, o.id
        """%(sqlDict)
  try:
    cur.execute(sql,sqlDict)
    conn.commit()
  except Exception,x:
    # if the inner select has no matches then AVG(uptime) is null, thus violating the avg_seconds not-null constraint.
    # This is good, we depend on this to keep
    # facts with 0 out of db
    # For properly configured products, this shouldn't happen very often
    logger.warn("No facts aggregated for day %s"%aDay)
    conn.rollback()

def processIntervals(configContext, logger, **kwargs):
  """
  call calculateMtbf repeatedly for each slot in the provided range preferring config data in this order:
   from startDate /else/ processingDay /else/ slotEnd - slotSize
     if startDate: to endDate /else/ midnight before now()
     if processingDay: to end of processingDay
     if slotEnd: to slotEnd
  Other kwargs/context values are passed unchanged to calculateMtbf
  """
  context = {}
  context.update(configContext)
  context.update(kwargs)
  slotSizeMinutes = context.get('slotSizeMinutes',24*60)
  slotSize = datetime.timedelta(minutes=slotSizeMinutes)
  startDate = context.get('startDate')
  processingDay = context.get('processingDay')
  slotEnd = context.get('slotEnd')
  if startDate:
    endDate = context.get('endDate')
    if not endDate:
      myMidnight = datetime.datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
      endDate = myMidnight - datetime.deltatime(days=1)
  elif processingDay:
    startDate = datetime.datetime.fromtimestamp(time.mktime(processingDay.timetuple()))
    endDate = startDate + datetime.deltatime(days=1)
  elif slotEnd:
    startDate = slotEnd - datetime.deltatime(minutes=slotSizeMinutes)
  else:
    logger.warn("Must provide startDate or processingDay or slotEnd. Quitting")
    return 0

  slotEnd = startDate + slotSize
  kwargs.setdefault('slotSizeMinutes',slotSizeMinutes)
  count = 0
  while slotEnd < endDate:
    kwargs['slotEnd'] = slotEnd
    calculateMtbf(configContext,logger,**kwargs)
    slotEnd += slotSize
    count += 1
  return count

def getProductsToUpdate(cur, conf, logger):
  params = {
    'configTable': configTable, 'startDate':'start_date', 'endDate':'end_date',
    }
  sql = "SELECT DISTINCT productdims_id FROM %(configTable)s WHERE %(startDate)s <= %%s AND %(endDate)s >= %%s;"%(params)
  try:
    logger.debug(sql % (conf.processingDay, conf.processingDay))
    cur.execute(sql, (conf.processingDay, conf.processingDay))
    rows = cur.fetchall()
  except Exception,x:
    soc_util.reportExceptionAndAbort(logger)
  
  if rows:
    #TODO log info
    ids = '(%s)'%(','.join(str(x[0]) for x in rows))
    sql = "SELECT p.id, p.product, p.version, p.release FROM productdims as p WHERE p.id IN %s"%(str(ids))
    logger.info(sql);
    cur.execute(sql);
    products = []
    for row in cur.fetchall():
      products.append( ProductAndOsData(row, logger) )
    return products
  else:
    logger.warn("Currently there are no MTBF products configured")
    return []
    
def getWhereClauseFor(product):
    "Order of criteria is significant to query performance... version then product then os_name"
    criteria = []
    if product.get('version','ALL') != "ALL":
      criteria.append("version = '%s'" % (product.get('version','unknownversion')))
    if product.get('product','ALL') != "ALL":
      criteria.append("product = '%s'" % (product.get('product','unknownproduct')))
    osName = product.get('os_name','ALL')
    if product.get('os_version','ALL') != "ALL":
      versionchunks = product.get('os_version','unknownos_version').split()
      if 1 == len(versionchunks) and versionchunks[0]:
        criteria.append("os_version = '%s'"%versionchunks[0])
      else:
        significant = None
        startIndex = 1
        for s in versionchunks:
          if '0.0.0' == s:
            startIndex += 1+len(s)
            continue
          elif osName.lower() == s.lower():
            startIndex += 1+len(s)
            continue
          significant = s
          break
        if significant:
          criteria.append("substr(os_version, %d, %d) = '%s'" % (startIndex,len(significant),significant))
    if osName != "ALL":
      criteria.append("substr(os_name, 1, 3) = '%s'" % osName.lower()[:3])
    if criteria:
      return " AND " + ' AND '.join(criteria) + " "
    else:
      return ''

class ProductAndOsData(dict):
  def __init__ (self, data, logger=None, **kwargs):
    """Constructor requires an array with 4 elements, corrosponding to the columns of the productdims table.
       If array instead has 7 elements, then the final 3 elemets are columns of the osdims table.      
       data - [product_id, product, version, release, os_id, os_name, os_version] where
       product - the name of a product. Ex: Firefox
       version - the numeric version. Ex: 3.0.5 or 3.5b4
       release - A build release level. One of ALL, major, milestone, or development
       os_name and os_version are as provided by the system
    """
    super(ProductAndOsData, self).__init__()
    if(logger):
      logger.info(data)
    self.product_id = data[0]
    self.product = data[1]
    self.version = data[2]
    self.release = data[3]
    if len(data) > 4:
      self.os_id = data[4]
      self.os_name = data[5]
      self.os_version = data[6]
    super(ProductAndOsData,self).update(kwargs)

  def __setattr__(self,name,value):
    self[name] = value

  def __getattr__(self,name):
    try:
      return self[name]
    except:
      super(ProductAndOsData, self).__getattr__(name)

  def __delattr__(self,name):
    del self[name]

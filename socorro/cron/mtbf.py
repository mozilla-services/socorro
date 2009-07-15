#!/usr/bin/python

"""
This script is what populates the mtbf facts table for the Mean Time Before failure report.

It will aggregate the previous days crash report informaiton, specifically the
average uptime, number of unique users, and number of reports. It does this across
products based on mtbfconfig for two dimensions - time and products.

The following fields are updated in mtbffacts table:
  id - primary key
  avg_seconds - average number of seconds (reports.uptime)
  report_count - number of crash reports
  unique_users - number of unique users
  day - the day for this time period (yesterday)
  productdims_id - foreign key reference into the product dimensions table
  
On the frontend various products from mtbfconfig are grouped into reports based on product and type of release.
active, release, and development.
 
Options:
-d, --processingDay
		Day to process in (YYYY-MM-DD) format. Defaults to yesterday.
  
"""
import time
import datetime

import psycopg2
import psycopg2.extras

import socorro.lib.util

def calculateMtbf(configContext, logger):
  try:
    databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    conn = psycopg2.connect(databaseDSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)
  products = getProductsToUpdate(cur, configContext, logger)
  aDay = datetime.date(*([int(x) for x in ("%s"%(configContext.processingDay)).split('-')][:3]))
  sDay = aDay
  eDay = aDay+datetime.timedelta(days=1)
  # half open interval starts at the beginning of the day ...
  dStart = aDay.isoformat()
  # ... and stops just before beginning of next day
  dEnd = (aDay + datetime.timedelta(days=1)).isoformat()
  for product in products:
    sql = """INSERT INTO mtbffacts (avg_seconds, report_count, day, productdims_id, osdims_id)
               SELECT AVG(r.uptime) AS avg_seconds, COUNT(r.*) AS report_count, DATE '%s', p.id, o.id -- << The day in question
                  FROM mtbfconfig cfg JOIN crash_reports r on cfg.osdims_id = r.osdims_id AND cfg.productdims_id = r.productdims_id
                  join productdims p on cfg.productdims_id = p.id
                  join osdims o on cfg.osdims_id = o.id
               WHERE r.date_processed >= %%(dStart)s
                 AND %%(dEnd)s > r.date_processed
               GROUP BY p.id, o.id
          """%(aDay)
    try:
      cur.execute(sql,({'dStart':sDay,'dEnd':eDay}))
      conn.commit()
    except Exception,x:
      # if the inner select has no matches then AVG(uptime) is null, thus violating the avg_seconds not-null constraint.
      # This is good, we depend on this to keep
      # facts with 0 out of db
      # For properly configured products, this shouldn't happen very often
      logger.warn("No facts generated for %s %s os=%s",product.get('product'), product.get('version'), product.get('os_name'));
      conn.rollback() 

def getProductsToUpdate(cur, conf, logger):
  sql = "SELECT productdims_id, osdims_id FROM mtbfconfig WHERE start_dt <= %s AND end_dt >= %s;"
  try:
    logger.debug(sql % (conf.processingDay, conf.processingDay))
    cur.execute(sql, (conf.processingDay, conf.processingDay))
    rows = cur.fetchall()
  except Exception,x:
    socorro.lib.util.reportExceptionAndAbort(logger)
    
  if rows:
    #TODO log info
    idpairs = tuple((str(x[0]),str(x[1])) for x in rows)
    sql = "SELECT p.id, p.product, p.version, p.release, o.id, o.os_name, o.os_version FROM productdims as p, osdims as o  WHERE (p.id, o.id) IN %s"%(str(idpairs))
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
    """Constructor requires an array with 7 elements, corrosponding to the columns of the productdims and osdims tables.
       data - [product_id, product, version, release, os_id, os_name, os_version] where
       product - the name of a product. Ex: Firefox
       version - the numeric version. Ex: 3.0.5 or 3.5b4
       release - A build release level. One of ALL, major, milestone, or development
       os_name - As we get it from the crash report. Ex: 'Windows NT'
       os_version - As we get it from the crash report
    """
    super(ProductAndOsData, self).__init__()
    if(logger):
      logger.info(data)
    self.product_id = data[0]
    self.product = data[1]
    self.version = data[2]
    self.release = data[3]
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

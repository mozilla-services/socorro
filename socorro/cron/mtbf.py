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
  window_end - the end point of the aggregation window. By default, midnight 00:00:00 of 'tomorrow'
  window_size - the size of the aggregation window. By default 1 day. The window is (end - size) <= x < end
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

import socorro.database.cachedIdAccess as socorro_cia
import socorro.lib.util as soc_util
import socorro.cron.util as cron_util

configTable = 'product_visibility'
resultTable = 'time_before_failure'

def processOneMtbfWindow(configContext, logger, **kwargs):
  """
  Extract data from reports into time_before_failure
  kwargs options beat configContext, and within those two:
   - intervalSizeMinutes is the number of minutes for this calculation interval. Default: One day's worth
   - intervalEnd is the moment past the end of the calculation interval.
   - processingDay (old style): the interval starts at midnight of the day, ends prior to next midnight

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
  startWindow,deltaWindow,endWindow = cron_util.getProcessingWindow(configContext,resultTable,cur,logger,**kwargs)
  sqlDict = {
    'configTable': configTable, 'startDate':'start_date', 'endDate':'end_date',
    'windowStart':startWindow, 'windowEnd':endWindow, 'windowSize':deltaWindow,
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
      specs.append('r.os_name = %(os_name)s')
      sqlDict['os_name'] = kwargs['os_name']
    elif 'os_name' in configContext and configContext.os_name: # ignore empty
      specs.append('r.os_name = %(os_name)s')
      sqlDict['os_name'] = configContext.os_name
    if 'os_version' in kwargs:
      specs.append('r.os_version LIKE %(os_version)s')
      sqlDict['os_version'] = "%%%s%%"%(kwargs['os_version'])
    elif 'os_version' in configContext and configContext.os_version: # ignore empty
      specs.append('r.os_version LIKE %(os_version)s')
      sqlDict['os_version'] = "%%%s%%"%(configContext.os_version)
    if specs:
      extraWhereClause = ' AND '+' AND '.join(specs)
  sqlDict['extraWhereClause'] = extraWhereClause
  # per ss: mtbf runs for 60 days from the time it starts: Ignore cfg.end
  sql = """SELECT SUM(r.uptime) AS sum_uptime_seconds,
                  COUNT(r.*) AS report_count,
                  p.id,
                  -- o.id, -- would go here
                  timestamp %%(windowEnd)s,
                  interval %%(windowSize)s,
                  r.os_name,
                  r.os_version
           FROM reports r JOIN productdims p ON r.product = p.product AND r.version = p.version
                          JOIN %(configTable)s cfg ON p.id = productdims_id
           WHERE NOT cfg.ignore
                 AND cfg.%(startDate)s <= %%(windowStart)s
                 AND %%(windowStart)s <= cfg.%(startDate)s+interval '60 days' -- per ss
                 AND %%(windowStart)s <= r.date_processed AND r.date_processed < %%(windowEnd)s
                 %(extraWhereClause)s
              GROUP BY p.id, r.os_name,r.os_version
        """%(sqlDict)
  inSql = """INSERT INTO %s
                  (sum_uptime_seconds, report_count, productdims_id, osdims_id, window_end, window_size)
            VALUES(%%s,%%s,%%s,%%s,%%s,%%s)"""%resultTable
  try:
    idCache = socorro_cia.IdCache(cur)
    cur.execute(sql,sqlDict)
    conn.rollback()
    data = cur.fetchall()
    idData = [ [d[0],d[1],d[2],idCache.getOsId(d[5],d[6]),d[3],d[4]] for d in data ]
    cur.executemany(inSql,idData)
    conn.commit()

  except psycopg2.IntegrityError,x:
    # if the inner select has no matches then AVG(uptime) is null, thus violating the avg_seconds not-null constraint.
    # This is good, we depend on this to keep
    # facts with 0 out of db
    # For properly configured products, this shouldn't happen very often
    conn.rollback()
    logger.warn("No facts aggregated for day %s"%sWindow)
  except Exception:
    conn.rollback()
    soc_util.reportExceptionAndContinue(logger)

def processDateInterval(configContext, logger, **kwargs):
  """
  call processOneMtbfWindow repeatedly for each window in the range defined by at least two paramerters among (start|delta|end)Date
  Other kwargs/context values are passed unchanged to processOneMtbfWindow
  """
  databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
  conn = psycopg2.connect(databaseDSN)
  cur = conn.cursor()
  now = datetime.datetime.now()
  startDate, deltaDate, endDate = cron_util.getProcessingDates(configContext,resultTable,cur,logger,**kwargs)
  startWindow,deltaWindow,endWindow = cron_util.getProcessingWindow(configContext,resultTable,cur,logger,**kwargs)
  if not startDate and not startWindow:
    logger.warn("MTBF (%s): No startDate, no startWindow. Did not run.",now)
    return 0
  if not startWindow: # we are guaranteed a startDate after the test above
    startWindow = startDate
  if not startDate or startDate > startWindow:
    startDate = startWindow
  if not deltaWindow:
    deltaWindow = datetime.timedelta(days=1)
  thisMidnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
  if not endDate or endDate > thisMidnight:
    endDate = thisMidnight
  if startDate + deltaWindow > endDate:
    logger.warn("MTBF (%s) startDate (%s) too close to endDate (%s). Did not run.",now, startDate,endDate)
    return 0
  count = 0
  kwargs['deltaWindow'] = deltaWindow
  startWindow = startDate
  while startWindow + deltaWindow < endDate:
    kwargs['startWindow'] = startWindow
    processOneMtbfWindow(configContext,logger,**kwargs)
    startWindow += deltaWindow
    count += 1
  return count

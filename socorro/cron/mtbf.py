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
  
  for product in products:
    aDay = configContext.processingDay
    start = "%s 00:00:00" % aDay
    end = "%s 23:59:59" % aDay
    sql = """/* soc.crn mtbf read/insert facts */
            INSERT INTO mtbffacts (avg_seconds, report_count, unique_users, day, productdims_id) 
              SELECT AVG(uptime) AS avg_seconds, 
                COUNT(date) AS report_count, COUNT(DISTINCT(user_id)) AS unique_users, DATE '%s', %d
              FROM reports  
              WHERE date >= TIMESTAMP WITHOUT TIME ZONE '%s' 
                AND date <= TIMESTAMP WITHOUT TIME ZONE '%s' %s
              """ % (aDay, product.dimensionId, start, end, getWhereClauseFor(product))
    try:
      logger.info(sql)
      cur.execute(sql)
      logger.info("Commiting results")
      conn.commit()
    except psycopg2.IntegrityError, e:
      # if the inner select has no matches then AVG(uptime) is null, thus violating the avg_seconds not-null constraint.
      # This is good, we depend on this to keep
      # facts with 0 out of db
      # For properly configured products, this shouldn't happen very often
      logger.warn("No facts generated for %s %s os=%s. Expected error [%s]" % (product.product, product.version, product.os_name, e));
      conn.rollback()  

def getProductsToUpdate(cur, conf, logger):
  sql = "/* soc.crn mtbf config */ SELECT productdims_id FROM mtbfconfig WHERE start_dt <= %s AND end_dt >= %s;"
        
  try:
    logger.debug(sql % (conf.processingDay, conf.processingDay))
    cur.execute(sql, (conf.processingDay, conf.processingDay))
    rows = cur.fetchall()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)
    
  if rows:
    #TODO log info
    ids = []
    for row in rows:
      #todo use ['id'] or whatever instead of index
      ids.append( str(row[0]) )
    sql = "/* soc.crn mtbf get prod dim */ SELECT id, product, version, os_name, release FROM productdims WHERE id IN (%s)" % (', '.join( ids ))
    logger.info(sql);
    cur.execute(sql);
    products = []
    for row in cur.fetchall():
      products.append( ProductDimension(row, logger) )
    return products
  else:
    logger.warn("Currently there are no MTBF products configured")
    return []
    
def getWhereClauseFor(product):
    "Order of criteria is significant to query performance... version then product then os_name"
    criteria = []
    if product.product == "ALL":
        return ""
    else:
      if product.version != "ALL":
        criteria.append("version = '%s'" % (product.version))
      criteria.append("product = '%s'" % (product.product))
      if product.os_name != "ALL":
          criteria.append("substr(os_name, 1, 3) = '%s'" % (product.os_name))
      return " AND " + ' AND '.join(criteria) + " "

class ProductDimension:
  def __init__ (self, config, logger=None):
    """Constructor requires an array with 5 elements, corrosponding to the columns of the productdims table.
       config - [id, product, version, os_name, release] where
       product - the name of a product. Ex: Firefox
       os_name - Win, Mac, etc
       release - A build release level. One of ALL, major, milestone, or development
    """
    if(logger):
      logger.info(config)
    self.dimensionId = config[0]
    self.product = config[1]
    self.version = config[2]
    self.os_name = config[3]
    self.release = config[4] 

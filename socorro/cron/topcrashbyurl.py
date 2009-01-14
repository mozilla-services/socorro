#!/usr/bin/python

"""
This script is what populates the topcrashurlfacts facts table for the Top Crashers By Url report

This fact table contains crash count and rank facts from a couple of dimensions
* Products - Versions level
* Urls - Domain (course) and Url (finer)
** Domain is calculated only against signature.ALL
* Signatures - ALL (course) and Each (finer)
** Each is calculated only against Urls.Url
* Days - Each Day

This table allows two style of drilling down and conversly rolling up.

ALL Domain -> All URLs (for a domain) -> ALL Signatures (for a url)

All URLs -> ALL Signatures (for a url)  

The following fields are updated in topcrashurlfacts table based on given dimensions:
  id - primary key
  count - aggregate number of crashes [1]
  rank - This crashes current rank 
  day - day the crashes where processed on ( usually yesterday when cron is run )  
  productdims_id - foreign key reference into the product dimensions table  
  urldims_id - foreign key reference into the product dimensions table  
  signaturedims_id - foreign key reference into the product dimensions table

[1] - Some filtering takes plus including
* Urls with no domain such as 'about:crashes'
* Empty or null urls
* Empty or null signatures

TODO: BUG - duplicate urldims! No results for this url in facts table sig !=1
select * from urldims
WHERE urldims.url = 'http://home.myspace.com/index.cfm' ;

select * from topcrashurlfacts 
JOIN signaturedims ON topcrashurlfacts.signaturedims_id = signaturedims.id
WHERE urldims_id IN (
select id from urldims
WHERE urldims.url = 'http://home.myspace.com/index.cfm' 
) AND signaturedims.id != 1;

TODO: delete from facts table old facts
TODO: delete from dimension table unused dimensions
 
Options:
-d, --processingDay
		Day to process in (YYYY-MM-DD) format. Defaults to yesterday.
  
"""
import time
import datetime

import psycopg2
import psycopg2.extras

import socorro.lib.util

def populateALLFacts(configContext, logger):
  try:
    databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    conn = psycopg2.connect(databaseDSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

  staticDimensions = {'date': configContext.processingDay }
  staticDimensions['start_date'] = "%s 00:00:00" % (configContext.processingDay)
  staticDimensions['end_date']   = "%s 23:59:59" % (configContext.processingDay)

  products = getProductDimensions(cur, logger)
  for product in products:
    staticProdDims = staticDimensions.copy()
    staticProdDims.update({'signature_id': 1, 'product_id': product['id'], 'product_name': product['name'], 'product_version': product['version'] })
    populateFactsForDim(ByUrlDomain(), staticProdDims, conn, cur, logger)
    logger.info("Finished populateFactsForDim for urlByDomain(%s)" % (product['name']))
    populateFactsForDim(ByUrlEachUrl(), staticProdDims, conn, cur, logger)
    logger.info("Finished populateFactsForDim for urlByUrl(%s)" % (product['name']))
  for product in products:
    urls = getUrlDimensions(product['id'], staticDimensions, cur, logger)
    logger.info("About to process %s urls for their signatues" % (len(urls)))
    c = 0
    for url in urls:
      c += 1
      if (c % 500) == 0:
        logger.info("Progress processed %s of %s" % (c, len(urls)))
      staticUrlDims = staticDimensions.copy()
      staticUrlDims.update({'product_id': product['id'], 'product_name': product['name'], 'product_version': product['version'], 'urldims_id': url['id'], 'urldims_url': url['url'] })
      populateFactsForDim(BySignature(), staticUrlDims, conn, cur, logger)    
      #logger.info("Finished populateFactsForDim for urlByUrl(%s, %s)" % (product['name'], url['url']))
    staticSigDims = staticDimensions.copy()
    staticSigDims['product_id'] = product['id']
    staticSigDims['product_name'] = product['name']
    staticSigDims['product_version'] = product['version']
    populateRelatedTables(staticSigDims, conn, cur, logger)

def populateRelatedTables(context, conn, readCur, logger):
  factUrlSigMap = getFactsUrlSigMap(context, conn, readCur, logger)
  selSql = """
        SELECT uuid, comments, signature, url
        FROM reports 
        WHERE TIMESTAMP WITHOUT TIME ZONE %(start_date)s <= date_processed
          AND date_processed <= TIMESTAMP WITHOUT TIME ZONE %(end_date)s
          AND comments IS NOT NULL AND url IS NOT NULL AND signature IS NOT NULL 
          AND comments != ''       AND url != ''       AND signature != '' 
          AND product = %(product_name)s AND version = %(product_version)s """
  logger.info("About to execute %s with %s" % (selSql, context))
  readCur.execute(selSql, context)
  logger.info("Finished affecting %s rows" % (readCur.rowcount))
  rows = readCur.fetchall()
  data = []
  for row in rows:
    try:
      aUrl = url(row['url'])
      d = {'uuid': row['uuid'], 'comments': row['comments'], 'fact_id': factUrlSigMap[aUrl][row['signature']]}
      data.append(d)
    except KeyError:
      pass # A comment for a fact we haven't recorded. Example - a product/url/signature with only 1 crash
    except:
      logger.info("Error populating related table for %s " % (row))
      socorro.lib.util.reportExceptionAndContinue(logger)

  insSel = """/* soc.crn tcburl insr crash comm */
        INSERT INTO topcrashurlfactsreports (uuid, comments, topcrashurlfacts_id)
        VALUES (%(uuid)s, %(comments)s, %(fact_id)s) """
  readCur.executemany(insSel, data)
  conn.commit()

def getFactsUrlSigMap(context, conn, cur, logger):
  """ This map caches db ids for the facts table which will be too expensive 
      to retrieve when created the topcrashurlfactsreports table it is in the form of 
  { 'http://www.example.com/foo':
     { 'nsJSChannel::Init(nsIURI*)': 12345 } 
  }
      where 12345 is the topcrashbyurl.id
"""
  sql = """
        SELECT topcrashurlfacts.id, count, urldims.url, signaturedims.signature
        FROM topcrashurlfacts 
        JOIN urldims ON urldims_id = urldims.id
        JOIN signaturedims ON signaturedims_id = signaturedims.id
        JOIN productdims ON productdims_id = productdims.id
        WHERE topcrashurlfacts.day = %(date)s
          AND productdims.product = %(product_name)s AND productdims.version = %(product_version)s
          AND topcrashurlfacts.signaturedims_id != 1 
          AND urldims.url != 'ALL' """
  cur.execute(sql, context)
  rows = cur.fetchall()
  urlSigMap = {}
  for row in rows:
    try:
      if not urlSigMap.has_key(row['url']):
        urlSigMap[row['url']] = {}
      urlSigMap[row['url']][row['signature']] = row['id']
    except:
      logger.info("Error getFactsUrlSigMap for %s " % (row))
      socorro.lib.util.reportExceptionAndContinue(logger)
  return urlSigMap

def getProductDimensions(cur, logger):
  try:
    sql = """/* soc.crn tcburl get prodconf */ 
        SELECT productdims_id AS id, product AS name, version
        FROM tcbyurlconfig JOIN productdims ON tcbyurlconfig.productdims_id = productdims.id
        WHERE enabled = 'Y' """
    cur.execute(sql)
    return cur.fetchall()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

def getUrlDimensions(productId, staticDimensions, cur, logger):
  " Grab all the urls that had facts earlier. This wil cause us to processs say another 5000 records "
  try:
    sql = """ /* soc.crn tcburl get urls wcrsh */
          SELECT  urldims.id, urldims.url FROM urldims
          JOIN topcrashurlfacts AS facts ON urldims.id = facts.urldims_id
          WHERE '%s' <= facts.day AND facts.day <= '%s'
            AND productdims_id = %s AND url != 'ALL' """
    cur.execute(sql % (staticDimensions['start_date'], staticDimensions['end_date'], productId))
    return cur.fetchall()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)
  
def domain(url):
  "Behavior is the same as Postgres SQL used for report.url -> urldims.domain"
  try:
    return url.split('/')[2]
  except IndexError:
    return ""
def url(url):
  "Behavior is the same as Postgres SQL used for report.url -> urldims.url"
  try:
    return url.split('?')[0]
  except IndexError:
    return ""

def populateFactsForDim(dimension, staticDimensions, conn, cur, logger):
  """For the given dimension, read operational DB. Aggregate facts. 
     Make sure we have dimension properties ready, then add new
     facts to the fact table. This is for a single level of granularity
     in the dimension"""
  propertyName = dimension.level()
  rs = dimension.aggregateFacts(staticDimensions, cur, logger)

  dimValues = map( lambda x: x[propertyName], rs )
  #TODO perf do we get called with empty dimIdMap? Why?
  #if len(dimensionIdMap) == 0:
  #  logger.warn("========== dimensionIdMap %s ============ for %s =====" % (dimensionIdMap, propertyName))
  #TODO perf cache known values in weak memory reference
  dimensionIdMap = ensureDimensionExist(conn, cur, dimension, propertyName, dimValues, logger )
  facts = prepareFacts(rs, propertyName, dimensionIdMap, staticDimensions, logger) 
  insertFacts(conn, cur, facts, rs, logger)

#TODO rename domains to dimIdMap
#Rewrite for clarity - process keys and then copy fact[propertyName] = dimIdMap[propertyName]
def prepareFacts(rows, propertyName, propertyToDimIdMap, staticDimensions, logger):
  """ Given a set of facts which we want to populate the facts table with, 
      associate them with their lookup dimensions. Some of these are static and one of them varies
      across the facts.

      rows - a resultset with domain and crash_count
      propertyName - the 1 property which varies
      propertyToDimIdMap - a mapping from a property's name to the property's dimension id 
      staticDimensions - the unchaning dimension properties associated with this fact
      
      Returns a list of dict obejcts suitable for use with executemany. """
  facts = []
  i = 0
  for row in rows:
    i += 1
    try:
      fact = {'rank': int(i), 'crash_count': int(row['crash_count']), 'day': staticDimensions['date']}       
      fact['product_id'] = int(staticDimensions['product_id']) 
      if staticDimensions.has_key('urldims_id'):
        fact['urldims_id'] = int(staticDimensions['urldims_id'])
      else:
        fact['urldims_id'] = int(propertyToDimIdMap[row[propertyName]])
      if staticDimensions.has_key('signature_id'):
        fact['signature_id'] = int(staticDimensions['signature_id'])
      else:
        fact['signature_id'] = propertyToDimIdMap[row[propertyName]]
      facts.append(fact)
    except StandardError, e:
      i -= 1
      logger.warn("There was an error while preparing this fact %s %s" % (propertyName, staticDimensions))
      socorro.lib.util.reportExceptionAndContinue(logger)

  return facts

def insertFacts(conn, cur, facts, rs, logger):
  "Takes a list of fact dictionaries and populates the database. "
  inSql = """/* soc.crn tcburl ins urlfacts */
             INSERT INTO topcrashurlfacts (count, rank, day, productdims_id, urldims_id, signaturedims_id)
             VALUES (%(crash_count)s, %(rank)s, %(day)s, %(product_id)s, %(urldims_id)s, %(signature_id)s)"""
  
  cur.executemany(inSql, facts)
  conn.commit()

def ensureDimensionExist(conn, cur, dimension, propertyName, propertyList, logger):
  rows = dimension.fetchProps(propertyList, cur, logger)
  oldProps = {}
  for row in rows:
    oldProps[row[propertyName]] = row['id']

  # for each property, if it isn't in results, then add it to DB
  newProps = []
  newPropsSeen = {}
  for prop in propertyList:
    if not oldProps.has_key(prop) and not newPropsSeen.has_key(prop):
      #logger.info("We haven't seen %s before" % (prop))
      newProp = {propertyName: prop}
      dimension.prepareNewProp(newProp, prop, logger)
      newProps.append(newProp)
      newPropsSeen[prop] = True
    #else:
      #if propertyName == 'signature':
        #logger.info("We've already seen %s before, it's %s" % (prop, oldProps[prop]))

  if len( newProps ) == 0:
    #logger.info("All values already in dim table for %s" % (propertyName))
    return oldProps
  else:
    dimension.insertNewProps(conn, cur, newProps, logger)
    rows = dimension.fetchProps(map( lambda x: x[propertyName], newProps), cur, logger)
    for row in rows:
      oldProps[row[propertyName]] = row['id']
      
    return oldProps

class ByUrlDomain:
  #'domain', getResultsByDomain, fetchDomainsFromDB, insertDomainsToDB
  def level(self):
    return 'domain'
  def aggregateFacts(self, staticDimensions, cur, logger):
    #rank is accomplished via ORDER BY here...
    # about:blank is the #1 crashing url, but it isn't really an intereting url...
    sql = """/* soc.crn tcburl top domain */
             SELECT count(id) as crash_count, split_part(url, '/', 3) AS domain 
             FROM reports WHERE TIMESTAMP WITHOUT TIME ZONE %(start_date)s <= date_processed
             AND  date_processed <= TIMESTAMP WITHOUT TIME ZONE %(end_date)s 
             AND product = %(product_name)s AND version = %(product_version)s
             AND url IS NOT NULL AND url != ''
             AND signature IS NOT NULL AND signature != ''
             GROUP BY domain
             HAVING count(id) > 1
             ORDER BY crash_count DESC;"""
    try:
      logger.info("about to execute ByDomain")
      cur.execute(sql, staticDimensions)
      logger.info("executed %s with %s" % (sql, staticDimensions))
      logger.info("affecting %s rows" % (cur.rowcount))
      rs = cur.fetchall()
      return filter(lambda row: row['domain'] != '', rs)
    except StandardError, e:
      logger.warn("There was an error during aggregateFacts by domain with %s" % (staticDimensions))
      socorro.lib.util.reportExceptionAndContinue(logger)
      

  def fetchProps(self, domains, cur, logger):
    """
      fetches the domains that exist in the db
      domains - a list of domain names like www.example.com. Some may exist, some not
  
      returns all of the domains with their ids, if they were found in the urldims table.
  
      TODO check domains in chunks of 500...
    """
    selSql = """/* soc.crn tcburl sel domaindim */
          SELECT id, domain FROM urldims WHERE url = 'ALL' AND domain IN ('%s')
          """
    try:
      cur.execute( selSql % "', '".join(domains))
      return cur.fetchall()
    except:
      socorro.lib.util.reportExceptionAndAbort(logger)

  def prepareNewProp(self, newProp, value, logger):
    pass

  def insertNewProps(self, conn, cur, newValues, logger):
    "Takes a list of fact dictionaries and populates the database. "
    try:
      inSql = """/* soc.crn tcburl ins domaindim */
              INSERT INTO urldims (domain, url) VALUES ( %(domain)s, 'ALL')"""
      cur.executemany(inSql, newValues)
      conn.commit()
    except:
      socorro.lib.util.reportExceptionAndAbort(logger)

class ByUrlEachUrl:
  def level(self):
    return 'url'
  def aggregateFacts(self, staticDimensions, cur, logger):
    #rank is accomplished via ORDER BY here...
    sql = """/* soc.crn tcburl top domain */
             SELECT COUNT(id) AS crash_count,  split_part(url, '?', 1) AS url from reports 
             WHERE TIMESTAMP WITHOUT TIME ZONE %(start_date)s <= date_processed
             AND date_processed <= TIMESTAMP WITHOUT TIME ZONE %(end_date)s
             AND product = %(product_name)s AND version = %(product_version)s 
             AND url IS NOT NULL AND url != ''
             AND signature IS NOT NULL AND signature != ''
             GROUP BY url
             HAVING COUNT(id) > 1
             ORDER BY crash_count DESC;
             """
    try:
      cur.execute(sql, staticDimensions)
      rs = cur.fetchall()
      return filter(lambda row: domain(row['url']) != '', rs)
    except StandardError, e:
      logger.warn("There was an error during aggregateFacts by URL with %s" % (staticDimensions))
      socorro.lib.util.reportExceptionAndContinue(logger) 

  def fetchProps(self, urls, cur, logger):
    """
      fetches the urls that exist in the db
      urls - a list of urls (http://www.example.com/foo.html, some which may exists and some which do not.
  
      returns results set for urls in the urldims table and it's id
  
      TODO check urls in chunks of 500...
    """
    selSql = """/* soc.crn tcburl sel urlindim */
          SELECT id, url FROM urldims WHERE url IN ('%s');"""

    try:
      cur.execute( selSql % "', '".join(urls))
      return cur.fetchall()      
    except:
      socorro.lib.util.reportExceptionAndAbort(logger)

  def prepareNewProp(self, newProp, value, logger):
    newProp['domain'] = domain( value )

  def insertNewProps(self, conn, cur, newValues, logger):
    "Takes a list of fact dictionaries and populates the database. "
    try:
      inSql = """/* soc.crn tcburl ins url domaindim */
              INSERT INTO urldims (domain, url) VALUES ( %(domain)s, %(url)s)"""
      cur.executemany(inSql, newValues)
      conn.commit()
    except:
      socorro.lib.util.reportExceptionAndAbort(logger)

class BySignature:
  def level(self):
    return 'signature'
  def aggregateFacts(self, staticDimensions, cur, logger):
    #rank is accomplished via ORDER BY here...
    # Would it be more efficient to do a couple Sigs at a time...?
    sql = """/* soc.crn tcburl top sign */
             SELECT COUNT(id) AS crash_count, signature from reports 
             WHERE TIMESTAMP WITHOUT TIME ZONE %(start_date)s <= date_processed
             AND date_processed <= TIMESTAMP WITHOUT TIME ZONE %(end_date)s
             AND product = %(product_name)s AND version = %(product_version)s AND url = %(urldims_url)s 
             AND signature IS NOT NULL AND signature != ''
             GROUP BY signature
             HAVING COUNT(id) > 1
             ORDER BY crash_count DESC;
             """ 
    try:
      cur.execute(sql, staticDimensions)
      rs = cur.fetchall()
      return rs
    except StandardError, e:
      logger.warn("There was an error during aggregateFacts by Signature with %s" % (staticDimensions))
      socorro.lib.util.reportExceptionAndContinue(logger) 

  def fetchProps(self, signatures, cur, logger):
    """
      fetches the signatures that exist in the db
      signatures - a list of crash sigs, so may exist, some not
  
      returns result set with keys id, signature for values dimension values that already exist in the DB
  
      TODO check signature in chunks of 500...
    """
    selSql = """/* soc.crn tcburl sel urlindim */
          SELECT id, signature FROM signaturedims WHERE signature IN ('%s');"""

    try:
      escapedSigs = map( lambda s: s.replace("'", "\\'"), signatures)
      cur.execute( selSql % "', '".join(escapedSigs))
      return cur.fetchall()      
    except:
      socorro.lib.util.reportExceptionAndAbort(logger)

  def prepareNewProp(self, newProp, value, logger):
    pass

  def insertNewProps(self, conn, cur, newValues, logger):
    "Takes a list of fact dictionaries and populates the database. "
    try:
      inSql = """/* soc.crn tcburl ins sign signaturedims */
              INSERT INTO signaturedims (signature) VALUES ( %(signature)s ) """
      cur.executemany(inSql, newValues)
      conn.commit()
    except:
      socorro.lib.util.reportExceptionAndAbort(logger)

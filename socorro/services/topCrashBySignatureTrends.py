import logging
logger = logging.getLogger("webapi")

import socorro.database.database as db
import socorro.webapi.webapiService as webapi
import socorro.lib.util as util
import socorro.lib.datetimeutil as dtutil

import socorro.services.tcbs.modern as modern
import socorro.services.tcbs.classic as classic

import psycopg2.extras as psyext

import datetime
import web

# theoretical sample output
#  [ [ (key, rank, rankDelta, ...), ... ], ... ]
#{
  #"resource": "http://socorro.mozilla.org/trends/topcrashes/bysig/Firefox/
  #               3.5.3/from/2009-10-03/to/2009-10-13/page/0",
  #"page": "0",
  #"previous": "null",
  #"next": "http://socorro.mozilla.org/trends/topcrashes/bysig/Firefox/
  #             3.5.3/from/2009-10-03/to/2009-10-13/page/0",
  #"ranks":[
    #{"signature": "LdrAlternateResourcesEnabled",
    #"previousRank": 3,
    #"currentRank": 8,
    #"change": -5},
    #{"signature": "OtherSignature",
    #"previousRank": "null",
    #"currentRank": 10,
    #"change": 10}
    #],
#}

def whichTCBS(aCursor, dbParams, product, version):
  '''
  Answers a boolean indicating if the old top crashes by signature should
  be used.
  '''
  sql = """
        /* socorro.services.topCrashBySignatures useTCBSClassic */
        SELECT which_table
        FROM product_selector
        WHERE product_name = '%s' AND
              version_string = '%s'""" % (product, version)
  try:
    return db.singleValueSql(aCursor, sql, dbParams)
  except db.SQLDidNotReturnSingleValue:
    logger.info("No record in product_selector for %s %s."
      % (product, version))
    raise ValueError, "No record of %s %s" % (product, version)

class TopCrashBySignatureTrends(webapi.JsonServiceBase):
  def __init__(self, configContext):
    super(TopCrashBySignatureTrends, self).__init__(configContext)
    logger.debug('TopCrashBySignatureTrends __init__')

  uri = ('/topcrash/sig/trend/rank/p/(.*)/v/(.*)/type/(.*)/end/(.*)'
         '/duration/(.*)/listsize/(.*)')

  def get(self, *args):
    logger.debug('TopCrashBySignatureTrends get')
    convertedArgs = webapi.typeConversion([str, str, str,
                                          dtutil.datetimeFromISOdateString,
                                          dtutil.strHoursToTimeDelta, int],
                                          args)
    parameters = util.DotDict(zip(['product','version','crashType','endDate',
                                   'duration', 'listSize'], convertedArgs))
    logger.debug("TopCrashBySignatureTrends get %s", parameters)
    parameters.logger = logger
    parameters.productVersionCache = self.context['productVersionCache']
    product = parameters['product']
    version = parameters['version']
    try:
      connection = self.database.connection()
      cursor = connection.cursor()
      table_type = whichTCBS(cursor, {}, product, version)
      impl = {
        "old": classic,
        "new": modern,
      }
      return impl[table_type].twoPeriodTopCrasherComparison(cursor, parameters)
    finally:
      connection.close()


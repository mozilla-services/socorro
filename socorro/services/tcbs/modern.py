import logging
logger = logging.getLogger("webapi")

import socorro.database.database as db
import socorro.webapi.webapiService as webapi
import socorro.lib.util as util

import psycopg2.extensions as psyext2
import datetime

# theoretical sample output
#  [ [ (key, rank, rankDelta, ...), ... ], ... ]
#{
  #"resource": "http://socorro.mozilla.org/trends/topcrashes/bysig/"
  #            "Firefox/3.5.3/from/2009-10-03/to/2009-10-13/page/0",
  #"page": "0",
  #"previous": "null",
  #"next": "http://socorro.mozilla.org/trends/topcrashes/bysig/"
  #        "Firefox/3.5.3/from/2009-10-03/to/2009-10-13/page/0",
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

def getListOfTopCrashersBySignature(aCursor, dbParams):
  """
  Answers a generator of tcbs rows
  """
  assertPairs = {
    'startDate': (datetime.date, datetime.datetime),
    'endDate': (datetime.date, datetime.datetime),
    'product': basestring,
    'version': basestring,
    'listSize': int
  }

  for param in assertPairs:
    if not isinstance(dbParams[param], assertPairs[param]):
      raise ValueError(type(dbParams[param]))

  where = ""
  if dbParams['crashType'] != 'all':
    where = "AND process_type = '%s'" % (dbParams['crashType'],)

  sql = """
    WITH tcbs_r as (
    SELECT tcbs.signature_id,
        signature,
        pv.product_name,
        version_string,
        sum(report_count) as report_count,
        sum(win_count) as win_count,
        sum(lin_count) as lin_count,
        sum(mac_count) as mac_count,
        sum(hang_count) as hang_count,
        plugin_count(process_type,report_count) as plugin_count,
        content_count(process_type,report_count) as content_count,
        first_report,
        version_list
    FROM tcbs
      JOIN signatures USING (signature_id)
      JOIN product_versions AS pv USING (product_version_id)
      JOIN signature_products_rollup AS spr
        ON spr.signature_id = tcbs.signature_id
        AND spr.product_name = pv.product_name
    WHERE pv.product_name = '%s'
      AND version_string = '%s'
      AND report_date BETWEEN '%s' AND '%s'
      %s
    GROUP BY tcbs.signature_id, signature, pv.product_name, version_string, first_report, spr.version_list
    ),
    tcbs_window AS (
      SELECT tcbs_r.*,
      sum(report_count) over () as total_crashes,
          dense_rank() over (order by report_count desc) as ranking
      FROM
        tcbs_r
    )
    SELECT signature,
           report_count,
           win_count,
           lin_count,
           mac_count,
           hang_count,
           plugin_count,
           content_count,
           first_report,
           version_list,
        report_count / total_crashes::float
        as percent_of_total
    FROM tcbs_window
    ORDER BY report_count DESC
    LIMIT %s
    """ % (dbParams["product"], dbParams["version"], dbParams["startDate"],
           dbParams["endDate"],  where, dbParams["listSize"])
  #logger.debug(aCursor.mogrify(sql, dbParams))
  return db.execute(aCursor, sql)

def rangeOfQueriesGenerator(aCursor, dbParams, queryFunction):
  """
  returns a list of the results of multiple queries.
  """
  i = dbParams.startDate
  endDate = dbParams.endDate
  while i < endDate:
    params = {}
    params.update(dbParams)
    params['startDate'] = i
    params['endDate'] = i + dbParams.duration
    dbParams.logger.debug("rangeOfQueriesGenerator for %s to %s",
                          params['startDate'],
                          params['endDate'])
    yield queryFunction(aCursor, params)
    i += dbParams.duration

class DictList(object):
  def __init__(self, sourceIterable):
    super(DictList, self).__init__()
    self.rowsBySignature = {}
    self.indexes = {}
    self.rows = list(sourceIterable)
    for i, x in enumerate(self.rows):
      self.rowsBySignature[x['signature']] = x
      self.indexes[x['signature']] = i

  def find (self, aSignature):
    return (self.indexes[aSignature],
            self.rowsBySignature[aSignature]['percentOfTotal'])

  def __iter__(self):
    return iter(self.rows)

def listOfListsWithChangeInRank(listOfQueryResultsIterable):
  """
  Step through a list of query results, altering them by adding prior
  ranking. Answers all but the very first item of the input.
  """
  listOfTopCrasherLists = []
  for aListOfTopCrashers in listOfQueryResultsIterable:
    try:
      previousList = DictList(listOfTopCrasherLists[-1])
    except IndexError:
      previousList = DictList([]) # 1st processed - has no previous history
    currentListOfTopCrashers = []
    aRowAsDict = prevRowAsDict = None
    for rank, aRow in enumerate(aListOfTopCrashers):
      prevRowAsDict = aRowAsDict
      logger.debug(aRowAsDict)
      aRowAsDict = dict(zip(['signature', 'count', 'win_count', 'linux_count',
                             'mac_count', 'hang_count', 'plugin_count',
                             'content_count', 'first_report_exact', 'versions', 'percentOfTotal'], aRow))
      aRowAsDict['currentRank'] = rank
      aRowAsDict['first_report'] = aRowAsDict['first_report_exact'].strftime('%Y-%m-%d')
      aRowAsDict['first_report_exact'] = aRowAsDict['first_report_exact'].strftime('%Y-%m-%d %H:%M:%S')
      versions = aRowAsDict['versions']
      aRowAsDict['versions_count'] = len(versions)
      aRowAsDict['versions'] = ', '.join(versions)
      try:
        (aRowAsDict['previousRank'],
         aRowAsDict['previousPercentOfTotal']) = previousList.find(
                                                   aRowAsDict['signature'])
        aRowAsDict['changeInRank'] = aRowAsDict['previousRank'] - rank
        aRowAsDict['changeInPercentOfTotal'] = (
          aRowAsDict['percentOfTotal'] - aRowAsDict['previousPercentOfTotal'])
      except KeyError:
        aRowAsDict['previousRank'] = "null"
        aRowAsDict['previousPercentOfTotal'] = "null"
        aRowAsDict['changeInRank'] = "new"
        aRowAsDict['changeInPercentOfTotal'] = "new"
      currentListOfTopCrashers.append(aRowAsDict)
    listOfTopCrasherLists.append(currentListOfTopCrashers)
  return listOfTopCrasherLists[1:]

def latestEntryBeforeOrEqualTo(aCursor, aDate, product, version):
  """
  Retrieve the closest report date containing the provided product and
  version that does not exceed the provided date.
  """
  sql = """
        SELECT
          max(report_date)
        FROM
          tcbs JOIN product_versions USING (product_version_id)
        WHERE
          tcbs.report_date <= %s
          AND product_name = %s
          AND version_string = %s
        """
  try:
    result = db.singleValueSql(aCursor, sql, (aDate, product, version))
  except:
    result = None
  return result or aDate

def twoPeriodTopCrasherComparison(
      databaseCursor, context,
      closestEntryFunction=latestEntryBeforeOrEqualTo,
      listOfTopCrashersFunction=getListOfTopCrashersBySignature):
  try:
    context['logger'].debug('entered twoPeriodTopCrasherComparison')
  except KeyError:
    context['logger'] = util.SilentFakeLogger()

  assertions = ['endDate', 'duration', 'product', 'version']

  for param in assertions:
    assert param in context, (
      "%s is missing from the configuration" % param)

  context['numberOfComparisonPoints'] = 2
  if not context['listSize']:
    context['listSize'] = 100

  #context['logger'].debug('about to latestEntryBeforeOrEqualTo')
  context['endDate'] = closestEntryFunction(databaseCursor,
                                            context['endDate'],
                                            context['product'],
                                            context['version'])
  context['logger'].debug('New endDate: %s' % context['endDate'])
  context['startDate'] = context.endDate - (context.duration *
                                            context.numberOfComparisonPoints)
  #context['logger'].debug('after %s' % context)
  listOfTopCrashers = listOfListsWithChangeInRank(
                        rangeOfQueriesGenerator(
                          databaseCursor,
                          context,
                          listOfTopCrashersFunction))[0]
  #context['logger'].debug('listOfTopCrashers %s' % listOfTopCrashers)
  totalNumberOfCrashes = totalPercentOfTotal = 0
  for x in listOfTopCrashers:
    totalNumberOfCrashes += x.get('count', 0)
    totalPercentOfTotal += x.get('percentOfTotal', 0)

  result = { 'crashes': listOfTopCrashers,
             'start_date': str(context.endDate - context.duration),
             'end_date': str(context.endDate),
             'totalNumberOfCrashes': totalNumberOfCrashes,
             'totalPercentage': totalPercentOfTotal,
           }
  #logger.debug("about to return %s", result)
  return result


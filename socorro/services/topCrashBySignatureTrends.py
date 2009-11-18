import logging
logger = logging.getLogger("tcbs")

import socorro.lib.psycopghelper as psy
import psycopg2.extras as psyext

import simplejson


#  [ [ (key, rank, rankDelta, ...), ... ], ... ]

{
  "resource": "http://socorro.mozilla.org/trends/topcrashes/bysig/Firefox/3.5.3/from/2009-10-03/to/2009-10-13/page/0",
  "page": "0",
  "previous": "null",
  "next": "http://socorro.mozilla.org/trends/topcrashes/bysig/Firefox/3.5.3/from/2009-10-03/to/2009-10-13/page/0",
  "ranks":[
    {"signature": "LdrAlternateResourcesEnabled",
    "previousRank": 3,
    "currentRank": 8,
    "change": -5},
    {"signature": "OtherSignature",
    "previousRank": "null",
    "currentRank": 10,
    "change": 10}
    ],
}

#-----------------------------------------------------------------------------------------------------------------
def totalNumberOfCrashesForPeriod (aCursor, databaseParameters):
  """
  """
  sql = """
    select
        sum(tcbs.count)
    from
        top_crashes_by_signature tcbs
            join productdims pd on tcbs.productdims_id = pd.id
                                   %(productNameJoinPhrase)s
                                   %(productVersionJoinPhrase)s
                join osdims os on tcbs.osdims_id = os.id
                                  %(osNameJoinPhrase)s
                                  %(osVersionJoinPhrase)s
    where
        %%(startDate)s < tcbs.window_end
        and tcbs.window_end <= %%(endDate)s
    """ % databaseParameters
  #logger.debug(aCursor.mogrify(sql, databaseParameters))
  return psy.singleValueSql(aCursor, sql, databaseParameters)

#-----------------------------------------------------------------------------------------------------------------
def getListOfTopCrashersBySignature(aCursor, databaseParameters, totalNumberOfCrashesForPeriodFunc=totalNumberOfCrashesForPeriod):
  """
  """
  databaseParameters["totalNumberOfCrashes"] = totalNumberOfCrashesForPeriodFunc(aCursor, databaseParameters)
  sql = """
  select
      tcbs.signature,
      sum(tcbs.count) as count,
      cast(sum(tcbs.count) as float) / %%(totalNumberOfCrashes)s as percentOfTotal,
      sum(case when os.os_name LIKE 'Windows%%%%' then tcbs.count else 0 end) as win_count,
      sum(case when os.os_name = 'Mac OS X' then tcbs.count else 0 end) as mac_count,
      sum(case when os.os_name = 'Linux' then tcbs.count else 0 end) as linux_count
  from
      top_crashes_by_signature tcbs
          join productdims pd on tcbs.productdims_id = pd.id
                                 and %%(startDate)s < tcbs.window_end
                                 and tcbs.window_end <= %%(endDate)s
                                 %(productNameJoinPhrase)s
                                 %(productVersionJoinPhrase)s
              join osdims os on tcbs.osdims_id = os.id
                                %(osNameJoinPhrase)s
                                %(osVersionJoinPhrase)s
  group by
      tcbs.signature,
      pd.product,
      pd.version
  order by
    2 desc
  limit %%(listSize)s""" % databaseParameters
  #logger.debug(aCursor.mogrify(sql, databaseParameters))
  return psy.execute(aCursor, sql, databaseParameters)

#-----------------------------------------------------------------------------------------------------------------
def rangeOfQueriesGenerator(aCursor, databaseParameters, queryExecutionFunction):
  """  returns a list of the results of multiple queries.
  """
  baseParameters = {'productNameJoinPhrase':'',
                    'productVersionJoinPhrase':'',
                    'osNameJoinPhrase':'',
                    'osVersionJoinPhrase':''}
  #print databaseParameters
  if databaseParameters.product:
    baseParameters['productNameJoinPhrase'] = 'and pd.product = %(product)s'
  if databaseParameters.version:
    baseParameters['productVersionJoinPhrase'] = 'and pd.version = %(version)s'
  if databaseParameters.os_name:
    baseParameters['osNameJoinPhrase'] = 'and os.os_name = %(os_name)s'
  if databaseParameters.os_version:
    baseParameters['osVersionJoinPhrase'] = 'and os.os_version = %(os_version)s'
  i = databaseParameters.startDate
  endDate = databaseParameters.endDate
  while i < endDate:
    parameters = baseParameters.copy()
    parameters.update(databaseParameters)
    parameters["startDate"] = i
    parameters["endDate"] = i + databaseParameters.duration
    databaseParameters.logger.debug('rangeOfQueriesGenerator for %s to %s', parameters["startDate"], parameters["endDate"])
    yield queryExecutionFunction(aCursor, parameters)
    i += databaseParameters.duration

#-----------------------------------------------------------------------------------------------------------------
class NotFound(Exception):
  pass

#-----------------------------------------------------------------------------------------------------------------
def find (iterable, targetToSearchFor, equalityFunction=lambda x, y: x == y, transformFunction=lambda x, i, y: i):
  """ linear search through an iterable for some target.  Equality is determined by the equalityFunction.
      the returned result is a transformation of the targetToSearchFor, the index at which the match was found,
      and the matchng item in the iteratble.
  """
  for i, x in enumerate(iterable):
    if equalityFunction(targetToSearchFor, x):
      return transformFunction(targetToSearchFor, i, x)
  raise NotFound

#-----------------------------------------------------------------------------------------------------------------
def listOfListsWithChangeInRank (listOfQueryResultsIterator):
  """ Step through a list of query results, altering them by adding prior ranking.
      return all but the very first item of the input.
  """
  listOfTopCrasherLists = []
  for i, aListOfTopCrashers in enumerate(listOfQueryResultsIterator):
    try:
      previousList = listOfTopCrasherLists[-1]
    except IndexError:
      previousList = [] # this was the 1st processed - it has no previous history
    currentListOfTopCrashers = []
    for rank, aRow in enumerate(aListOfTopCrashers):
      aRowAsDict = dict(zip(['signature', 'count', 'percentOfTotal', 'win_count', 'mac_count', 'linux_count'], aRow))
      aRowAsDict['currentRank'] = rank
      try:
        aRowAsDict['previousRank'], aRowAsDict['previousPercentOfTotal'] = find(previousList, aRowAsDict, lambda x, y: x['signature'] == y['signature'], lambda x, i, y: (i, y['percentOfTotal']))
        aRowAsDict['changeInRank'] = aRowAsDict['previousRank'] - rank  #reversed sign as requested
        aRowAsDict['changeInPercentOfTotal'] = aRowAsDict['percentOfTotal'] - aRowAsDict['previousPercentOfTotal']
      except NotFound:
        aRowAsDict['previousRank'] = aRowAsDict['previousPercentOfTotal'] = "null"
        aRowAsDict['changeInRank'] = aRowAsDict['changeInPercentOfTotal'] = "new"
      currentListOfTopCrashers.append(aRowAsDict)
    listOfTopCrasherLists.append(currentListOfTopCrashers)
  return listOfTopCrasherLists[1:]

#-----------------------------------------------------------------------------------------------------------------
def latestEntryBeforeOrEqualTo(aCursor, aDate):
  sql = """
    select
        max(window_end)
    from
        top_crashes_by_signature tcbs
    where
        tcbs.window_end <= %s
    """
  return psy.singleValueSql(aCursor, sql, (aDate,))

#-----------------------------------------------------------------------------------------------------------------
def twoPeriodTopCrasherComparison (databaseCursor, context):
  context['logger'].debug('entered twoPeriodTopCrasherComparison')
  assert "endDate" in context, "endDate is missing from the configuration"
  assert "duration" in context, "duration is missing from the configuration"
  assert "product" in context, "product is missing from the configuration"
  assert "version" in context, "version is missing from the configuration"
  assert "listSize" in context, "listSize is missing from the configuration"
  context['numberOfComparisonPoints'] = 2
  if not context['listSize']:
    context['listSize'] = 100
  #context['logger'].debug('about to latestEntryBeforeOrEqualTo')
  context['endDate'] = latestEntryBeforeOrEqualTo(databaseCursor, context['endDate'])
  #context['logger'].debug('before %s' % context)
  context['startDate'] = context.endDate - context.duration * context.numberOfComparisonPoints
  #context['logger'].debug('after %s' % context)
  listOfTopCrashers = listOfListsWithChangeInRank(rangeOfQueriesGenerator(databaseCursor, context, getListOfTopCrashersBySignature))[0]
  context['logger'].debug('listOfTopCrashers %s' % listOfTopCrashers)
  totalNumberOfCrashes = totalPercentOfTotal = 0
  for x in listOfTopCrashers:
    totalNumberOfCrashes += x['count']
    totalPercentOfTotal += x['percentOfTotal']
  result = { 'crashes': listOfTopCrashers,
             'start_date': str(context.endDate - context.duration),
             'end_date': str(context.endDate),
             'totalNumberOfCrashes': totalNumberOfCrashes,
             'totalPercentage': totalPercentOfTotal,
           }
  context['logger'].debug('about to return %s', result)
  return result

#-----------------------------------------------------------------------------------------------------------------
def main (config):
  """
  """
  connPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  aConnection, aCursor = connPool.connectionCursorPair()

  config["numberOfComparisonPoints"] = 2

  return json.dumps(compareTopCrashBySignatureOverTime(aCursor, **config))





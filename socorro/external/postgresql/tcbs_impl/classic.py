import logging
logger = logging.getLogger("webapi")

import socorro.database.database as db

import socorro.lib.util as util

import datetime

# theoretical sample output
#    [ [ (key, rank, rankDelta, ...), ... ], ... ]
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


#------------------------------------------------------------------------------
def totalNumberOfCrashesForPeriod(aCursor, databaseParameters):
    """
    """
    where = ""
    if databaseParameters["crash_type"] == 'browser':
        where = "AND tcbs.plugin_count = 0 AND tcbs.hang_count = 0"
    if databaseParameters["crash_type"] == 'plugin':
        where = "AND tcbs.plugin_count > 0 OR tcbs.hang_count > 0"

    sql = """
        select
                sum(tcbs.count)
        from
                top_crashes_by_signature tcbs
        where
                '%s' < tcbs.window_end
                and tcbs.window_end <= '%s'
                and tcbs.productdims_id = %d
                %s
        """ % (databaseParameters["startDate"], databaseParameters["to_date"],
                        databaseParameters["productdims_id"], where)
    #logger.debug(aCursor.mogrify(sql, databaseParameters))
    return db.singleValueSql(aCursor, sql, databaseParameters)


#------------------------------------------------------------------------------
def getListOfTopCrashersBySignature(
        aCursor,
        databaseParameters,
        totalNumberOfCrashesForPeriodFunc=totalNumberOfCrashesForPeriod):
    """
    """
    databaseParameters["totalNumberOfCrashes"] = (
        totalNumberOfCrashesForPeriodFunc(aCursor, databaseParameters))

    if databaseParameters["totalNumberOfCrashes"] == None:
        return []

    assertPairs = {
     'totalNumberOfCrashes': long,
     'startDate': datetime.datetime,
     'to_date': datetime.datetime,
     'productdims_id': int,
     'limit': int
    }
    for param in assertPairs.keys():
        assert type(databaseParameters[param]) is assertPairs[param], \
        "Expected %s for %s, actual type is %s" % (assertPairs[param], param,
            type(databaseParameters[param]))

    where = []
    if databaseParameters["crash_type"] == 'browser':
        where.append("tcbs.plugin_count = 0 AND tcbs.hang_count = 0")
    if databaseParameters["crash_type"] == 'plugin':
        where.append("tcbs.plugin_count > 0 OR tcbs.hang_count > 0")
    if databaseParameters['os']:
        where.append("os.os_name ILIKE '%s%%'" % databaseParameters['os'])

    if where:
        where = "where %s" % " AND ".join(where)
    else:
        where = ""

    sql = """
    select
        tcbs.signature,
        sum(tcbs.count) as count,
        cast(sum(tcbs.count) as float) / %d as percentOfTotal,
        sum(case when os.os_name LIKE 'Windows%%' then tcbs.count else 0 end)
            as win_count,
        sum(case when os.os_name = 'Mac OS X' then tcbs.count else 0 end)
            as mac_count,
        sum(case when os.os_name = 'Linux' then tcbs.count else 0 end)
            as linux_count,
        sum(tcbs.hang_count) as hang_count,
        sum(tcbs.plugin_count) as plugin_count
    from
        top_crashes_by_signature tcbs
            join osdims os on tcbs.osdims_id = os.id
                            and '%s' < tcbs.window_end
                            and tcbs.window_end <= '%s'
                            and tcbs.productdims_id = %d
    %s
    group by
            tcbs.signature
    order by
        2 desc
    limit %d""" % (databaseParameters["totalNumberOfCrashes"],
                   databaseParameters["startDate"],
                   databaseParameters["to_date"],
                   databaseParameters["productdims_id"], where,
                   databaseParameters["limit"])

    #logger.debug(aCursor.mogrify(sql, databaseParameters))
    return db.execute(aCursor, sql)


#------------------------------------------------------------------------------
def rangeOfQueriesGenerator(aCursor, databaseParameters,
                            queryExecutionFunction):
    """Returns a list of the results of multiple queries.
    """
    i = databaseParameters.startDate
    to_date = databaseParameters.to_date
    while i < to_date:
        parameters = {}
        parameters.update(databaseParameters)
        parameters["startDate"] = i
        parameters["to_date"] = i + databaseParameters.duration
        databaseParameters.logger.debug('rangeOfQueriesGenerator for %s to %s',
            parameters["startDate"], parameters["to_date"])
        yield queryExecutionFunction(aCursor, parameters)
        i += databaseParameters.duration


#------------------------------------------------------------------------------
class DictList(object):
    def __init__(self, sourceIterable):
        super(DictList, self).__init__()
        self.rowsBySignature = {}
        self.indexes = {}
        self.rows = list(sourceIterable)
        for i, x in enumerate(self.rows):
            self.rowsBySignature[x['signature']] = x
            self.indexes[x['signature']] = i

    def find(self, aSignature):
        return (self.indexes[aSignature],
                self.rowsBySignature[aSignature]['percentOfTotal'])

    def __iter__(self):
        return iter(self.rows)


#------------------------------------------------------------------------------
def listOfListsWithChangeInRank(listOfQueryResultsIterable):
    """ Step through a list of query results, altering them by adding prior
    ranking. Return all but the very first item of the input.
    """
    listOfTopCrasherLists = []
    for i, aListOfTopCrashers in enumerate(listOfQueryResultsIterable):
        try:
            previousList = DictList(listOfTopCrasherLists[-1])
        except IndexError:
            # this was the 1st processed - it has no previous history
            previousList = DictList([])
        currentListOfTopCrashers = []
        for rank, aRow in enumerate(aListOfTopCrashers):
            aRowAsDict = dict(zip([
                'signature',
                'count',
                'percentOfTotal',
                'win_count',
                'mac_count',
                'linux_count',
                'hang_count',
                'plugin_count'
            ], aRow))
            aRowAsDict['currentRank'] = rank
            aRowAsDict['startup_percent'] = None
            try:
                (aRowAsDict['previousRank'],
                aRowAsDict['previousPercentOfTotal']) = previousList.find(
                    aRowAsDict['signature'])
                # reversed sign as requested
                aRowAsDict['changeInRank'] = aRowAsDict['previousRank'] - rank
                aRowAsDict['changeInPercentOfTotal'] = (
                    aRowAsDict['percentOfTotal'] -
                    aRowAsDict['previousPercentOfTotal'])
            except KeyError:
                aRowAsDict['previousRank'] = \
                    aRowAsDict['previousPercentOfTotal'] = "null"
                aRowAsDict['changeInRank'] = \
                    aRowAsDict['changeInPercentOfTotal'] = "new"
            currentListOfTopCrashers.append(aRowAsDict)
        listOfTopCrasherLists.append(currentListOfTopCrashers)
    return listOfTopCrasherLists[1:]


#------------------------------------------------------------------------------
def latestEntryBeforeOrEqualTo(aCursor, aDate, productdims_id):
    sql = """
        select
                max(window_end)
        from
                top_crashes_by_signature tcbs
        where
                tcbs.window_end <= %s
                and tcbs.productdims_id = %s
        """
    try:
        result = db.singleValueSql(aCursor, sql, (aDate, productdims_id))
        if result:
            return result
        return aDate
    except:
        return aDate


#------------------------------------------------------------------------------
def twoPeriodTopCrasherComparison(
        databaseCursor,
        context,
        closestEntryFunction=latestEntryBeforeOrEqualTo,
        listOfTopCrashersFunction=getListOfTopCrashersBySignature):
    try:
        context['logger'].debug('entered twoPeriodTopCrasherComparison')
    except KeyError:
        context['logger'] = util.SilentFakeLogger()
    assert "to_date" in context, "to_date is missing from the configuration"
    assert "duration" in context, "duration is missing from the configuration"
    assert "product" in context, "product is missing from the configuration"
    assert "version" in context, "version is missing from the configuration"
    assert "limit" in context, "limit is missing from the configuration"
    context.productdims_id = context['productVersionCache'].getId(
                                                         context.product,
                                                         context.version)
    context['numberOfComparisonPoints'] = 2
    if not context['limit']:
        context['limit'] = 100
    #context['logger'].debug('about to latestEntryBeforeOrEqualTo')
    context['to_date'] = closestEntryFunction(databaseCursor,
                                              context['to_date'],
                                              context['productdims_id'])
    context['logger'].debug('to_date %s' % context['to_date'])
    context['startDate'] = (context.to_date - context.duration *
                            context.numberOfComparisonPoints)
    #context['logger'].debug('after %s' % context)
    listOfTopCrashers = listOfListsWithChangeInRank(rangeOfQueriesGenerator(
        databaseCursor,
        context,
        listOfTopCrashersFunction
    ))[0]
    #context['logger'].debug('listOfTopCrashers %s' % listOfTopCrashers)
    totalNumberOfCrashes = totalPercentOfTotal = 0
    for x in listOfTopCrashers:
        totalNumberOfCrashes += x['count']
        totalPercentOfTotal += x['percentOfTotal']
    result = {
        'crashes': listOfTopCrashers,
        'start_date': str(context.to_date - context.duration),
        'end_date': str(context.to_date),
        'totalNumberOfCrashes': totalNumberOfCrashes,
        'totalPercentage': totalPercentOfTotal,
    }
    #context['logger'].debug('about to return %s', result)
    return result

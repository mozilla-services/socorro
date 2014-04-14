# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
logger = logging.getLogger("webapi")

import socorro.database.database as db
from socorro.lib import datetimeutil, util

import datetime

"""
 theoretical sample output
    [ [ (key, rank, rankDelta, ...), ... ], ... ]
{
    "resource": "http://socorro.mozilla.org/trends/topcrashes/bysig/"
                "Firefox/3.5.3/from/2009-10-03/to/2009-10-13/page/0",
    "page": "0",
    "previous": "null",
    "next": "http://socorro.mozilla.org/trends/topcrashes/bysig/"
            "Firefox/3.5.3/from/2009-10-03/to/2009-10-13/page/0",
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
"""


def getListOfTopCrashersBySignature(connection, dbParams):
    """
    Answers a generator of tcbs rows
    """
    assertPairs = {
        'startDate': (datetime.date, datetime.datetime),
        'to_date': (datetime.date, datetime.datetime),
        'product': basestring,
        'version': basestring,
        'limit': int
    }

    for param in assertPairs:
        if not isinstance(dbParams[param], assertPairs[param]):
            raise ValueError(type(dbParams[param]))

    order_by = 'report_count'  # default order field
    where = ['']  # trick for the later join
    if dbParams['crash_type'] != 'all':
        where.append("process_type = '%s'" % (dbParams['crash_type'],))
    if dbParams['os']:
        order_by = '%s_count' % dbParams['os'][0:3].lower()
        where.append("%s > 0" % order_by)

    where = ' AND '.join(where)

    table_to_use = 'tcbs'
    date_range_field = 'report_date'

    if dbParams['date_range_type'] == 'build':
        table_to_use = 'tcbs_build'
        date_range_field = 'build_date'

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
                version_list,
                sum(startup_count) as startup_count,
                sum(is_gc_count) as is_gc_count
        FROM %s tcbs
            JOIN signatures USING (signature_id)
            JOIN product_versions AS pv USING (product_version_id)
            JOIN signature_products_rollup AS spr
                ON spr.signature_id = tcbs.signature_id
                AND spr.product_name = pv.product_name
        WHERE pv.product_name = %%s
            AND version_string = %%s
            AND tcbs.%s BETWEEN %%s AND %%s
            %s
        GROUP BY tcbs.signature_id, signature, pv.product_name, version_string,
             first_report, spr.version_list
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
                %s / total_crashes::float as percent_of_total,
                startup_count / %s::float as startup_percent,
                is_gc_count,
                total_crashes::int
        FROM tcbs_window
        ORDER BY %s DESC
        LIMIT %s
    """ % (
        table_to_use,
        date_range_field,
        where,
        order_by,
        order_by,
        order_by,
        dbParams["limit"]
    )
    cursor = connection.cursor()
    params = (
        dbParams['product'],
        dbParams['version'],
        dbParams['startDate'],
        dbParams['to_date'],
    )
    try:
        return db.execute(cursor, sql, params)
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()


def rangeOfQueriesGenerator(connection, dbParams, queryFunction):
    """
    returns a list of the results of multiple queries.
    """
    i = dbParams.startDate
    to_date = dbParams.to_date
    while i < to_date:
        params = {}
        params.update(dbParams)
        params['startDate'] = i
        params['to_date'] = i + dbParams.duration
        dbParams.logger.debug("rangeOfQueriesGenerator for %s to %s",
                                                    params['startDate'],
                                                    params['to_date'])
        yield queryFunction(connection, params)
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

    def find(self, aSignature):
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
            # 1st processed - has no previous history
            previousList = DictList([])
        currentListOfTopCrashers = []
        aRowAsDict = None
        for rank, aRow in enumerate(aListOfTopCrashers):
            #logger.debug(aRowAsDict)
            aRowAsDict = dict(zip(['signature', 'count', 'win_count',
                                   'linux_count', 'mac_count', 'hang_count',
                                   'plugin_count', 'content_count',
                                   'first_report_exact', 'versions',
                                   'percentOfTotal', 'startup_percent',
                                   'is_gc_count', 'total_crashes'], aRow))
            aRowAsDict['currentRank'] = rank
            aRowAsDict['first_report'] = (
                aRowAsDict['first_report_exact'].strftime('%Y-%m-%d'))
            aRowAsDict['first_report_exact'] = (
                aRowAsDict['first_report_exact'].strftime('%Y-%m-%d %H:%M:%S'))
            versions = aRowAsDict['versions']
            aRowAsDict['versions_count'] = len(versions)
            aRowAsDict['versions'] = ', '.join(versions)
            try:
                (aRowAsDict['previousRank'],
                 aRowAsDict['previousPercentOfTotal']) = previousList.find(
                                                    aRowAsDict['signature'])
                aRowAsDict['changeInRank'] = aRowAsDict['previousRank'] - rank
                aRowAsDict['changeInPercentOfTotal'] = (
                    aRowAsDict['percentOfTotal'] -
                    aRowAsDict['previousPercentOfTotal'])
            except KeyError:
                aRowAsDict['previousRank'] = "null"
                aRowAsDict['previousPercentOfTotal'] = "null"
                aRowAsDict['changeInRank'] = "new"
                aRowAsDict['changeInPercentOfTotal'] = "new"
            currentListOfTopCrashers.append(aRowAsDict)
        listOfTopCrasherLists.append(currentListOfTopCrashers)
    return listOfTopCrasherLists[1:]


def latestEntryBeforeOrEqualTo(connection, aDate, product, version):
    """
    Retrieve the closest report date containing the provided product and
    version that does not exceed the provided date.

    We append a day to the max(report_date) to ensure that we
    capture reports to the end of the day, not the beginning.
    """
    sql = """
                SELECT
                    max(report_date) + 1
                FROM
                    tcbs JOIN product_versions USING (product_version_id)
                WHERE
                    tcbs.report_date <= %s
                    AND product_name = %s
                    AND version_string = %s
                """
    cursor = connection.cursor()
    try:
        result = db.singleValueSql(cursor, sql, (aDate, product, version))
        connection.commit()
    except:
        result = None
        connection.rollback()
    return result or aDate


def twoPeriodTopCrasherComparison(
            databaseConnection, context,
            closestEntryFunction=latestEntryBeforeOrEqualTo,
            listOfTopCrashersFunction=getListOfTopCrashersBySignature):
    try:
        context['logger'].debug('entered twoPeriodTopCrasherComparison')
    except KeyError:
        context['logger'] = util.SilentFakeLogger()

    assertions = ['to_date', 'duration', 'product', 'version']

    for param in assertions:
        assert param in context, (
            "%s is missing from the configuration" % param)

    context['numberOfComparisonPoints'] = 2
    if not context['limit']:
        context['limit'] = 100

    #context['logger'].debug('about to latestEntryBeforeOrEqualTo')
    context['to_date'] = closestEntryFunction(databaseConnection,
                                              context['to_date'],
                                              context['product'],
                                              context['version'])
    context['logger'].debug('New to_date: %s' % context['to_date'])
    context['startDate'] = context.to_date - (context.duration *
                                              context.numberOfComparisonPoints)
    #context['logger'].debug('after %s' % context)
    listOfTopCrashers = listOfListsWithChangeInRank(
                                            rangeOfQueriesGenerator(
                                                databaseConnection,
                                                context,
                                                listOfTopCrashersFunction))[0]
    #context['logger'].debug('listOfTopCrashers %s' % listOfTopCrashers)
    totalNumberOfCrashes = totalPercentOfTotal = 0
    for x in listOfTopCrashers:
        if 'total_crashes' in x:
            totalNumberOfCrashes = x['total_crashes']
            del x['total_crashes']
        totalPercentOfTotal += x.get('percentOfTotal', 0)

    result = {
        'crashes': listOfTopCrashers,
        'start_date': datetimeutil.date_to_string(
            context.to_date - context.duration
        ),
        'end_date': datetimeutil.date_to_string(context.to_date),
        'totalNumberOfCrashes': totalNumberOfCrashes,
        'totalPercentage': totalPercentOfTotal,
    }
    #logger.debug("about to return %s", result)
    return result

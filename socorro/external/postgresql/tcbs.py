# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.lib import datetimeutil, util
from socorro.external.postgresql.dbapi2_util import (
    execute_query_iter,
    single_value_sql,
)

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


#------------------------------------------------------------------------------
def get_list_of_top_crashers_by_signature(connection, db_params):
    """
    Answers a generator of tcbs rows
    """
    assert_pairs = {
        'startDate': (datetime.date, datetime.datetime),
        'to_date': (datetime.date, datetime.datetime),
        'product': basestring,
        'version': basestring,
        'limit': int
    }

    for param in assert_pairs:
        if not isinstance(db_params[param], assert_pairs[param]):
            raise ValueError(type(db_params[param]))

    order_by = 'report_count'  # default order field
    where = ['']  # trick for the later join
    if db_params['crash_type'] != 'all':
        where.append("process_type = '%s'" % (db_params['crash_type'],))
    if db_params['os']:
        order_by = '%s_count' % db_params['os'][0:3].lower()
        where.append("%s > 0" % order_by)

    where = ' AND '.join(where)

    table_to_use = 'tcbs'
    date_range_field = 'report_date'

    if db_params['date_range_type'] == 'build':
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
        db_params["limit"]
    )
    params = (
        db_params['product'],
        db_params['version'],
        db_params['startDate'],
        db_params['to_date'],
    )
    return execute_query_iter(connection, sql, params)


#------------------------------------------------------------------------------
def range_of_queries_generator(connection, db_params, query_function):
    """returns a list of the results of multiple queries."""
    i = db_params.startDate
    to_date = db_params.to_date
    while i < to_date:
        params = {}
        params.update(db_params)
        params['startDate'] = i
        params['to_date'] = i + db_params.duration
        db_params.logger.debug(
            "rangeOfQueriesGenerator for %s to %s",
            params['startDate'],
            params['to_date']
        )
        yield query_function(connection, params)
        i += db_params.duration


#==============================================================================
class DictList(object):
    #--------------------------------------------------------------------------
    def __init__(self, source_iterable):
        super(DictList, self).__init__()
        self.rows_by_signature = {}
        self.indexes = {}
        self.rows = list(source_iterable)
        for i, x in enumerate(self.rows):
            self.rows_by_signature[x['signature']] = x
            self.indexes[x['signature']] = i

    #--------------------------------------------------------------------------
    def find(self, a_signature):
        return (
            self.indexes[a_signature],
            self.rows_by_signature[a_signature]['percentOfTotal']
        )

    #--------------------------------------------------------------------------
    def __iter__(self):
        return iter(self.rows)


#------------------------------------------------------------------------------
def list_of_lists_with_change_in_rank(list_of_query_results_iterable):
    """
    Step through a list of query results, altering them by adding prior
    ranking. Answers all but the very first item of the input.
    """
    list_of_top_crasher_lists = []
    for a_list_of_top_crashers in list_of_query_results_iterable:
        try:
            previous_list = DictList(list_of_top_crasher_lists[-1])
        except IndexError:
            # 1st processed - has no previous history
            previous_list = DictList([])
        current_list_of_top_crashers = []
        a_row_as_dict = None
        for rank, aRow in enumerate(a_list_of_top_crashers):
            a_row_as_dict = dict(
                zip(
                    ['signature', 'count', 'win_count',
                     'linux_count', 'mac_count', 'hang_count',
                     'plugin_count', 'content_count',
                     'first_report_exact', 'versions',
                     'percentOfTotal', 'startup_percent',
                     'is_gc_count', 'total_crashes'],
                    aRow
                )
            )
            a_row_as_dict['currentRank'] = rank
            a_row_as_dict['first_report'] = (
                a_row_as_dict['first_report_exact'].strftime('%Y-%m-%d'))
            a_row_as_dict['first_report_exact'] = (
                a_row_as_dict['first_report_exact']
                .strftime('%Y-%m-%d %H:%M:%S')
            )
            versions = a_row_as_dict['versions']
            a_row_as_dict['versions_count'] = len(versions)
            a_row_as_dict['versions'] = ', '.join(versions)
            try:
                a_row_as_dict['previousRank'], \
                    a_row_as_dict['previousPercentOfTotal'] = (
                        previous_list.find(a_row_as_dict['signature'])
                    )
                a_row_as_dict['changeInRank'] = (
                    a_row_as_dict['previousRank'] - rank
                )
                a_row_as_dict['changeInPercentOfTotal'] = (
                    a_row_as_dict['percentOfTotal'] -
                    a_row_as_dict['previousPercentOfTotal'])
            except KeyError:
                a_row_as_dict['previousRank'] = "null"
                a_row_as_dict['previousPercentOfTotal'] = "null"
                a_row_as_dict['changeInRank'] = "new"
                a_row_as_dict['changeInPercentOfTotal'] = "new"
            current_list_of_top_crashers.append(a_row_as_dict)
        list_of_top_crasher_lists.append(current_list_of_top_crashers)
    return list_of_top_crasher_lists[1:]


#------------------------------------------------------------------------------
def latest_entry_before_or_equal_to(connection, a_date, product, version):
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
    result = single_value_sql(connection, sql, (a_date, product, version))
    return result or a_date


#------------------------------------------------------------------------------
def two_period_top_crasher_comparison(
    connection,
    config,
    closest_entry_function=latest_entry_before_or_equal_to,
    list_of_top_crashers_function=get_list_of_top_crashers_by_signature
):
    try:
        config['logger'].debug('entered two_period_top_crasher_comparison')
    except KeyError:
        config['logger'] = util.SilentFakeLogger()

    assertions = ['to_date', 'duration', 'product', 'version']

    for param in assertions:
        assert param in config, (
            "%s is missing from the configuration" % param)

    config['number_of_comparison_points'] = 2
    if not config['limit']:
        config['limit'] = 100

    #context['logger'].debug('about to latestEntryBeforeOrEqualTo')
    config['to_date'] = closest_entry_function(
        connection,
        config['to_date'],
        config['product'],
        config['version']
    )
    config['logger'].debug('New to_date: %s' % config['to_date'])
    config['startDate'] = config.to_date - (
        config.duration * config.number_of_comparison_points
    )
    #context['logger'].debug('after %s' % context)
    list_of_top_crashers = list_of_lists_with_change_in_rank(
        range_of_queries_generator(
            connection,
            config,
            list_of_top_crashers_function
        )
    )[0]
    total_number_of_crashes = totalPercentOfTotal = 0
    for x in list_of_top_crashers:
        if 'total_crashes' in x:
            total_number_of_crashes = x['total_crashes']
            del x['total_crashes']
        totalPercentOfTotal += x.get('percentOfTotal', 0)

    result = {
        'crashes': list_of_top_crashers,
        'start_date': datetimeutil.date_to_string(
            config.to_date - config.duration
        ),
        'end_date': datetimeutil.date_to_string(config.to_date),
        'totalNumberOfCrashes': total_number_of_crashes,
        'totalPercentage': totalPercentOfTotal,
    }
    return result

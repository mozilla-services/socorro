# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.lib import (
    MissingArgumentError,
    BadArgumentError,
    datetimeutil,
    external_common,
)
from socorro.external.postgresql import tcbs
from socorro.external.postgresql.base import PostgreSQLBase


logger = logging.getLogger("webapi")


class Crashes(PostgreSQLBase):
    """Handle retrieval and creation of crash reports data with PostgreSQL.
    """

    def get_daily(self, **kwargs):
        """Return crashes by active daily users. """
        now = datetimeutil.utc_now().date()
        lastweek = now - datetime.timedelta(weeks=1)

        filters = [
            ("product", None, "str"),
            ("versions", None, ["list", "str"]),
            ("from_date", lastweek, "date"),
            ("to_date", now, "date"),
            ("os", None, ["list", "str"]),
            ("report_type", None, ["list", "str"]),
            ("date_range_type", "date", "str"),
        ]

        # aliases
        if "from" in kwargs and "from_date" not in kwargs:
            kwargs["from_date"] = kwargs.get("from")
        if "to" in kwargs and "to_date" not in kwargs:
            kwargs["to_date"] = kwargs.get("to")

        params = external_common.parse_arguments(filters, kwargs)

        if not params.product:
            raise MissingArgumentError('product')

        if not params.versions or not params.versions[0]:
            raise MissingArgumentError('versions')

        params.versions = tuple(params.versions)

        # simple version, for home page graphs mainly
        if ((not params.os or not params.os[0]) and
                (not params.report_type or not params.report_type[0])):
            if params.date_range_type == "build":
                table_to_use = "home_page_graph_build_view"
                date_range_field = "build_date"
            else:
                table_to_use = "home_page_graph_view"
                date_range_field = "report_date"

            db_fields = ("product_name", "version_string", date_range_field,
                         "report_count", "adu", "crash_hadu")

            out_fields = ("product", "version", "date", "report_count", "adu",
                          "crash_hadu")

            sql = """
                /* socorro.external.postgresql.crashes.Crashes.get_daily */
                SELECT %(db_fields)s
                FROM %(table_to_use)s
                WHERE product_name=%%(product)s
                AND version_string IN %%(versions)s
                AND %(date_range_field)s BETWEEN %%(from_date)s
                    AND %%(to_date)s
            """ % {"db_fields": ", ".join(db_fields),
                   "date_range_field": date_range_field,
                   "table_to_use": table_to_use}

        # complex version, for daily crashes page mainly
        else:
            if params.date_range_type == "build":
                table_to_use = "crashes_by_user_build_view"
                date_range_field = "build_date"
            else:
                table_to_use = "crashes_by_user_view"
                date_range_field = "report_date"

            db_fields = [
                "product_name",
                "version_string",
                date_range_field,
                "sum(adjusted_report_count)::bigint as report_count",
                "sum(adu)::bigint as adu",
                """crash_hadu(sum(report_count)::bigint, sum(adu)::bigint,
                              avg(throttle)) as crash_hadu""",
                "avg(throttle) as throttle"
            ]

            out_fields = ["product", "version", "date", "report_count", "adu",
                          "crash_hadu", "throttle"]

            db_group = ["product_name", "version_string", date_range_field]

            sql_where = []
            if params.os and params.os[0]:
                sql_where.append("os_short_name IN %(os)s")
                params.os = tuple(x[0:3].lower() for x in params.os)

            if params.report_type and params.report_type[0]:
                sql_where.append("crash_type_short IN %(report_type)s")
                params.report_type = tuple(params.report_type)

            if sql_where:
                sql_where = "AND %s" % " AND ".join(sql_where)
            else:
                sql_where = ''

            sql = """
                /* socorro.external.postgresql.crashes.Crashes.get_daily */
                SELECT %(db_fields)s
                FROM (
                    SELECT
                        product_name,
                        version_string,
                        %(date_range_field)s,
                        os_name,
                        os_short_name,
                        SUM(report_count)::int as report_count,
                        SUM(adjusted_report_count)::int
                            as adjusted_report_count,
                        MAX(adu) as adu,
                        AVG(throttle) as throttle
                    FROM %(table_to_use)s
                    WHERE product_name=%%(product)s
                    AND version_string IN %%(versions)s
                    AND %(date_range_field)s BETWEEN %%(from_date)s
                        AND %%(to_date)s
                    %(sql_where)s
                    GROUP BY product_name, version_string,
                             %(date_range_field)s, os_name, os_short_name
                ) as aggregated_crashes_by_user
            """ % {"db_fields": ", ".join(db_fields),
                   "date_range_field": date_range_field,
                   "table_to_use": table_to_use,
                   "sql_where": sql_where}

            if db_group:
                sql = "%s GROUP BY %s" % (sql, ", ".join(db_group))

        error_message = "Failed to retrieve daily crashes data from PostgreSQL"
        results = self.query(sql, params, error_message=error_message)

        hits = {}
        for row in results:
            daily_data = dict(zip(out_fields, row))
            if "throttle" in daily_data:
                daily_data["throttle"] = float(daily_data["throttle"])
            daily_data["crash_hadu"] = float(daily_data["crash_hadu"])
            daily_data["date"] = datetimeutil.date_to_string(
                daily_data["date"]
            )

            key = "%s:%s" % (daily_data["product"],
                             daily_data["version"])

            if "os_short" in daily_data:
                del daily_data["os_short"]

            if key not in hits:
                hits[key] = {}

            hits[key][daily_data["date"]] = daily_data

        return {"hits": hits}

    def get_count_by_day(self, **kwargs):
        """Returns the number of crashes on a daily basis"""
        filters = [
            ("signature", None, "str"),
            ("start_date", None, "date"),
            ("end_date", None, "date")
        ]

        DATE_FORMAT = "%Y-%m-%d"

        params = external_common.parse_arguments(filters, kwargs)

        for param in ("signature", "start_date"):
            if not params[param]:
                raise MissingArgumentError(param)

        if not params.end_date:
            params.end_date = params.start_date + datetime.timedelta(1)

        sql = """
            SELECT
                COUNT(*),
                date_processed::date
            FROM
                reports_clean rc
            JOIN signatures ON
                rc.signature_id=signatures.signature_id
            WHERE
                rc.date_processed >= %(start_date)s AND
                rc.date_processed::date < %(end_date)s AND
                signatures.signature=%(signature)s
            GROUP BY
                rc.date_processed::date
        """

        hits = {}

        for count, date in self.query(sql, params):
            hits[date.strftime(DATE_FORMAT)] = count

        current = params.start_date
        while current < params.end_date:
            hits.setdefault(current.strftime(DATE_FORMAT), 0)
            current += datetime.timedelta(1)

        return {"hits": hits, "total": len(hits)}

    def get_signatures(self, **kwargs):
        """Return top crashers by signatures.

        See https://socorro.readthedocs.io/en/latest/middleware.html#tcbs
        """
        filters = [
            ("product", None, "str"),
            ("version", None, "str"),
            ("crash_type", "all", "str"),
            ("to_date", datetimeutil.utc_now(), "datetime"),
            ("duration", datetime.timedelta(7), "timedelta"),
            ("os", None, "str"),
            ("limit", 100, "int"),
            ("date_range_type", None, "str")
        ]

        params = external_common.parse_arguments(filters, kwargs)
        params.logger = logger

        # what the twoPeriodTopCrasherComparison() function does is that it
        # makes a start date from taking the to_date - duration
        if params.duration > datetime.timedelta(30):
            raise BadArgumentError('Duration too long. Max 30 days.')

        with self.get_connection() as connection:
            return tcbs.twoPeriodTopCrasherComparison(connection, params)

    def get_signature_history(self, **kwargs):
        """Return the history of a signature.

        See https://socorro.readthedocs.io/en/latest/middleware.html
        """
        now = datetimeutil.utc_now()
        lastweek = now - datetime.timedelta(days=7)

        filters = [
            ('product', None, 'str'),
            ('version', None, 'str'),
            ('signature', None, 'str'),
            ('end_date', now, 'datetime'),
            ('start_date', lastweek, 'datetime'),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        for param in ('product', 'version', 'signature'):
            if not params[param]:
                raise MissingArgumentError(param)

        if params.signature == '##null##':
            signature_where = 'AND signature IS NULL'
        else:
            signature_where = 'AND signature = %(signature)s'

        if params.signature == '##empty##':
            params.signature = ''

        sql = """
            /* external.postgresql.crashes.Crashes.get_signature_history */
            WITH hist AS (
                SELECT
                    report_date,
                    report_count
                FROM
                    tcbs JOIN signatures using (signature_id)
                         JOIN product_versions using (product_version_id)
                WHERE
                    report_date BETWEEN %%(start_date)s AND %%(end_date)s
                    AND product_name = %%(product)s
                    AND version_string = %%(version)s
                    %s
                GROUP BY
                    report_date, report_count
                ORDER BY 1
            ),
            scaling_window AS (
                SELECT
                    hist.*,
                    SUM(report_count) over () AS total_crashes
                FROM hist
            )
            SELECT
                report_date AS date,
                report_count AS count,
                report_count / total_crashes::float * 100 AS percent_of_total
            FROM scaling_window
            ORDER BY report_date DESC
        """ % signature_where

        error_message = 'Failed to retrieve signature history from PostgreSQL'
        results = self.query(sql, params, error_message=error_message)

        # Transforming the results into what we want
        history = []
        for dot in results.zipped():
            dot['date'] = datetimeutil.date_to_string(dot['date'])
            history.append(dot)

        return {
            'hits': history,
            'total': len(history)
        }

    def get_exploitability(self, **kwargs):
        """Return a list of exploitable crash reports.

        See socorro.lib.external_common.parse_arguments() for all filters.
        """
        now = datetimeutil.utc_now().date()
        lastweek = now - datetime.timedelta(weeks=1)

        filters = [
            ("start_date", lastweek, "date"),
            ("end_date", now, "date"),
            ("product", None, "str"),
            ("version", None, "str"),
            ("page", None, "int"),
            ("batch", None, "int"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        sql_where = """
            report_date BETWEEN %(start_date)s AND %(end_date)s
            AND
            null_count + none_count + low_count + medium_count + high_count > 4
        """

        if params.product:
            sql_where += " AND pv.product_name = %(product)s"
        if params.version:
            sql_where += " AND pv.version_string = %(version)s"

        inner_with_sql = """
            SELECT
                signature,
                SUM(high_count) AS high_count,
                SUM(medium_count) AS medium_count,
                SUM(low_count) AS low_count,
                SUM(null_count) AS null_count,
                SUM(none_count) AS none_count,
                SUM(high_count) + SUM(medium_count) AS med_or_high
            FROM exploitability_reports
            JOIN product_versions AS pv USING (product_version_id)
            WHERE
                high_count + medium_count + null_count + none_count > 4
                AND
                %s
            GROUP BY signature
        """ % (sql_where,)

        count_sql_query = """
            /* external.postgresql.crashes.Crashes.get_exploitability */
            WITH sums AS (
                %s
            )
            SELECT
                count(signature)
            FROM sums
        """ % (inner_with_sql,)

        results = self.query(
            count_sql_query,
            params,
            error_message="Failed to retrieve exploitable crashes count"
        )
        total_crashes_count, = results[0]

        sql_query = """
            /* external.postgresql.crashes.Crashes.get_exploitability */
            WITH sums AS (
                %s
            )
            SELECT
                signature,
                high_count,
                medium_count,
                low_count,
                null_count,
                none_count
            FROM sums
            ORDER BY
                med_or_high DESC, signature ASC
        """ % (inner_with_sql,)

        if params['page'] is not None:
            if params['page'] <= 0:
                raise BadArgumentError('page', params['page'], 'starts on 1')
            if params['batch'] is None:
                raise MissingArgumentError('batch')
            sql_query += """
            LIMIT %(limit)s
            OFFSET %(offset)s
            """
            params['limit'] = params['batch']
            params['offset'] = params['batch'] * (params['page'] - 1)

        error_message = (
            "Failed to retrieve exploitable crashes from PostgreSQL"
        )
        results = self.query(sql_query, params, error_message=error_message)

        # Transforming the results into what we want
        crashes = results.zipped()

        return {
            "hits": crashes,
            "total": total_crashes_count
        }


class AduBySignature(Crashes):

    def get(self, **kwargs):
        """Return a list of ADUs and crash counts by signature and ADU date
        """
        now = datetimeutil.utc_now().date()
        lastweek = now - datetime.timedelta(weeks=1)

        filters = [
            ("start_date", lastweek, "date"),
            ("end_date", now, "date"),
            ("signature", None, "str"),
            ("channel", None, "str"),
            ("product_name", None, "str"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        for param in ("start_date", "end_date", "signature", "channel"):
            if not params[param]:
                raise MissingArgumentError(param)

        if params.end_date - params.start_date > datetime.timedelta(days=365):
            raise BadArgumentError('Duration too long. Max 365 days.')

        sql_query = """
            SELECT
                product_name,
                signature,
                adu_date::TEXT,
                build_date::TEXT,
                buildid::TEXT,
                crash_count,
                adu_count,
                os_name,
                channel
            FROM crash_adu_by_build_signature
            WHERE adu_date BETWEEN %(start_date)s AND %(end_date)s
            AND product_name = %(product_name)s
            AND channel = %(channel)s
            AND signature = %(signature)s
            ORDER BY buildid
        """

        error_message = (
            "Failed to retrieve crash ADU by build signature from PostgreSQL"
        )
        results = self.query(sql_query, params, error_message=error_message)

        crashes = results.zipped()

        return {
            "hits": crashes,
            "total": len(crashes)
        }

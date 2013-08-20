# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.external import MissingOrBadArgumentError
from socorro.external.postgresql import tcbs
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util
from socorro.lib import datetimeutil, external_common, search_common

logger = logging.getLogger("webapi")


class Crashes(PostgreSQLBase):
    """Handle retrieval and creation of crash reports data with PostgreSQL.
    """

    def prepare_search_params(self, **kwargs):
        """Return a dictionary of parameters for a search-like SQL query.

        Uses socorro.lib.search_common.get_parameters() for arguments
        filtering.
        """
        params = search_common.get_parameters(kwargs)

        if not params["signature"]:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'signature' is missing or empty"
            )

        params["terms"] = params["signature"]
        params["search_mode"] = "is_exactly"

        # Default mode falls back to starts_with for postgres
        if params["plugin_search_mode"] == "default":
            params["plugin_search_mode"] = "starts_with"

        # Searching for terms in plugins
        if params["report_process"] == "plugin" and params["plugin_terms"]:
            params["plugin_terms"] = " ".join(params["plugin_terms"])
            params["plugin_terms"] = Crashes.prepare_terms(
                params["plugin_terms"],
                params["plugin_search_mode"]
            )

        # Get information about the versions
        util_service = Util(config=self.context)
        params["versions_info"] = util_service.versions_info(**params)

        # Parsing the versions
        params["versions_string"] = params["versions"]
        (params["versions"], params["products"]) = Crashes.parse_versions(
            params["versions"],
            params["products"]
        )

        # Changing the OS ids to OS names
        if hasattr(self.context, 'webapi'):
            context = self.context.webapi
        else:
            # old middleware
            context = self.context
        for i, elem in enumerate(params["os"]):
            for platform in context.platforms:
                if platform["id"] == elem:
                    params["os"][i] = platform["name"]

        return params

    def get_comments(self, **kwargs):
        """Return a list of comments on crash reports, filtered by
        signatures and other fields.

        See socorro.lib.search_common.get_parameters() for all filters.
        """
        params = self.prepare_search_params(**kwargs)

        # Creating the parameters for the sql query
        sql_params = {}

        # Preparing the different parts of the sql query

        # WARNING: sensitive data is returned here (email). When there is
        # an authentication mecanism, a verification should be done here.
        sql_select = """
            SELECT
                r.date_processed,
                r.user_comments,
                r.uuid,
                CASE
                    WHEN r.email = '' THEN null
                    WHEN r.email IS NULL THEN null
                    ELSE r.email
                END
        """

        sql_from = self.build_reports_sql_from(params)
        (sql_where, sql_params) = self.build_reports_sql_where(params,
                                                               sql_params,
                                                               self.context)
        sql_where = "%s AND r.user_comments IS NOT NULL" % sql_where

        sql_order = "ORDER BY email ASC, r.date_processed ASC"

        # Assembling the query
        sql_query = " ".join((
            "/* external.postgresql.crashes.Crashes.get_comments */",
            sql_select, sql_from, sql_where, sql_order)
        )

        error_message = "Failed to retrieve comments from PostgreSQL"
        results = self.query(sql_query, sql_params,
                             error_message=error_message)

        # Transforming the results into what we want
        comments = []
        for row in results:
            comment = dict(zip((
                "date_processed",
                "user_comments",
                "uuid",
                "email",
            ), row))
            comment["date_processed"] = datetimeutil.date_to_string(
                comment["date_processed"]
            )
            comments.append(comment)

        return {
            "hits": comments,
            "total": len(comments)
        }

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
            ("separated_by", None, "str"),
            ("date_range_type", "date", "str"),
        ]

        # aliases
        if "from" in kwargs and "from_date" not in kwargs:
            kwargs["from_date"] = kwargs.get("from")
        if "to" in kwargs and "to_date" not in kwargs:
            kwargs["to_date"] = kwargs.get("to")

        params = external_common.parse_arguments(filters, kwargs)

        if not params.product:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'product' is missing or empty"
            )

        if not params.versions or not params.versions[0]:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'versions' is missing or empty"
            )

        params.versions = tuple(params.versions)

        # simple version, for home page graphs mainly
        if ((not params.os or not params.os[0]) and
                (not params.report_type or not params.report_type[0]) and
                (not params.separated_by or not params.separated_by[0])):
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

            if params.separated_by == "os":
                db_fields += ["os_name", "os_short_name"]
                db_group += ["os_name", "os_short_name"]
                out_fields += ["os", "os_short"]

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

        sql = str(" ".join(sql.split()))  # better formatting of the sql string

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
            if params.separated_by == "os":
                key = "%s:%s" % (key, daily_data["os_short"])

            if "os_short" in daily_data:
                del daily_data["os_short"]

            if key not in hits:
                hits[key] = {}

            hits[key][daily_data["date"]] = daily_data

        return {"hits": hits}

    def get_count_by_day(self, **kwargs):
        """Returns the number of crashes on a daily basis"""
        error_message = "Error getting data from PostgreSQL."

        if not kwargs.get("signature") or not kwargs.get("date"):
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'signture' and 'date' is missing or empty"
            )

        sql = """
            SELECT
                COUNT(*)
            FROM
                reports
            WHERE
                utc_day_is(date_processed, %(date)s) AND
                signature=%(signature)s
        """

        params = {"signature": kwargs["signature"], "date": kwargs["date"]}
        result = self.query(sql, params, error_message)
        return {"total": result[0][0]}

    def get_frequency(self, **kwargs):
        """Return the number and frequency of crashes on each OS.

        See socorro.lib.search_common.get_parameters() for all filters.
        """
        # aliases
        if "from" in kwargs and "from_date" not in kwargs:
            kwargs["from_date"] = kwargs.get("from")
        if "to" in kwargs and "to_date" not in kwargs:
            kwargs["to_date"] = kwargs.get("to")

        params = self.prepare_search_params(**kwargs)

        # Creating the parameters for the sql query
        sql_params = {
            "signature": params.signature
        }

        # Preparing the different parts of the sql query
        sql_select = ["""
            SELECT
                r.build AS build_date,
                COUNT(CASE WHEN (r.signature = %(signature)s) THEN 1 END)
                    AS count,
                CAST(COUNT(CASE WHEN (r.signature = %(signature)s) THEN 1 END)
                    AS FLOAT(10)) / count(r.id) AS frequency,
                COUNT(r.id) AS total
        """]

        ## Adding count for each OS
        if hasattr(self.context, 'webapi'):
            context = self.context.webapi
        else:
            # old middleware
            context = self.context

        for i in context.platforms:
            sql_select.append("""
                COUNT(CASE WHEN (r.signature = %%(signature)s
                      AND r.os_name = '%s') THEN 1 END) AS count_%s
            """ % (i["name"], i["id"]))
            sql_select.append("""
                CASE WHEN (COUNT(CASE WHEN (r.os_name = '%s') THEN 1 END)
                > 0) THEN (CAST(COUNT(CASE WHEN (r.signature = '%s'
                AND r.os_name = '%s') THEN 1 END) AS FLOAT(10)) /
                COUNT(CASE WHEN (r.os_name = '%s') THEN 1 END)) ELSE 0.0
                END AS frequency_%s
            """ % (i["name"], params.signature, i["name"], i["name"], i["id"]))

        sql_select = ", ".join(sql_select)

        sql_from = self.build_reports_sql_from(params)

        (sql_where, sql_params) = self.build_reports_sql_where(
            params,
            sql_params,
            context
        )

        sql_group = "GROUP BY r.build"
        sql_order = "ORDER BY r.build DESC"

        # Assembling the query
        sql = " ".join((
            "/* external.postgresql.crashes.Crashes.get_fequency */",
            sql_select, sql_from, sql_where, sql_group, sql_order)
        )
        sql = str(" ".join(sql.split()))  # better formatting of the sql string

        # Query the database
        error_message = "Failed to retrieve extensions from PostgreSQL"
        results = self.query(sql, sql_params, error_message=error_message)

        fields = ["build_date", "count", "frequency", "total"]
        for platform in context.platforms:
            fields.append("count_%s" % platform["id"])
            fields.append("frequency_%s" % platform["id"])

        frequencies = [dict(zip(fields, row)) for row in results]

        return {
            "hits": frequencies,
            "total": len(frequencies)
        }

    def get_paireduuid(self, **kwargs):
        """Return paired uuid given a uuid and an optional hangid.

        If a hangid is passed, then return only one result. Otherwise, return
        all found paired uuids.

        """
        filters = [
            ("uuid", None, "str"),
            ("hangid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'uuid' is missing or empty"
            )

        crash_date = datetimeutil.uuid_to_date(params.uuid)

        sql = """
            /* socorro.external.postgresql.crashes.Crashes.get_paireduuid */
            SELECT uuid
            FROM reports r
            WHERE r.uuid != %(uuid)s
            AND r.date_processed BETWEEN
                TIMESTAMP %(crash_date)s - CAST('1 day' AS INTERVAL) AND
                TIMESTAMP %(crash_date)s + CAST('1 day' AS INTERVAL)
        """
        sql_params = {
            "uuid": params.uuid,
            "crash_date": crash_date
        }

        if params.hangid is not None:
            sql = """%s
                AND r.hangid = %%(hangid)s
                LIMIT 1
            """ % sql
            sql_params["hangid"] = params.hangid
        else:
            sql = """%s
                AND r.hangid IN (
                    SELECT hangid
                    FROM reports r2
                    WHERE r2.date_processed BETWEEN
                        TIMESTAMP %%(crash_date)s - CAST('1 day' AS INTERVAL)
                        AND
                        TIMESTAMP %%(crash_date)s + CAST('1 day' AS INTERVAL)
                    AND r2.uuid = %%(uuid)s
                )
            """ % sql

        # Query the database
        error_message = "Failed to retrieve paired uuids from PostgreSQL"
        results = self.query(sql, sql_params, error_message=error_message)

        # Transforming the results into what we want
        uuids = [dict(zip(("uuid",), row)) for row in results]

        return {
            "hits": uuids,
            "total": len(uuids)
        }

    def get_signatures(self, **kwargs):
        """Return top crashers by signatures.

        See http://socorro.readthedocs.org/en/latest/middleware.html#tcbs
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

        try:
            connection = self.database.connection()
            cursor = connection.cursor()
            return tcbs.twoPeriodTopCrasherComparison(cursor, params)
        finally:
            connection.close()

    def get_signature_history(self, **kwargs):
        """Return the history of a signature.

        See http://socorro.readthedocs.org/en/latest/middleware.html#crashes_signature_history
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
                raise MissingOrBadArgumentError(
                    "Mandatory parameter '%s' is missing or empty" % param
                )

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
                report_date,
                report_count,
                report_count / total_crashes::float * 100 AS percent_of_total
            FROM scaling_window
            ORDER BY report_date DESC
        """ % signature_where

        error_message = 'Failed to retrieve signature history from PostgreSQL'
        results = self.query(sql, params, error_message=error_message)

        # Transforming the results into what we want
        history = []
        for row in results:
            dot = dict(zip(('date', 'count', 'percent_of_total'), row))
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
            ("page", None, "int"),
            ("batch", None, "int"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        count_sql_query = """
            /* external.postgresql.crashes.Crashes.get_exploitability */
            SELECT COUNT(*)
            FROM exploitability_reports
            WHERE
                report_date BETWEEN %(start_date)s AND %(end_date)s
        """
        results = self.query(
            count_sql_query,
            params,
            error_message="Failed to retrieve exploitable crashes count"
        )
        total_crashes_count, = results[0]

        sql_query = """
            /* external.postgresql.crashes.Crashes.get_exploitability */
            SELECT
                signature,
                report_date,
                null_count,
                none_count,
                low_count,
                medium_count,
                high_count
            FROM exploitability_reports
            WHERE
                report_date BETWEEN %(start_date)s AND %(end_date)s
            ORDER BY
                report_date DESC
        """

        if params['page'] is not None:
            if params['page'] <= 0:
                raise MissingOrBadArgumentError(
                    "'page' starts on 1"
                )
            if params['batch'] is None:
                raise MissingOrBadArgumentError(
                    "'page' passed but not 'batch' size specified"
                )
            sql_query += """
            LIMIT %(limit)s
            OFFSET %(offset)s
            """
            params['limit'] = params['batch']
            params['offset'] = params['batch'] * (params['page'] - 1)

        error_message = "Failed to retrieve exploitable crashes from PostgreSQL"
        results = self.query(sql_query, params, error_message=error_message)

        # Transforming the results into what we want
        crashes = []
        for row in results:
            crash = dict(zip(("signature",
                              "report_date",
                              "null_count",
                              "none_count",
                              "low_count",
                              "medium_count",
                              "high_count"), row))
            crash["report_date"] = datetimeutil.date_to_string(
                crash["report_date"])
            crashes.append(crash)

        return {
            "hits": crashes,
            "total": total_crashes_count
        }

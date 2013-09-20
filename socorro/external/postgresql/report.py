# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging

from socorro.external import MissingArgumentError, BadArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util
from socorro.lib import datetimeutil, search_common

logger = logging.getLogger("webapi")


class Report(PostgreSQLBase):

    """
    Implement the /report service with PostgreSQL.
    """

    def get_list(self, **kwargs):
        """
        List all crashes with a given signature and return them.

        Both `from_date` and `to_date` (and their aliases `from` and `to`)
        are required and can not be greater than 30 days apart.

        Optional arguments: see SearchCommon.get_parameters()

        """
        # aliases
        if "from" in kwargs and "from_date" not in kwargs:
            kwargs["from_date"] = kwargs.get("from")
        if "to" in kwargs and "to_date" not in kwargs:
            kwargs["to_date"] = kwargs.get("to")

        if not kwargs.get('from_date'):
            raise MissingArgumentError('from_date')
        if not kwargs.get('to_date'):
            raise MissingArgumentError('to_date')

        from_date = datetimeutil.datetimeFromISOdateString(kwargs['from_date'])
        to_date = datetimeutil.datetimeFromISOdateString(kwargs['to_date'])
        span_days = (to_date - from_date).days
        if span_days > 30:
            raise BadArgumentError(
                'Span between from_date and to_date can not be more than 30'
            )
        include_raw_crash = kwargs.get('include_raw_crash') or False
        params = search_common.get_parameters(kwargs)

        if not params["signature"]:
            raise MissingArgumentError('signature')

        params["terms"] = params["signature"]
        params["search_mode"] = "is_exactly"

        # Default mode falls back to starts_with for postgres
        if params["plugin_search_mode"] == "default":
            params["plugin_search_mode"] = "starts_with"

        # Limiting to a signature
        if params["terms"]:
            params["terms"] = self.prepare_terms(params["terms"],
                                                 params["search_mode"])

        # Searching for terms in plugins
        if params["report_process"] == "plugin" and params["plugin_terms"]:
            params["plugin_terms"] = " ".join(params["plugin_terms"])
            params["plugin_terms"] = self.prepare_terms(
                params["plugin_terms"],
                params["plugin_search_mode"]
            )

        # Get information about the versions
        util_service = Util(config=self.context)
        params["versions_info"] = util_service.versions_info(**params)

        # Parsing the versions
        params["versions_string"] = params["versions"]
        (params["versions"], params["products"]) = self.parse_versions(
            params["versions"],
            params["products"]
        )

        if hasattr(self.context, 'webapi'):
            context = self.context.webapi
        else:
            # old middleware
            context = self.context
        # Changing the OS ids to OS names
        for i, elem in enumerate(params["os"]):
            for platform in context.platforms:
                if platform["id"][:3] == elem[:3]:
                    params["os"][i] = platform["name"]

        # Creating the parameters for the sql query
        sql_params = {
        }

        # Preparing the different parts of the sql query
        sql_select = """
            SELECT
                r.date_processed,
                r.uptime,
                r.user_comments,
                r.uuid::uuid,
                r.uuid as uuid_text,
                r.product,
                r.version,
                r.build,
                r.signature,
                r.url,
                r.os_name,
                r.os_version,
                r.cpu_name,
                r.cpu_info,
                r.address,
                r.reason,
                r.last_crash,
                r.install_age,
                r.hangid,
                r.process_type,
                (r.client_crash_date - (r.install_age * INTERVAL '1 second'))
                  AS install_time
        """
        if include_raw_crash:
            pass
        else:
            sql_select += """
                , rd.duplicate_of
            """

        wrapped_select = """
            WITH report_slice AS (
              %s
            ), dupes AS (
                SELECT
                    report_slice.uuid,
                    rd.duplicate_of
                FROM reports_duplicates rd
                JOIN report_slice ON report_slice.uuid_text = rd.uuid
                WHERE
                    rd.date_processed BETWEEN %%(from_date)s AND %%(to_date)s
            )

            SELECT
                rs.*,
                dupes.duplicate_of,
                rc.raw_crash
            FROM report_slice rs
            LEFT OUTER JOIN dupes USING (uuid)
            LEFT OUTER JOIN raw_crashes rc ON
                rs.uuid = rc.uuid
                AND
                rc.date_processed BETWEEN %%(from_date)s AND %%(to_date)s
        """

        sql_from = self.build_reports_sql_from(params)

        if not include_raw_crash:
            sql_from = """%s
                LEFT OUTER JOIN reports_duplicates rd ON r.uuid = rd.uuid
            """ % sql_from

        sql_where, sql_params = self.build_reports_sql_where(
            params,
            sql_params,
            self.context
        )

        sql_order = """
            ORDER BY r.date_processed DESC
        """

        sql_limit, sql_params = self.build_reports_sql_limit(
            params,
            sql_params
        )

        # Assembling the query
        if include_raw_crash:
            sql_query = "\n".join((
                "/* socorro.external.postgresql.report.Report.list */",
                sql_select, sql_from, sql_where, sql_order, sql_limit)
            )
        else:
            sql_query = "\n".join((
                "/* socorro.external.postgresql.report.Report.list */",
                sql_select, sql_from, sql_where, sql_order, sql_limit)
            )

        # Query for counting the results
        sql_count_query = "\n".join((
            "/* socorro.external.postgresql.report.Report.list */",
            "SELECT count(*)", sql_from, sql_where)
        )

        # Querying the DB
        with self.get_connection() as connection:

            total = self.count(
                sql_count_query,
                sql_params,
                error_message="Failed to count crashes from reports.",
                connection=connection
            )

            # No need to call Postgres if we know there will be no results
            if total:

                if include_raw_crash:
                    sql_query = wrapped_select % sql_query

                results = self.query(
                    sql_query,
                    sql_params,
                    error_message="Failed to retrieve crashes from reports",
                    connection=connection
                )
            else:
                results = []

        # Transforming the results into what we want
        fields = (
            "date_processed",
            "uptime",
            "user_comments",
            "uuid",
            "uuid",  # the uuid::text one
            "product",
            "version",
            "build",
            "signature",
            "url",
            "os_name",
            "os_version",
            "cpu_name",
            "cpu_info",
            "address",
            "reason",
            "last_crash",
            "install_age",
            "hangid",
            "process_type",
            "install_time",
            "duplicate_of",
        )
        if include_raw_crash:
            fields += ("raw_crash",)
        crashes = []
        for row in results:
            crash = dict(zip(fields, row))
            if include_raw_crash and crash['raw_crash']:
                crash['raw_crash'] = json.loads(crash['raw_crash'])
            for i in crash:
                try:
                    crash[i] = datetimeutil.date_to_string(crash[i])
                except TypeError:
                    pass
            crashes.append(crash)

        return {
            "hits": crashes,
            "total": total
        }

    def generate_sql_select(self, params):
        """
        Generate and return the SELECT part of the final SQL query.
        """
        sql_select = ["SELECT r.signature, count(r.id) as total"]

        if hasattr(self.context, 'webapi'):
            context = self.context.webapi
        else:
            # old middleware
            context = self.context
        ## Adding count for each OS
        for i in context.platforms:
            sql_select.append("".join(("count(CASE WHEN (r.os_name = %(os_",
                                       i["id"], ")s) THEN 1 END) AS is_",
                                       i["id"])))

        sql_select.append(("SUM (CASE WHEN r.hangid IS NULL THEN 0  ELSE 1 "
                           "END) AS numhang"))
        sql_select.append(("SUM (CASE WHEN r.process_type IS NULL THEN 0  "
                           "ELSE 1 END) AS numplugin"))

        ## Searching through plugins
        if params["report_process"] == "plugin":
            sql_select.append(("plugins.name AS pluginName, "
                               "plugins_reports.version AS pluginVersion, "
                               "plugins.filename AS pluginFilename"))

        return ", ".join(sql_select)

    def generate_sql_from(self, params):
        """
        Generate and return the FROM part of the final SQL query.
        """
        sql_from = ["FROM reports r"]

        ## Searching through plugins
        if params["report_process"] == "plugin":
            sql_from.append(("plugins_reports ON "
                             "plugins_reports.report_id = r.id"))
            sql_from.append(("plugins ON "
                             "plugins_reports.plugin_id = plugins.id"))

        return sql_from

    def generate_sql_group(self, params):
        """
        Generate and return the GROUP BY part of the final SQL query.
        """
        sql_group = ["GROUP BY r.signature"]

        # Searching through plugins
        if params["report_process"] == "plugin":
            sql_group.append("pluginName, pluginVersion, pluginFilename ")

        return ", ".join(sql_group)

import logging
import datetime
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util
from socorro.lib import search_common, util

import socorro.database.database as db

logger = logging.getLogger("webapi")


class Report(PostgreSQLBase):

    """
    Implement the /report service with PostgreSQL.
    """

    def get_list(self, **kwargs):
        """
        List all crashes with a given signature and return them.

        Optional arguments: see SearchCommon.get_parameters()

        """
        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        params = search_common.get_parameters(kwargs)
        params["signature"] = kwargs.get("signature")

        if params["signature"] is None:
            return None
        elif isinstance(params["signature"], list):
            params["signature"] = " ".join(params["signature"])

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
                                                params["plugin_search_mode"])

        # Get information about the versions
        util_service = Util(config=self.context)
        params["versions_info"] = util_service.versions_info(**params)

        # Parsing the versions
        params["versions_string"] = params["versions"]
        (params["versions"], params["products"]) = self.parse_versions(
                                                            params["versions"],
                                                            params["products"])

        # Changing the OS ids to OS names
        for i, elem in enumerate(params["os"]):
            for platform in self.context.platforms:
                if platform["id"] == elem:
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
                r.uuid,
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
                    AS install_time,
                rd.duplicate_of
        """

        sql_from = self.build_reports_sql_from(params)
        sql_from = """%s
            LEFT OUTER JOIN reports_duplicates rd ON r.uuid = rd.uuid
        """ % sql_from

        (sql_where, sql_params) = self.build_reports_sql_where(params,
                                                               sql_params,
                                                               self.context)

        sql_order = """
            ORDER BY r.date_processed DESC
        """

        (sql_limit, sql_params) = self.build_reports_sql_limit(params,
                                                               sql_params)

        # Assembling the query
        sql_query = " ".join((
                "/* socorro.external.postgresql.report.Report.list */",
                sql_select, sql_from, sql_where, sql_order, sql_limit))

        # Query for counting the results
        sql_count_query = " ".join((
                "/* socorro.external.postgresql.report.Report.list */",
                "SELECT count(*)", sql_from, sql_where))

        # Debug
        logger.debug(sql_count_query)
        logger.debug(cur.mogrify(sql_count_query, sql_params))

        # Querying the DB
        try:
            total = db.singleValueSql(cur, sql_count_query, sql_params)
        except db.SQLDidNotReturnSingleValue:
            total = 0
            util.reportExceptionAndContinue(logger)

        results = []

        # No need to call Postgres if we know there will be no results
        if total != 0:
            try:
                results = db.execute(cur, sql_query, sql_params)
            except psycopg2.Error:
                util.reportExceptionAndContinue(logger)

        json_result = {
            "total": total,
            "hits": []
        }

        # Transforming the results into what we want
        for crash in results:
            row = dict(zip((
                       "date_processed",
                       "uptime",
                       "user_comments",
                       "uuid",
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
                       "duplicate_of"), crash))
            for i in row:
                if isinstance(row[i], datetime.datetime):
                    row[i] = str(row[i])
            json_result["hits"].append(row)

        self.connection.close()

        return json_result

    def generate_sql_select(self, params):
        """
        Generate and return the SELECT part of the final SQL query.
        """
        sql_select = ["SELECT r.signature, count(r.id) as total"]

        ## Adding count for each OS
        for i in self.context.platforms:
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

        ## Searching through branches
        if params["branches"]:
            sql_from.append(("branches ON (branches.product = r.product "
                             "AND branches.version = r.version)"))

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

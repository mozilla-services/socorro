import logging
import psycopg2
import datetime

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util
from socorro.lib import search_common, util

import socorro.database.database as db

logger = logging.getLogger("webapi")


class Crashes(PostgreSQLBase):

    """
    Implement the /crashes service with PostgreSQL.
    """

    def __init__(self, *args, **kwargs):
        super(Crashes, self).__init__(*args, **kwargs)

    def prepare_search_params(self, **kwargs):
        """Return a dictionary of parameters for a search-like SQL query.

        Uses socorro.lib.search_common.get_parameters() for arguments
        filtering.
        """
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

        # Searching for terms in plugins
        if params["report_process"] == "plugin" and params["plugin_terms"]:
            params["plugin_terms"] = " ".join(params["plugin_terms"])
            params["plugin_terms"] = Crashes.prepare_terms(
                                                params["plugin_terms"],
                                                params["plugin_search_mode"])

        # Get information about the versions
        util_service = Util(config=self.context)
        params["versions_info"] = util_service.versions_info(**params)

        # Parsing the versions
        params["versions_string"] = params["versions"]
        (params["versions"], params["products"]) = Crashes.parse_versions(
                                                            params["versions"],
                                                            params["products"])

        # Changing the OS ids to OS names
        for i, elem in enumerate(params["os"]):
            for platform in self.context.platforms:
                if platform["id"] == elem:
                    params["os"][i] = platform["name"]

        return params

    def get_comments(self, **kwargs):
        """Return a list of comments on crash reports, filtered by
        signatures and other fields.

        See socorro.lib.search_common.get_parameters() for all filters.
        """
        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        params = self.prepare_search_params(**kwargs)
        if params is None:
            return None

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

        (sql_limit, sql_params) = self.build_reports_sql_limit(params,
                                                               sql_params)

        # Assembling the query
        sql_query = " ".join((
                "/* external.postgresql.crashes.Crashes.get_comments */",
                sql_select, sql_from, sql_where, sql_order, sql_limit))

        # Query for counting the results
        sql_count_query = " ".join((
                "/* external.postgresql.crashes.Crashes.get_comments */",
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
                       "user_comments",
                       "uuid",
                       "email"), crash))
            for i in row:
                if isinstance(row[i], datetime.datetime):
                    row[i] = str(row[i])
            json_result["hits"].append(row)

        self.connection.close()

        return json_result

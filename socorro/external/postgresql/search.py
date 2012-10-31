# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external import DatabaseError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util
from socorro.lib import search_common

logger = logging.getLogger("webapi")


class Search(PostgreSQLBase):

    """
    Implement the /search service with PostgreSQL.
    """

    def search(self, **kwargs):
        import warnings
        warnings.warn("Use `.get()' instead", DeprecationWarning, 2)
        return self.get(**kwargs)

    def signatures(self, **kwargs):
        kwargs['data_type'] = 'signatures'
        return self.get(**kwargs)

    def crashes(self, **kwargs):
        kwargs['data_type'] = 'crashes'
        return self.get(**kwargs)

    def get(self, **kwargs):
        """
        Search for crashes and return them.

        See http://socorro.readthedocs.org/en/latest/middleware.html#search

        Optional arguments: see SearchCommon.get_parameters()

        """
        params = search_common.get_parameters(kwargs)

        # change aliases from the web to the implementation's need
        if "for" in params and "terms" not in params:
            params["terms"] = params.get("for")
        if "from" in params and "from_date" not in params:
            params["from_date"] = params.get("from")
        if "to" in params and "to_date" not in params:
            params["to_date"] = params.get("to")
        if "in" in params and "fields" not in params:
            params["fields"] = params.get("in")

        # Default mode falls back to starts_with for postgres
        if params["search_mode"] == "default":
            params["search_mode"] = "starts_with"
        if params["plugin_search_mode"] == "default":
            params["plugin_search_mode"] = "starts_with"

        # For Postgres, we never search for a list of terms
        if params["terms"]:
            params["terms"] = " ".join(params["terms"])
            params["terms"] = Search.prepare_terms(params["terms"],
                                                   params["search_mode"])

        # Searching for terms in plugins
        if params["report_process"] == "plugin" and params["plugin_terms"]:
            params["plugin_terms"] = " ".join(params["plugin_terms"])
            params["plugin_terms"] = Search.prepare_terms(
                                                params["plugin_terms"],
                                                params["plugin_search_mode"])

        # Get information about the versions
        util_service = Util(config=self.context)
        params["versions_info"] = util_service.versions_info(**params)

        # Parsing the versions
        params["versions_string"] = params["versions"]
        (params["versions"], params["products"]) = Search.parse_versions(
                                                            params["versions"],
                                                            params["products"])
        if hasattr(self.context, 'webapi'):
            context = self.context.webapi
        else:
            # old middleware
            context = self.context
        # Changing the OS ids to OS names
        for i, elem in enumerate(params["os"]):
            for platform in context.platforms:
                if platform["id"][0:3] == elem[0:3]:
                    params["os"][i] = platform["name"]

        # Creating the parameters for the sql query
        sql_params = {}

        # Preparing the different parts of the sql query
        sql_select = self.generate_sql_select(params)

        # Adding count for each OS
        for i in context.platforms:
            sql_params["os_%s" % i["id"]] = i["name"]

        sql_from = self.build_reports_sql_from(params)

        (sql_where, sql_params) = self.build_reports_sql_where(params,
                                                               sql_params,
                                                               context)

        sql_group = self.generate_sql_group(params)

        sql_order = """
            ORDER BY total DESC, signature
        """

        (sql_limit, sql_params) = self.build_reports_sql_limit(params,
                                                               sql_params)

        # Assembling the query
        sql_query = " ".join(("/* socorro.search.Search search */",
                              sql_select, sql_from, sql_where, sql_group,
                              sql_order, sql_limit))

        # Query for counting the results
        sql_count_query = " ".join((
                "/* socorro.external.postgresql.search.Search search.count */",
                "SELECT count(DISTINCT r.signature)", sql_from, sql_where))

        # Querying the database
        try:
            connection = self.database.connection()

            total = self.count(
                sql_count_query,
                sql_params,
                error_message="Failed to count crashes from PostgreSQL.",
                connection=connection
            )

            results = []

            # No need to call Postgres if we know there will be no results
            if total != 0:
                results = self.query(
                    sql_query,
                    sql_params,
                    error_message="Failed to retrieve crashes from PostgreSQL",
                    connection=connection
                )
        except psycopg2.Error:
            raise DatabaseError("Failed to retrieve crashes from PostgreSQL")
        finally:
            if connection:
                connection.close()

        # Transforming the results into what we want
        crashes = []
        for row in results:
            if params["report_process"] == "plugin":
                crash = dict(zip((
                    "signature",
                    "count",
                    "is_windows",
                    "is_mac",
                    "is_linux",
                    "numhang",
                    "numplugin",
                    "numcontent",
                    "pluginname",
                    "pluginversion",
                    "pluginfilename"
                ), row))
            else:
                crash = dict(zip((
                    "signature",
                    "count",
                    "is_windows",
                    "is_mac",
                    "is_linux",
                    "numhang",
                    "numplugin",
                    "numcontent"
                ), row))
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
        sql_select.append(("SUM (CASE WHEN r.process_type='plugin' THEN 1"
                           "ELSE 0 END) as numplugin"))
        sql_select.append(("SUM (CASE WHEN r.process_type='content' THEN 1"
                           "ELSE 0 END) as numcontent"))

        ## Searching through plugins
        if params["report_process"] == "plugin":
            sql_select.append(("plugins.name AS pluginName, "
                               "plugins_reports.version AS pluginVersion, "
                               "plugins.filename AS pluginFilename"))

        return ", ".join(sql_select)

    def generate_sql_group(self, params):
        """
        Generate and return the GROUP BY part of the final SQL query.
        """
        sql_group = ["GROUP BY r.signature"]

        # Searching through plugins
        if params["report_process"] == "plugin":
            sql_group.append("pluginName, pluginVersion, pluginFilename ")

        return ", ".join(sql_group)

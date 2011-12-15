import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util

import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil
import socorro.lib.search_common as search_common
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class Search(PostgreSQLBase):

    """
    Implement the /search service with PostgreSQL.
    """

    def __init__(self, *args, **kwargs):
        super(Search, self).__init__(*args, **kwargs)

    def search(self, **kwargs):
        """
        Search for crashes and return them.

        See http://socorro.readthedocs.org/en/latest/middleware.html#search

        Optional arguments: see SearchCommon.get_parameters()

        """
        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        params = search_common.get_parameters(kwargs)

        # Default mode falls back to starts_with for postgres
        if params["search_mode"] == "default":
            params["search_mode"] = "starts_with"
        if params["plugin_search_mode"] == "default":
            params["plugin_search_mode"] = "starts_with"

        # Handling dates
        params["from_date"] = dtutil.string_to_datetime(params["from_date"])
        params["to_date"] = dtutil.string_to_datetime(params["to_date"])

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

        # Parsing the versions
        params["versions_string"] = params["versions"]
        (params["versions"], params["products"]) = Search.parse_versions(
                                                            params["versions"],
                                                            params["products"])

        # Changing the OS ids to OS names
        for i, elem in enumerate(params["os"]):
            for platform in self.context.platforms:
                if platform["id"] == elem:
                    params["os"][i] = platform["name"]

        # Creating the parameters for the sql query
        sql_params = {
            "from_date": params["from_date"],
            "to_date": params["to_date"],
            "limit": params["result_number"],
            "offset": params["result_offset"]
        }
        sql_params = Search.dispatch_params(sql_params, "term",
                                            params["terms"])
        sql_params = Search.dispatch_params(sql_params, "product",
                                            params["products"])
        sql_params = Search.dispatch_params(sql_params, "os",
                                            params["os"])
        sql_params = Search.dispatch_params(sql_params, "version",
                                            params["versions"])
        sql_params = Search.dispatch_params(sql_params, "build",
                                            params["build_ids"])
        sql_params = Search.dispatch_params(sql_params, "reason",
                                            params["reasons"])
        sql_params = Search.dispatch_params(sql_params, "plugin_term",
                                            params["plugin_terms"])
        sql_params = Search.dispatch_params(sql_params, "branch",
                                            params["branches"])

        # Preparing the different parts of the sql query

        #---------------------------------------------------------------
        # SELECT
        #---------------------------------------------------------------

        sql_select = self.generate_sql_select(params)

        # Adding count for each OS
        for i in self.context.platforms:
            sql_params["os_%s" % i["id"]] = i["name"]

        #---------------------------------------------------------------
        # FROM
        #---------------------------------------------------------------

        sql_from = self.generate_sql_from(params)

        #---------------------------------------------------------------
        # WHERE
        #---------------------------------------------------------------

        sql_where = ["""
            WHERE r.date_processed BETWEEN %(from_date)s AND %(to_date)s
        """]

        ## Adding terms to where clause
        if params["terms"]:
            if params["search_mode"] == "is_exactly":
                sql_where.append("r.signature=%(term)s")
            else:
                sql_where.append("r.signature LIKE %(term)s")

        ## Adding products to where clause
        if params["products"]:
            products_list = ["r.product=%(product" + str(x) + ")s"
                             for x in range(len(params["products"]))]
            sql_where.append("(%s)" % (" OR ".join(products_list)))

        ## Adding OS to where clause
        if params["os"]:
            os_list = ["r.os_name=%(os" + str(x) + ")s"
                       for x in range(len(params["os"]))]
            sql_where.append("(%s)" % (" OR ".join(os_list)))

        ## Adding branches to where clause
        if params["branches"]:
            branches_list = ["branches.branch=%(branch" + str(x) + ")s"
                             for x in range(len(params["branches"]))]
            sql_where.append("(%s)" % (" OR ".join(branches_list)))

        ## Adding versions to where clause
        if params["versions"]:

            # Get information about the versions
            versions_service = Util(config=self.context)
            fakeparams = {
                "versions": params["versions_string"]
            }
            versions_info = versions_service.versions_info(**fakeparams)

            if isinstance(params["versions"], list):
                versions_where = []

                for x in range(0, len(params["versions"]), 2):
                    version_where = []
                    version_where.append(str(x).join(("r.product=%(version",
                                                      ")s")))

                    key = "%s:%s" % (params["versions"][x],
                                     params["versions"][x + 1])
                    version_where = self.generate_version_where(
                                            key, params["versions"],
                                            versions_info, x, sql_params,
                                            version_where)

                    version_where.append(str(x + 1).join((
                                            "r.version=%(version", ")s")))
                    versions_where.append("(%s)" % " AND ".join(version_where))

                sql_where.append("(%s)" % " OR ".join(versions_where))

            else:
                # Original product:value
                key = "%s:%s" % (params["products"], params["versions"])
                version_where = []

                version_where = self.generate_version_where(
                                            key, params["versions"],
                                            versions_info, None, sql_params,
                                            version_where)

                version_where.append("r.version=%(version)s")
                sql_where.append("(%s)" % " AND ".join(version_where))

        ## Adding build id to where clause
        if params["build_ids"]:
            build_ids_list = ["r.build=%(build" + str(x) + ")s"
                              for x in range(len(params["build_ids"]))]
            sql_where.append("(%s)" % (" OR ".join(build_ids_list)))

        ## Adding reason to where clause
        if params["reasons"]:
            reasons_list = ["r.reason=%(reason" + str(x) + ")s"
                            for x in range(len(params["reasons"]))]
            sql_where.append("(%s)" % (" OR ".join(reasons_list)))

        if params["report_type"] == "crash":
            sql_where.append("r.hangid IS NULL")
        elif params["report_type"] == "hang":
            sql_where.append("r.hangid IS NOT NULL")

        ## Searching through plugins
        if params["report_process"] == "plugin":
            sql_where.append("r.process_type = 'plugin'")
            sql_where.append(("plugins_reports.date_processed BETWEEN "
                              "%(from_date)s AND %(to_date)s"))

            if params["plugin_terms"]:
                comp = "="

                if params["plugin_search_mode"] in ("contains", "starts_with"):
                    comp = " LIKE "

                sql_where_plugin_in = []
                for f in params["plugin_in"]:
                    if f == "name":
                        field = "plugins.name"
                    elif f == "filename":
                        field = "plugins.filename"

                    sql_where_plugin_in.append(comp.join((field,
                                                          "%(plugin_term)s")))

                sql_where.append("(%s)" % " OR ".join(sql_where_plugin_in))

        elif params["report_process"] == "browser":
            sql_where.append("r.process_type IS NULL")

        elif params["report_process"] == "content":
            sql_where.append("r.process_type = 'content'")

        sql_where = " AND ".join(sql_where)

        #---------------------------------------------------------------
        # GROUP BY
        #---------------------------------------------------------------

        sql_group = self.generate_sql_group(params)

        #---------------------------------------------------------------
        # ORDER BY
        #---------------------------------------------------------------

        sql_order = """
            ORDER BY total DESC
        """

        #---------------------------------------------------------------
        # LIMIT OFFSET
        #---------------------------------------------------------------

        sql_limit = """
            LIMIT %(limit)s
            OFFSET %(offset)s
        """

        # Assembling the query
        sql_from = " JOIN ".join(sql_from)
        sql_query = " ".join(("/* socorro.search.Search search */",
                              sql_select, sql_from, sql_where, sql_group,
                              sql_order, sql_limit))

        # Query for counting the results
        sql_count_query = " ".join((
                "/* socorro.external.postgresql.search.Search search.count */",
                "SELECT count(DISTINCT r.signature)", sql_from, sql_where))

        # Debug
        logger.debug(cur.mogrify(sql_query, sql_params))

        # Querying the DB
        try:
            total = db.singleValueSql(cur, sql_count_query, sql_params)
        except Exception:
            total = 0
            util.reportExceptionAndContinue(logger)

        # No need to call Postgres if we know there will be no results
        if total != 0:
            try:
                results = db.execute(cur, sql_query, sql_params)
            except Exception:
                results = []
                util.reportExceptionAndContinue(logger)
        else:
            results = []

        json_result = {
            "total": total,
            "hits": []
        }

        # Transforming the results into what we want
        for crash in results:
            if params["report_process"] == "plugin":
                row = dict(zip(("signature", "count", "is_windows", "is_mac",
                                "is_linux", "numhang", "numplugin",
                                "numcontent", "pluginname", "pluginversion",
                                "pluginfilename"), crash))
            else:
                row = dict(zip(("signature", "count", "is_windows", "is_mac",
                                "is_linux", "numhang", "numplugin",
                                "numcontent"), crash))
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
        sql_select.append(("SUM (CASE WHEN r.process_type='content' THEN 1"
                           "ELSE 0 END) as numcontent"))

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

    @staticmethod
    def prepare_terms(terms, search_mode):
        """
        Prepare terms for search, adding '%' where needed,
        given the search mode.
        """
        if search_mode in ("contains", "starts_with"):
            terms = terms.replace("_", "\_").replace("%", "\%")

        if search_mode == "contains":
            terms = "%" + terms + "%"
        elif search_mode == "starts_with":
            terms = terms + "%"
        return terms

    @staticmethod
    def generate_version_where(key, versions, versions_info, x, sql_params,
                               version_where):
        """
        Return a list of strings for version restrictions.
        """
        if key in versions_info:
            version_info = versions_info[key]
        else:
            version_info = None

        if x is None:
            version_param = "version"
        else:
            version_param = "version%s" % (x + 1)

        if version_info and version_info["release_channel"]:
            if version_info["release_channel"] in ("Beta", "Aurora",
                                                   "Nightly"):
                # Use major_version instead of full version
                sql_params[version_param] = version_info["major_version"]
                # Restrict by release_channel
                version_where.append("r.release_channel ILIKE '%s'" % (
                                            version_info["release_channel"]))
                if version_info["release_channel"] == "Beta":
                    # Restrict to a list of build_id
                    version_where.append("r.build IN ('%s')" % (
                        "', '".join([
                            str(bid) for bid in version_info["build_id"]])))

            else:
                # it's a release
                version_where.append(("r.release_channel NOT IN ('nightly', "
                                      "'aurora', 'beta')"))

        return version_where
